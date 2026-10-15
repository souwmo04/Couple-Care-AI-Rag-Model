"""Chat orchestration: the end-to-end pipeline for one user turn.

    validate → detect language → normalize → safety pre-check → retrieve (dense + BM25 → RRF
    → optional rerank → threshold/dedupe) → context budget → generate → validate citations
    → response safety check → persist (if enabled) → respond

``prepare`` does everything before generation and is shared by the JSON endpoint and the
streaming endpoint. When the safety layer selects a deterministic template, no model call
is made and the response is marked ``generated = False`` — template text is never passed
off as model output.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime

from app.core.container import Container
from app.core.language import (
    analyze_language,
    estimate_tokens,
    normalize_text,
    output_token_allowance,
    response_language_for,
)
from app.core.prompts import build_messages
from app.core.schemas import (
    ChatRequest,
    ChatResponse,
    DetectedLanguage,
    SafetyLevel,
    SafetyStatus,
    SourceCard,
    StoredMessage,
)
from app.errors import AppError, NotFoundError
from app.generation.llm_client import GenerationParams
from app.retrieval.citations import build_source_cards, format_context, validate_citations
from app.retrieval.retriever import RetrievalParams, RetrievalResult, RetrievedItem
from app.safety.escalation import SafetyDecision, decide, merge_levels, resources_for
from app.safety.output_check import check_response
from app.storage.sessions import Conversation, new_id

log = logging.getLogger("couplecare.orchestrator")

HISTORY_CHAR_LIMIT = 1200
PROMPT_OVERHEAD_TOKENS = 900
VAGUE_MAX_TOKENS = 6


@dataclass
class TurnPlan:
    request: ChatRequest
    owner: str
    conversation: Conversation
    message: str
    detected: DetectedLanguage
    response_language: str
    decision: SafetyDecision
    retrieval: RetrievalResult | None
    context_items: list[RetrievedItem]
    grounded: bool
    needs_clarification_hint: bool
    started: float


def _stage_value(stage) -> str:
    return stage.value if hasattr(stage, "value") else str(stage)


class Orchestrator:
    def __init__(self, container: Container) -> None:
        self.c = container

    # ------------------------------------------------------------------ preparation
    async def prepare(self, request: ChatRequest, owner: str) -> TurnPlan:
        started = time.perf_counter()
        settings = self.c.settings
        runtime = self.c.settings_store.get()
        message = normalize_text(request.message)
        if not message:
            raise AppError("Message cannot be empty.", code="empty_message", status_code=422)
        if len(message) > settings.max_message_chars:
            raise AppError("Message is too long.", code="message_too_long", status_code=413)

        analysis = analyze_language(message)
        response_language = response_language_for(request.language.value, analysis.detected)

        store = self.c.store()
        if request.conversation_id:
            conversation = store.get(owner, request.conversation_id)
            if conversation is None:
                raise NotFoundError("Conversation not found. It may have expired or been deleted.")
        else:
            conversation = store.create(owner, message, request.relationship_stage, response_language)

        # Safety pre-check runs on the raw user text, independent of retrieval and generation.
        decision = decide(self.c.safety.assess(message), response_language)
        decision = merge_levels(decision, SafetyLevel(conversation.safety_level) if conversation.safety_level else None)

        retrieval: RetrievalResult | None = None
        context_items: list[RetrievedItem] = []
        # A very short opening message ("We had a fight.") lacks the context needed for useful advice.
        # Retrieval still finds loosely related passages, which led the model to confident but
        # off-target answers (dev evaluation 2026-10-15); ask what happened first instead.
        vague = analysis.token_count <= VAGUE_MAX_TOKENS and not request.conversation_id
        if not decision.skip_generation and not vague:
            query = self._retrieval_query(message, conversation)
            params = RetrievalParams(
                final_k=runtime.retrieval_top_k,
                dense_k=runtime.dense_top_k,
                bm25_k=runtime.bm25_top_k,
                threshold=runtime.relevance_threshold,
                rerank=runtime.rerank_enabled,
                expand=runtime.query_expansion_enabled,
            )
            # Embedding + FAISS search are CPU-bound; keep them off the event loop.
            retrieval = await asyncio.to_thread(self.c.retriever.search, query, params)
            output_tokens = output_token_allowance(response_language, runtime.max_output_tokens)
            context_items = self._fit_budget(retrieval.relevant, output_tokens, conversation)

        hint = vague  # caution-level safety addenda already ask their own check-in question
        return TurnPlan(
            request=request,
            owner=owner,
            conversation=conversation,
            message=message,
            detected=analysis.detected,
            response_language=response_language,
            decision=decision,
            retrieval=retrieval,
            context_items=context_items,
            grounded=bool(context_items),
            needs_clarification_hint=hint,
            started=started,
        )

    def _retrieval_query(self, message: str, conversation: Conversation) -> str:
        """Short follow-ups ("what should I say?") are retrieved together with the previous user turn."""
        if len(message.split()) >= 8:
            return message
        previous = [m.content for m in conversation.messages if m.role == "user"]
        return f"{previous[-1]}\n{message}" if previous else message

    def _fit_budget(
        self, items: list[RetrievedItem], output_tokens: int, conversation: Conversation
    ) -> list[RetrievedItem]:
        """Keep passages (in rank order) that fit the model's context window.

        Token costs are estimated per script (Bangla ≈ 1 token per character), so Bangla passages
        and history are not under-counted.
        """
        runtime = self.c.settings_store.get()
        profile = self.c.settings.get_model(runtime.model_id)
        context_tokens = profile.context_length if profile else 4096
        history = self._history(conversation, drop_trailing_user=False)
        history_tokens = sum(estimate_tokens(content) + 8 for _, content in history)
        budget = context_tokens - output_tokens - PROMPT_OVERHEAD_TOKENS - history_tokens
        chosen: list[RetrievedItem] = []
        used = 0
        for item in items:
            cost = estimate_tokens(item.passage.text) + 40  # label, title and section line
            if used + cost > budget:
                break
            chosen.append(item)
            used += cost
        return chosen

    def _history(self, conversation: Conversation, drop_trailing_user: bool) -> list[tuple[str, str]]:
        runtime = self.c.settings_store.get()
        messages = list(conversation.messages)
        if drop_trailing_user and messages and messages[-1].role == "user":
            messages = messages[:-1]
        recent = messages[-runtime.history_turns * 2 :] if runtime.history_turns else []
        return [(m.role, m.content[:HISTORY_CHAR_LIMIT]) for m in recent if m.content]

    # ------------------------------------------------------------------ helpers
    def _record_user_message(self, plan: TurnPlan) -> None:
        store = self.c.store()
        if plan.request.regenerate:
            store.remove_last_assistant(plan.owner, plan.conversation.id)
            return
        store.append(
            plan.owner,
            plan.conversation.id,
            StoredMessage(
                id=new_id(),
                role="user",
                content=plan.message,
                created_at=datetime.now(UTC),
                language=plan.detected.value,
            ),
            stage=plan.request.relationship_stage,
            language=plan.response_language,
        )

    def _safety_status(self, plan: TurnPlan) -> SafetyStatus:
        d = plan.decision
        region = self.c.settings_store.get().support_region
        resources = resources_for(self.c.support_directory, region, d.categories) if d.level != SafetyLevel.NONE else []
        if d.level == SafetyLevel.DECLINED:
            resources = []
        return SafetyStatus(level=d.level, message=d.banner, resources=resources)

    def _generation_params(self, plan: TurnPlan) -> GenerationParams:
        runtime = self.c.settings_store.get()
        return GenerationParams(
            temperature=runtime.temperature,
            max_tokens=output_token_allowance(plan.response_language, runtime.max_output_tokens),
        )

    def _messages(self, plan: TurnPlan):
        # Re-read the conversation after the user turn was recorded (SQLite returns snapshots).
        # The stored conversation now ends with the current user message, which is sent
        # separately with the evidence, so it is excluded from history.
        conversation = self.c.store().get(plan.owner, plan.conversation.id) or plan.conversation
        history = self._history(conversation, drop_trailing_user=True)
        return build_messages(
            user_message=plan.message,
            history=history,
            context=format_context(plan.context_items),
            response_language=plan.response_language,
            relationship_stage=_stage_value(plan.request.relationship_stage),
            grounded=plan.grounded,
            safety_addendum=plan.decision.prompt_addendum,
            needs_clarification_hint=plan.needs_clarification_hint,
        )

    def _finalize(self, plan: TurnPlan, raw_answer: str, generated: bool) -> ChatResponse:
        sources: list[SourceCard] = []
        answer = raw_answer
        flags: list[str] = []
        if generated:
            answer = trim_incomplete_sentence(answer)
            citation = validate_citations(answer, len(plan.context_items))
            answer = citation.text
            if citation.removed_markers:
                flags.append("fabricated_citation_removed")
            checked = check_response(answer, plan.decision.level, self.c.allowed_numbers)
            answer = checked.text
            flags.extend(checked.flags)
            sources = build_source_cards(plan.context_items, citation.cited_ids)
            if not answer.strip():
                answer = _empty_fallback(plan.response_language)
                generated = False
        if flags:
            log.info("response_adjusted", extra={"flags": flags})

        safety = self._safety_status(plan)
        message_id = new_id()
        self.c.store().append(
            plan.owner,
            plan.conversation.id,
            StoredMessage(
                id=message_id,
                role="assistant",
                content=answer,
                created_at=datetime.now(UTC),
                sources=sources,
                safety=safety,
                language=plan.response_language,
                grounded=plan.grounded and generated,
                generated=generated,
            ),
            safety_level=plan.decision.level.value if plan.decision.level != SafetyLevel.NONE else None,
        )

        needs_clarification = plan.needs_clarification_hint and _ends_with_question(answer)
        duration_ms = int((time.perf_counter() - plan.started) * 1000)
        log.info(
            "chat_turn",
            extra={
                "duration_ms": duration_ms,
                "language": plan.detected.value,
                "safety_level": plan.decision.level.value,
                "passages": len(plan.context_items),
                "generated": generated,
            },
        )
        return ChatResponse(
            conversation_id=plan.conversation.id,
            message_id=message_id,
            answer=answer,
            detected_language=plan.detected,
            response_language=plan.response_language,
            sources=sources,
            grounded=plan.grounded and generated,
            safety=safety,
            needs_clarification=needs_clarification,
            model_id=self.c.active_model_id() if generated else None,
            generated=generated,
            duration_ms=duration_ms,
        )

    # ------------------------------------------------------------------ entry points
    async def respond(self, request: ChatRequest, owner: str) -> ChatResponse:
        plan = await self.prepare(request, owner)
        self._record_user_message(plan)
        if plan.decision.skip_generation:
            return self._finalize(plan, plan.decision.template or "", generated=False)
        answer = await self.c.llm().complete(self._messages(plan), self._generation_params(plan))
        return self._finalize(plan, answer, generated=True)

    async def stream(self, request: ChatRequest, owner: str) -> AsyncIterator[dict]:
        """Yield events: ``meta`` → ``delta``* → ``done`` (or ``error``).

        Text is released sentence by sentence after the same citation and safety checks used
        for the final answer, so removed content is never shown even briefly.
        """
        plan = await self.prepare(request, owner)
        self._record_user_message(plan)
        yield {
            "event": "meta",
            "conversation_id": plan.conversation.id,
            "detected_language": plan.detected.value,
            "response_language": plan.response_language,
            "safety": self._safety_status(plan).model_dump(),
        }

        if plan.decision.skip_generation:
            final = self._finalize(plan, plan.decision.template or "", generated=False)
            yield {"event": "delta", "text": final.answer}
            yield {"event": "done", "response": final.model_dump(mode="json")}
            return

        buffer = ""
        raw = ""
        try:
            async for token in self.c.llm().stream(self._messages(plan), self._generation_params(plan)):
                raw += token
                buffer += token
                ready, buffer = _split_complete(buffer)
                if ready:
                    safe = self._check_fragment(ready, plan)
                    if safe:
                        yield {"event": "delta", "text": safe}
        except asyncio.CancelledError:
            # Client pressed stop / disconnected: keep what was generated so far.
            if raw.strip():
                self._finalize(plan, raw + "\n\n_(Generation stopped.)_", generated=True)
            raise
        except AppError as exc:
            yield {"event": "error", "code": exc.code, "message": exc.message, "retryable": exc.retryable}
            return
        if buffer:
            safe = self._check_fragment(buffer, plan)
            if safe:
                yield {"event": "delta", "text": safe}
        final = self._finalize(plan, raw, generated=True)
        yield {"event": "done", "response": final.model_dump(mode="json")}

    def _check_fragment(self, fragment: str, plan: TurnPlan) -> str:
        from app.generation.llm_client import strip_reasoning

        fragment = strip_reasoning(fragment) if "<think>" in fragment.lower() else fragment
        cited = validate_citations(fragment, len(plan.context_items)).text
        checked = check_response(cited, plan.decision.level, self.c.allowed_numbers).text
        # check_response trims whitespace; restore the separator the model produced.
        trailing = fragment[len(fragment.rstrip()) :]
        return checked + trailing if checked else ""


_BOUNDARY_RE = re.compile(r"[.!?।](?:\s+|$)|\n")


def _split_complete(buffer: str) -> tuple[str, str]:
    """Split ``buffer`` into (complete sentences, remainder)."""
    last = None
    for match in _BOUNDARY_RE.finditer(buffer):
        if match.end() < len(buffer) or buffer.endswith("\n"):
            last = match.end()
    if last is None:
        return "", buffer
    return buffer[:last], buffer[last:]


_TERMINAL_RE = re.compile(r"[.!?।?](?:[\s\]\)\"'”’*_]|\[S\d+\])*$")
_LAST_TERMINAL_RE = re.compile(r"[.!?।?](?:\s*\[S\d+\])*[\"'”’*_)]*(?=\s|$)")


def trim_incomplete_sentence(text: str) -> str:
    """Drop a trailing fragment cut off by the output-token limit ("… দুজনের মনে হয").

    Text that already ends a sentence, or that has no complete sentence at all, is returned as-is.
    """
    stripped = text.rstrip()
    if not stripped or _TERMINAL_RE.search(stripped):
        return stripped
    matches = list(_LAST_TERMINAL_RE.finditer(stripped))
    if not matches:
        return stripped
    return stripped[: matches[-1].end()].rstrip()


def _ends_with_question(text: str) -> bool:
    tail = text.strip()[-300:]
    return "?" in tail or "？" in tail


def _empty_fallback(language: str) -> str:
    return {
        "bn": "দুঃখিত, এই উত্তরটি নিরাপত্তা যাচাইয়ে আটকে গেছে। আপনার প্রশ্নটি একটু অন্যভাবে লিখে আবার চেষ্টা করবেন?",
        "banglish": "Dukkhito, ei uttor ta safety check e atke geche. Proshno ta ektu onnobhabe likhe abar try korben?",
    }.get(
        language, "Sorry — that answer didn't pass the safety checks. Could you rephrase your question and try again?"
    )
