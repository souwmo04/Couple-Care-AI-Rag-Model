"""Prompt assembly.

The system prompt lives in ``prompt_templates/system_v<N>.md`` so it can be reviewed and
edited without touching code. ``PROMPT_VERSION`` is recorded with every evaluation run so
results can be traced to the exact prompt used.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.generation.llm_client import ChatMessage

PROMPT_VERSION = "system_v1"
TEMPLATE_DIR = Path(__file__).parent / "prompt_templates"

LANGUAGE_INSTRUCTIONS = {
    "en": "Respond in clear, natural English.",
    "bn": (
        "Respond in natural, standard Bangla (বাংলা) using Bengali script. Use warm, respectful language "
        "(আপনি form). Keep common English terms only where Bangla speakers normally use them."
    ),
    "banglish": (
        "Respond in Banglish: Bangla written in Roman (English) letters, the way people text, mixing in common "
        "English words naturally (e.g. 'Apni ja feel korchen ta khub swabhabik'). Do not switch to Bengali script."
    ),
}

STAGE_CONTEXT = {
    "dating": "The user has said they are in a dating relationship.",
    "engaged": "The user has said they are engaged.",
    "married": "The user has said they are married.",
    "unspecified": "The user has not specified their relationship stage; do not assume one.",
}


@lru_cache(maxsize=4)
def load_system_prompt(version: str = PROMPT_VERSION) -> str:
    path = TEMPLATE_DIR / f"{version}.md"
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
) -> list[ChatMessage]:
    system_parts = [load_system_prompt(), "", LANGUAGE_INSTRUCTIONS.get(response_language, LANGUAGE_INSTRUCTIONS["en"]),
                    STAGE_CONTEXT.get(relationship_stage, STAGE_CONTEXT["unspecified"])]
    if safety_addendum:
        system_parts += ["", safety_addendum]
    system = "\n".join(system_parts)

    messages = [ChatMessage("system", system)]
    for role, content in history:
        messages.append(ChatMessage(role, content))

    if grounded:
        evidence = (
            "Knowledge-base passages for this question (cite with their labels):\n\n" + context
        )
    else:
        evidence = (
            "No sufficiently relevant passages were found in the knowledge base for this question. "
            "Say briefly that your answer is general guidance not drawn from the knowledge base, do not cite any "
            "sources, and be appropriately cautious."
        )
    hint = (
        "\n\nThe message is short or missing key details. If it would change your advice, ask one focused clarifying "
        "question (you may still offer a brief, general first thought)."
        if needs_clarification_hint else ""
    )
    messages.append(ChatMessage("user", f"{evidence}\n\n---\nUser message:\n{user_message}{hint}"))
    return messages
