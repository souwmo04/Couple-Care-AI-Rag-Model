"""Experiment runner for the four configurations and ablations.

Configurations (evaluation-only; never exposed to app users):
    A  base LLM, no retrieval, no safety orchestration
    B  dense-vector RAG (multilingual E5 only), no safety orchestration
    C  hybrid multilingual RAG (E5 + BM25 + RRF + query expansion), no safety orchestration
    D  hybrid RAG with safety-aware orchestration (the production pipeline)

Everything else — prompt version, generation parameters, model, index — is held constant
across configurations and recorded in the run manifest.

Suites:
    retrieval   no model needed; Recall@5/10, MRR, nDCG@10 per configuration and ablation
    safety      no model needed; risk-detection recall and inappropriate escalation per language
    generation  needs a running local model; produces outputs for human annotation plus
                automatic behaviour metrics (citation validity, clarification, abstention, latency)
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field

from app.core.prompts import PROMPT_VERSION, build_messages
from app.evaluation.dataset import EvalCase
from app.evaluation.metrics import mean, ndcg_at_k, rate, recall_at_k, reciprocal_rank, summarize_latencies
from app.retrieval.citations import format_context, validate_citations
from app.retrieval.retriever import RetrievalParams, Retriever
from app.safety.classifier import SafetyEnsemble
from app.safety.escalation import decide

CONFIGS = {
    "A": {"retrieval": None, "safety": False, "label": "Base LLM, no retrieval"},
    "B": {"retrieval": "dense", "safety": False, "label": "Dense RAG"},
    "C": {"retrieval": "hybrid", "safety": False, "label": "Hybrid multilingual RAG"},
    "D": {"retrieval": "hybrid", "safety": True, "label": "Hybrid RAG + safety orchestration"},
}


@dataclass
class RetrievalVariant:
    name: str
    mode: str = "hybrid"
    expand: bool = True
    rerank: bool = False
    final_k: int = 10
    notes: dict = field(default_factory=dict)


# ----------------------------------------------------------------------------- retrieval


def evaluate_retrieval(cases: list[EvalCase], retriever: Retriever, variant: RetrievalVariant) -> dict:
    per_case = []
    by_language: dict[str, list[dict]] = defaultdict(list)
    latencies = []
    for case in cases:
        relevant = set(case.relevant_document_ids)
        if not relevant:
            continue
        # Retrieve a deep passage list, then evaluate at the *document* level: the ranked document
        # list is the passages' documents in order of first appearance, cut to variant.final_k.
        params = RetrievalParams(final_k=50, dense_k=50, bm25_k=50, threshold=0.0,
                                 mode=variant.mode, expand=variant.expand, rerank=variant.rerank)  # fmt: skip
        result = retriever.search(case.user_query, params)
        latencies.append(result.duration_ms)
        ranked = list(dict.fromkeys(i.passage.document_id for i in result.items))[: variant.final_k]
        row = {
            "case_id": case.case_id,
            "language": case.language,
            "topic": case.topic,
            "recall@5": recall_at_k(ranked, relevant, 5),
            "recall@10": recall_at_k(ranked, relevant, 10),
            "mrr": reciprocal_rank(ranked, relevant),
            "ndcg@10": ndcg_at_k(ranked, relevant, 10),
            "effective_mode": result.mode,
        }
        per_case.append(row)
        by_language[case.language].append(row)

    def agg(rows: list[dict]) -> dict:
        return {m: mean([r[m] for r in rows]) for m in ("recall@5", "recall@10", "mrr", "ndcg@10")} | {"n": len(rows)}

    return {
        "variant": variant.name,
        "settings": {"mode": variant.mode, "expand": variant.expand, "rerank": variant.rerank, **variant.notes},
        "overall": agg(per_case),
        "by_language": {lang: agg(rows) for lang, rows in sorted(by_language.items())},
        "latency": summarize_latencies(latencies),
        "per_case": per_case,
    }


# ----------------------------------------------------------------------------- safety


def evaluate_safety(cases: list[EvalCase], ensemble: SafetyEnsemble | None = None) -> dict:
    ensemble = ensemble or SafetyEnsemble()
    per_case = []
    for case in cases:
        decision = decide(ensemble.assess(case.user_query), case.language if case.language != "mixed" else "en")
        flagged = decision.level.value != "none"
        per_case.append(
            {
                "case_id": case.case_id,
                "language": case.language,
                "expected": case.safety_category,
                "predicted_level": decision.level.value,
                "predicted_categories": [c.value for c in decision.categories],
                "flagged": flagged,
                "category_match": case.safety_category in [c.value for c in decision.categories],
            }
        )

    def agg(rows: list[dict]) -> dict:
        risky = [r for r in rows if r["expected"] != "none"]
        benign = [r for r in rows if r["expected"] == "none"]
        return {
            "risk_detection_recall": rate([r["flagged"] for r in risky]),
            "category_recall": rate([r["category_match"] for r in risky]),
            "inappropriate_escalation": rate([r["flagged"] for r in benign]),
            "n_risky": len(risky),
            "n_benign": len(benign),
        }

    languages = sorted({r["language"] for r in per_case})
    categories = sorted({r["expected"] for r in per_case if r["expected"] != "none"})
    return {
        "overall": agg(per_case),
        "by_language": {lang: agg([r for r in per_case if r["language"] == lang]) for lang in languages},
        "by_category": {
            cat: {
                "recall": rate([r["category_match"] for r in per_case if r["expected"] == cat]),
                "n": sum(r["expected"] == cat for r in per_case),
            }  # fmt: skip
            for cat in categories
        },
        "misses": [r for r in per_case if r["expected"] != "none" and not r["flagged"]],
        "false_alarms": [r for r in per_case if r["expected"] == "none" and r["flagged"]],
        "per_case": per_case,
    }


# ----------------------------------------------------------------------------- generation


async def generate_for_config(case: EvalCase, config: str, container, runtime) -> dict:
    """Run one case through configuration A–D. Requires a reachable local model server."""
    from app.core.language import analyze_language, response_language_for
    from app.core.orchestrator import Orchestrator
    from app.core.schemas import ChatRequest, LanguageCode, RelationshipStage
    from app.generation.llm_client import GenerationParams

    started = time.perf_counter()
    spec = CONFIGS[config]
    if spec["safety"]:
        request = ChatRequest(message=case.user_query, language=LanguageCode.AUTO,
                              relationship_stage=RelationshipStage(case.relationship_stage))  # fmt: skip
        response = await Orchestrator(container).respond(request, owner="evaluation-run")
        return {
            "answer": response.answer, "generated": response.generated, "grounded": response.grounded,
            "safety_level": response.safety.level.value, "cited": [s.citation_id for s in response.sources if s.cited],
            "retrieved_documents": [s.document_id for s in response.sources],
            "needs_clarification": response.needs_clarification, "latency_ms": response.duration_ms,
            "citations_removed": None,
        }  # fmt: skip

    analysis = analyze_language(case.user_query)
    language = response_language_for("auto", analysis.detected)
    items = []
    if spec["retrieval"]:
        result = container.retriever.search(case.user_query, RetrievalParams(
            final_k=runtime.retrieval_top_k, threshold=runtime.relevance_threshold, mode=spec["retrieval"],
            expand=spec["retrieval"] == "hybrid"))  # fmt: skip
        items = result.relevant
    messages = build_messages(
        user_message=case.user_query,
        history=[],
        context=format_context(items),
        response_language=language,
        relationship_stage=case.relationship_stage,
        grounded=bool(items),
        safety_addendum=None,
        needs_clarification_hint=False,
    )
    raw = await container.llm().complete(messages, GenerationParams(temperature=runtime.temperature,
                                                                    max_tokens=runtime.max_output_tokens))  # fmt: skip
    check = validate_citations(raw, len(items))
    return {
        "answer": check.text, "generated": True, "grounded": bool(items), "safety_level": "not_applied",
        "cited": check.cited_ids, "retrieved_documents": [i.passage.document_id for i in items],
        "needs_clarification": "?" in check.text.strip()[-300:],
        "latency_ms": int((time.perf_counter() - started) * 1000), "citations_removed": check.removed_markers,
    }  # fmt: skip


def summarize_generation(rows: list[dict], cases: dict[str, EvalCase]) -> dict:
    def pick(cond) -> list[dict]:
        return [r for r in rows if cond(cases[r["case_id"]])]

    clar = pick(lambda c: c.requires_clarification)
    no_clar = pick(lambda c: not c.requires_clarification and c.safety_category == "none" and not c.out_of_scope)
    oos = pick(lambda c: c.out_of_scope)
    risky = pick(lambda c: c.safety_category != "none")
    benign = pick(lambda c: c.safety_category == "none")
    return {
        "n": len(rows),
        "appropriate_clarification": rate([r["needs_clarification"] for r in clar]),
        "over_clarification": rate([r["needs_clarification"] for r in no_clar]),
        "appropriate_abstention": rate([not r["grounded"] for r in oos]),
        "risk_detection_recall": rate([r["safety_level"] not in {"none", "not_applied"} for r in risky]),
        "inappropriate_escalation": rate([r["safety_level"] not in {"none", "not_applied"} for r in benign]),
        "fabricated_citations_removed": sum(r["citations_removed"] or 0 for r in rows),
        "latency": summarize_latencies([r["latency_ms"] for r in rows]),
        "prompt_version": PROMPT_VERSION,
    }
