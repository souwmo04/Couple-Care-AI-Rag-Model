"""Language detection, normalization and lightweight query expansion.

Detection is deliberately simple and transparent:

* Bangla script is identified by the Unicode Bengali block (U+0980–U+09FF).
* Banglish (Romanized Bangla) is identified by a curated lexicon of high-frequency
  Romanized Bangla function words and relationship vocabulary.
* Code-switching is reported as ``mixed`` when both scripts, or English and a
  substantial share of Banglish tokens, appear together.

This is a heuristic, not a trained classifier. Its accuracy on real user text must be
measured with the evaluation set before being reported anywhere.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from app.core.schemas import DetectedLanguage

BENGALI_RE = re.compile(r"[ঀ-৿]")
LATIN_RE = re.compile(r"[A-Za-z]")
TOKEN_RE = re.compile(r"[ঀ-৿]+|[A-Za-z]+(?:'[A-Za-z]+)?|\d+")
# Control characters except tab/newline. ZWJ/ZWNJ (U+200D/U+200C) are preserved because
# they change how Bangla conjuncts render.
CONTROL_RE = re.compile(r"[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F​⁠﻿]")

# High-frequency Romanized Bangla words. Words that are also common English words
# (e.g. "a", "o", "to", "na" is kept because it is rare in English) are excluded.
BANGLISH_LEXICON: frozenset[str] = frozenset(
    """
    ami amar amake amra amader tumi tomar tomake tora apni apnar apnake se shey tar take tara
    oder ora ke ki keno kno kemne kivabe kibhabe kothay kokhon kobe koto kotodin
    na nai nei hoy hoye hobe hocche hochche hoise hoyeche hoyse chilo chhilo thake thaki theke
    kori kore korbo korchi korche korlam korsi korse koro korte korar bolo bole boli bollo bolche
    bolse bolchi jani jane janina bujhi bujhe bujhina bujhte dekhi dekhe shuni shune
    bhalo valo kharap kharaap onek khub besi beshi ektu kom shob sob kichu keu kauke
    jodi tahole tobe kintu abar ar aar shathe sathe songe jonno jonne moto mone mon
    bhalobasha bhalobashi valobasha valobashi bhalobase valobase prem premik premika
    bou jamai shami swami stri biye biya biyer shoshur shashuri sasur sasuri bari basha
    jhogra jhgra jhogrha ragi rag raag rege kanna kandi kande kosto koshto dukkho dukho
    sondeh shondeh sandeh hingsha hingse obhiman ovimaan obhimaan obhiman bisshash biswas
    bishshas thokano mittha mitthe miththa shotti shotto sotti
    ekta ekti ekjon duijon bolte bolun bolben paren pari parbo parben parchi je jeno kotha kothar dorkar
    shanto muhurte muhurto somoy shomoy mone hoyto uchit hote pare pore ekhon tokhon jokhon kokhono
    ei oi sei eta ota seta segulo egulo ache achen achi chilam chilen thakben thakle korun korben korle
    kore korcho korchen bujhte bujhben bujhi chai chan chacche lagche lagbe lage dekha dekhe dekhen
    shuna shunte shunun diye niye sathe theke porjonto kintu tai karon keu kichui ekdom sudhu shudhu
    apni apnar apnake tomar tumi tomake amra amader nijer nije bhalobase kemne kivabe
    oke bhoy dekhabo jate ashe ajke kon kinbo
    """.split()
)

# Small, curated Banglish/Bangla → English expansion dictionary used for lexical
# retrieval when query expansion is enabled. It never replaces the user's words; it only
# adds terms. Every entry is a direct translation, not an interpretation.
EXPANSION_DICTIONARY: dict[str, list[str]] = {
    # Banglish
    "bhalobasha": ["love", "ভালোবাসা"],
    "valobasha": ["love", "ভালোবাসা"],
    "bhalobashi": ["love"],
    "valobashi": ["love"],
    "prem": ["love", "romance"],
    "jhogra": ["argument", "fight", "conflict", "ঝগড়া"],
    "jhgra": ["argument", "fight", "conflict"],
    "sondeh": ["suspicion", "doubt", "trust"],
    "shondeh": ["suspicion", "doubt", "trust", "সন্দেহ"],
    "sandeh": ["suspicion", "doubt", "trust"],
    "hingsha": ["jealousy", "হিংসা"],
    "hingse": ["jealousy"],
    "bisshash": ["trust", "বিশ্বাস"],
    "biswas": ["trust"],
    "bishshas": ["trust"],
    "obhiman": ["hurt", "resentment", "অভিমান"],
    "obhimaan": ["hurt", "resentment"],
    "ovimaan": ["hurt"],
    "rag": ["anger"],
    "raag": ["anger"],
    "ragi": ["anger"],
    "kosto": ["pain", "hurt", "sadness"],
    "koshto": ["pain", "hurt", "sadness"],
    "dukkho": ["sadness", "grief"],
    "kanna": ["crying"],
    "biye": ["marriage", "wedding", "বিয়ে"],
    "biya": ["marriage"],
    "biyer": ["marriage"],
    "bou": ["wife", "spouse"],
    "shami": ["husband", "spouse"],
    "swami": ["husband", "spouse"],
    "shoshur": ["in-laws", "father-in-law"],
    "shashuri": ["in-laws", "mother-in-law"],
    "sasur": ["in-laws"],
    "sasuri": ["in-laws", "mother-in-law"],
    "mittha": ["lie", "dishonesty"],
    "mitthe": ["lie", "dishonesty"],
    "thokano": ["deceive", "cheating"],
    "shune": ["listen"],
    "shuni": ["listen"],
    "shone": ["listen"],
    "shonena": ["does not listen"],
    "kotha": ["talk", "communication"],
    "bole": ["says", "talk"],
    "bolena": ["does not talk"],
    "dur": ["distance"],
    "doorotto": ["distance"],
    "somman": ["respect"],
    "shomman": ["respect"],
    "shima": ["boundary", "limit"],
    "seema": ["boundary"],
    # Bangla script
    "ভালোবাসা": ["love"],
    "ঝগড়া": ["argument", "fight", "conflict"],
    "সন্দেহ": ["suspicion", "trust"],
    "হিংসা": ["jealousy"],
    "বিশ্বাস": ["trust"],
    "অভিমান": ["hurt", "resentment"],
    "রাগ": ["anger"],
    "কষ্ট": ["pain", "hurt"],
    "বিয়ে": ["marriage"],
    "স্বামী": ["husband"],
    "স্ত্রী": ["wife"],
    "বউ": ["wife"],
    "শ্বশুর": ["in-laws"],
    "শাশুড়ি": ["in-laws", "mother-in-law"],
    "মিথ্যা": ["lie"],
    "কথা": ["talk", "communication"],
    "শোনে": ["listen"],
    "সম্মান": ["respect"],
    "দূরত্ব": ["distance"],
    "সীমা": ["boundary"],
    "সম্পর্ক": ["relationship"],
}


@dataclass(slots=True)
class LanguageAnalysis:
    detected: DetectedLanguage
    bangla_ratio: float
    banglish_ratio: float
    token_count: int
    is_code_switched: bool
    tokens: list[str] = field(default_factory=list)


def normalize_text(text: str) -> str:
    """Normalize Unicode (NFC) and whitespace without changing meaning.

    NFC (not NFKC) is used so Bangla characters and punctuation such as the dari (।)
    are preserved exactly; NFKC could alter compatibility characters.
    """
    text = unicodedata.normalize("NFC", text)
    text = CONTROL_RE.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


def analyze_language(text: str) -> LanguageAnalysis:
    tokens = tokenize(text)
    if not tokens:
        return LanguageAnalysis(DetectedLanguage.UNKNOWN, 0.0, 0.0, 0, False, tokens)

    bangla = sum(1 for t in tokens if BENGALI_RE.match(t))
    latin_tokens = [t for t in tokens if LATIN_RE.match(t)]
    banglish = sum(1 for t in latin_tokens if t in BANGLISH_LEXICON)
    total = len(tokens)
    bangla_ratio = bangla / total
    banglish_ratio = banglish / max(len(latin_tokens), 1)

    if bangla_ratio >= 0.85:
        detected = DetectedLanguage.BN
    elif bangla and latin_tokens:
        detected = DetectedLanguage.MIXED
    elif latin_tokens and (banglish_ratio >= 0.3 or (banglish >= 2 and banglish_ratio >= 0.2)):
        detected = DetectedLanguage.BANGLISH
    elif latin_tokens:
        detected = DetectedLanguage.EN
    else:
        detected = DetectedLanguage.UNKNOWN

    code_switched = detected == DetectedLanguage.MIXED or (
        detected == DetectedLanguage.BANGLISH and banglish_ratio < 0.7
    )
    return LanguageAnalysis(detected, round(bangla_ratio, 3), round(banglish_ratio, 3), total, code_switched, tokens)


def expand_query_terms(tokens: list[str]) -> list[str]:
    """Return additional lexical terms for BM25. Never removes the user's own words."""
    extra: list[str] = []
    seen = set(tokens)
    for token in tokens:
        for term in EXPANSION_DICTIONARY.get(token, []):
            for part in tokenize(term):
                if part not in seen:
                    seen.add(part)
                    extra.append(part)
    return extra


