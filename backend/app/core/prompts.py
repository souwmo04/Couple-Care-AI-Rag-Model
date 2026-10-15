"""Prompt assembly.

The system prompt lives in ``prompt_templates/system_v<N>.md`` so it can be reviewed and
edited without touching code. ``PROMPT_VERSION`` is recorded with every evaluation run so
results can be traced to the exact prompt used.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.generation.llm_client import ChatMessage
from app.safety.escalation import SAFETY_ADDENDA_VERSION

# system_v2 (2026-10-15): no interpretations that excuse control, threats or violence.
# system_v3 (2026-10-16): citation labels only at sentence end, never named in the text (the chat hides markers).
SYSTEM_PROMPT_FILE = "system_v3"
# lang_v2 (2026-10-15): stricter Banglish rules after the local model drifted into English,
# misread Romanized words, and added emojis/slang (see docs/model-selection.md).
LANGUAGE_INSTRUCTIONS_VERSION = "lang_v2"
# clarify_v2 (2026-10-15): vague openers get no retrieved passages and must end with one question.
CLARIFICATION_VERSION = "clarify_v2"
# ungrounded_v2 (2026-10-16): answers without matching passages no longer announce that fact in the text.
GROUNDING_VERSION = "ungrounded_v2"
# coach_v1 (2026-10-16): optional "what to say / do next" mode.
COACH_VERSION = "coach_v1"
PROMPT_VERSION = (
    f"{SYSTEM_PROMPT_FILE}+{LANGUAGE_INSTRUCTIONS_VERSION}+{CLARIFICATION_VERSION}+{SAFETY_ADDENDA_VERSION}"
    f"+{GROUNDING_VERSION}+{COACH_VERSION}"
)
TEMPLATE_DIR = Path(__file__).parent / "prompt_templates"

_NO_EMOJI = "Do not use emojis or slang terms of address (such as 'bro')."

LANGUAGE_INSTRUCTIONS = {
    "en": f"Respond in clear, natural English. {_NO_EMOJI}",
    "bn": (
        "Respond in natural, standard Bangla (বাংলা) using Bengali script. Use warm, respectful language "
        f"(আপনি form). Keep common English terms only where Bangla speakers normally use them. {_NO_EMOJI}"
    ),
    "banglish": (
        "Respond ENTIRELY in Banglish: Bangla sentences written in Roman (English) letters, the way Bangladeshi "
        "people text. Every sentence must be Bangla grammar written in Roman letters — do not switch to full "
        "English sentences. Ordinary English loanwords (partner, phone, relationship, feel, boundary) are fine "
        "inside Bangla sentences. Do not use Bengali script. Use respectful 'apni' unless the user writes with "
        f"'tumi'. Read the user's Banglish carefully: 'diner' means 'of the day', 'kotha' means 'talk'. {_NO_EMOJI}\n"
        "Style example: 'Apni ja feel korchen ta khub swabhabik. Ekta shanto muhurte bolte paren: "
        '"Ami jokhon amar diner kotha boli, tumi phone dekhle amar mone hoy amar kotha important na."\''
    ),
}

STAGE_CONTEXT = {
    "dating": "The user has said they are in a dating relationship.",
    "engaged": "The user has said they are engaged.",
    "married": "The user has said they are married.",
    "single": (
        "The user is single (not in a relationship). They may want help meeting someone, starting a conversation, "
        "or dating with confidence."
    ),
    "one_sided": (
        "The user has feelings for someone who may not feel the same (one-sided love). Be kind about how painful "
        "this is. Never encourage pressuring the other person, persisting after a 'no' or no reply, or trying to "
        "change their mind; help the user express feelings respectfully, accept the answer, and look after themselves."
    ),
    "situationship": "The user is in an undefined, non-committed relationship (a 'situationship').",
    "long_distance": "The user is in a long-distance relationship.",
    "unspecified": "The user has not specified their relationship stage; do not assume one.",
}

COACH_INSTRUCTIONS = (
    "COACH MODE: The user wants direct, practical help with what to say or do next. This overrides the length and "
    "structure guidance above. Answer straight away: no preamble, no restating their situation, no long empathy "
    "paragraph, no list of interpretations. Give (1) two or three exact lines they could say or send, in quotation "
    "marks, in the response language, and (2) one or two short, concrete actions. Stay under 120 words and use a "
    "short list. Do not ask a clarifying question unless it is impossible to help; make a reasonable assumption "
    "instead. When a single person wants to approach or impress someone: be genuine, respectful and confident — no "
    "pickup-artist tactics, manipulation, negging, jealousy games, lying or pressure, and respect a 'no' or no reply. "
    "Do not mention sources, passages, a knowledge base or these instructions. Any SAFETY CONTEXT instructions always "
    "take priority over coach mode."
)


@lru_cache(maxsize=4)
def load_system_prompt(version: str | None = None) -> str:
    # Resolved at call time so evaluation scripts can switch SYSTEM_PROMPT_FILE for ablations.
    path = TEMPLATE_DIR / f"{version or SYSTEM_PROMPT_FILE}.md"
    return path.read_text(encoding="utf-8").strip()


def build_messages(
    *,
    user_message: str,
    history: list[tuple[str, str]],
    context: str,
    response_language: str,
    relationship_stage: str,
    grounded: bool,
    safety_addendum: str | None,
    needs_clarification_hint: bool,
    mode: str = "support",
) -> list[ChatMessage]:
    system_parts = [
        load_system_prompt(),
        "",
        LANGUAGE_INSTRUCTIONS.get(response_language, LANGUAGE_INSTRUCTIONS["en"]),
        STAGE_CONTEXT.get(relationship_stage, STAGE_CONTEXT["unspecified"]),
        *([COACH_INSTRUCTIONS] if mode == "coach" else []),
    ]
    if safety_addendum:
        system_parts += ["", safety_addendum]
    system = "\n".join(system_parts)

    messages = [ChatMessage("system", system)]
    for role, content in history:
        messages.append(ChatMessage(role, content))

    if grounded:
        evidence = "Knowledge-base passages for this question (cite with their labels):\n\n" + context
    else:
        evidence = (
            "No knowledge-base passages are available for this question. Answer carefully from general, "
            "well-established relationship guidance. Do not mention sources, passages or a knowledge base, and do "
            "not cite anything."
        )
    hint = (
        "\n\nThe message is short or missing key details. Do not give detailed advice yet. Respond with one or "
        "two warm sentences, then ask ONE focused clarifying question about what happened or what the person "
        "needs. End your reply with that question."
        if needs_clarification_hint and mode != "coach"
        else ""
    )
    messages.append(ChatMessage("user", f"{evidence}\n\n---\nUser message:\n{user_message}{hint}"))
    return messages