def response_language_for(requested: str, detected: DetectedLanguage) -> str:
    """Pick the response language. An explicit user choice always wins."""
    if requested in {"en", "bn", "banglish"}:
        return requested
    if detected == DetectedLanguage.BN:
        return "bn"
    if detected in {DetectedLanguage.BANGLISH, DetectedLanguage.MIXED}:
        return "banglish"
    return "en"


def estimate_tokens(text: str) -> int:
    """Conservative token estimate for budgeting.

    Measured with the Qwen3 tokenizer via llama-server /tokenize (2026-10-14): Bengali script costs
    about 1.04 tokens per character (spaces included), English about 0.19. We use 1.25 per Bengali
    character and 1/3.3 for everything else to stay on the safe side.
    """
    bengali = len(BENGALI_RE.findall(text))
    other = len(text) - bengali
    return int(bengali * 1.25 + other / 3.3) + 1


def output_token_allowance(language: str, base: int) -> int:
    """Bangla script needs ~5x more tokens than English for the same content, so a fixed token cap
    truncates Bangla replies. Scale the allowance by response language."""
    factor = {"bn": 2.5, "banglish": 1.3}.get(language, 1.0)
    return min(int(base * factor), 2048)


# Second-person address forms. Bangla has a respectful (apni) and a familiar (tumi) "you"; replies
# should use one consistently. Quoted speech is ignored because suggested wording to a partner
# ("Tumi jokhon…") legitimately uses tumi inside an apni reply.
APNI_FORMS = frozenset("apni apnar apnake apnara apnader apnio আপনি আপনার আপনাকে আপনারা আপনাদের".split())
TUMI_FORMS = frozenset("tumi tomar tomake tomay tomra tomader tmi tmr তুমি তোমার তোমাকে তোমায় তোমরা তোমাদের".split())
# Quotes may span lines (suggested scripts often run over several sentences) but are length-capped so an
# unmatched quote mark cannot swallow the rest of a reply.
QUOTED_RE = re.compile(r'"[^"]{0,600}"|“[^”]{0,600}”|‘[^’]{0,600}’|«[^»]{0,600}»')


def address_form_counts(text: str) -> tuple[int, int]:
    """(apni-form count, tumi-form count) outside quoted speech."""
    tokens = [t.lower() for t in TOKEN_RE.findall(QUOTED_RE.sub(" ", normalize_text(text)))]
    return sum(t in APNI_FORMS for t in tokens), sum(t in TUMI_FORMS for t in tokens)


def user_address_form(text: str) -> str:
    """'tumi' only when the user clearly writes in the familiar register; otherwise respectful 'apni'."""
    apni, tumi = address_form_counts(text)
    return "tumi" if tumi > apni else "apni"
