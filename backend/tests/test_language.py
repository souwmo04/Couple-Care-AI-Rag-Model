from __future__ import annotations

import pytest

from app.core.language import analyze_language, expand_query_terms, normalize_text, response_language_for, tokenize
from app.core.schemas import DetectedLanguage as L


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("My partner does not listen to me.", L.EN),
        ("আমার স্বামী আমার কথা শোনে না।", L.BN),
        ("amar bf amake ekdom time dey na, ki korbo?", L.BANGLISH),
        ("Amar wife er sathe onek jhogra hocche lately", L.BANGLISH),
        ("I feel আমি একা in this marriage", L.MIXED),
        ("", L.UNKNOWN),
        ("!!! ???", L.UNKNOWN),
    ],
)
def test_detects_language(text: str, expected: L) -> None:
    assert analyze_language(text).detected == expected


def test_code_switching_flag() -> None:
    assert analyze_language("I feel আমি একা in this marriage").is_code_switched
    assert not analyze_language("My partner does not listen to me").is_code_switched


def test_normalization_preserves_bangla_and_zwnj() -> None:
    text = "র‍্যাব  ক্ষমা।‌\r\n\r\n\r\nনতুন"
    out = normalize_text(text)
    assert "‍" in out  # ZWJ in র‍্যাব kept
    assert "‌" in out  # ZWNJ kept
    assert "।" in out
    assert "\r" not in out and "\n\n\n" not in out


def test_normalization_strips_control_characters() -> None:
    assert normalize_text("hello\x00\x07 world﻿") == "hello world"


def test_normalization_uses_nfc() -> None:
    decomposed = "é"  # e + combining acute
    assert normalize_text(decomposed) == "é"


def test_query_expansion_adds_but_never_removes() -> None:
    tokens = tokenize("onek jhogra hocche, sondeh kore")
    extra = expand_query_terms(tokens)
    assert {"argument", "conflict", "suspicion", "trust"} <= set(extra)
    assert not set(extra) & set(tokens)


def test_bangla_query_expansion() -> None:
    assert "jealousy" in expand_query_terms(tokenize("আমার হিংসা হয়"))


@pytest.mark.parametrize(
    ("requested", "detected", "expected"),
    [
        ("auto", L.BN, "bn"),
        ("auto", L.BANGLISH, "banglish"),
        ("auto", L.MIXED, "banglish"),
        ("auto", L.EN, "en"),
        ("auto", L.UNKNOWN, "en"),
        ("bn", L.EN, "bn"),
        ("en", L.BN, "en"),
    ],
)
def test_response_language_respects_explicit_choice(requested: str, detected: L, expected: str) -> None:
    assert response_language_for(requested, detected) == expected


def test_token_estimate_reflects_bangla_cost() -> None:
    from app.core.language import estimate_tokens

    bn = "প্রতি সপ্তাহে ঘরের কাজ নিয়ে ঝগড়া হওয়া একটা সাধারণ সমস্যা।"
    en = "Fighting about chores every week is a common problem."
    # Measured: Bangla ~1.04 tokens/char, English ~0.19 tokens/char; the estimate must not under-count.
    assert estimate_tokens(bn) >= len(bn)
    assert estimate_tokens(en) >= len(en) * 0.19
    assert estimate_tokens(bn) > 3 * estimate_tokens(en)


def test_output_allowance_scales_for_bangla() -> None:
    from app.core.language import output_token_allowance

    assert output_token_allowance("en", 700) == 700
    assert output_token_allowance("bn", 700) == 1750
    assert output_token_allowance("bn", 1536) == 2048  # capped


@pytest.mark.parametrize(
    "text",
    [
        "Ekta shanto muhurte bolte paren je amar kotha shuna dorkar.",
        "Apni ja feel korchen ta khub swabhabik.",
        "Tomar dik theke byapar ta kemon lagche, bolba?",
        "Ami chai amra aro kachakachi thaki.",
    ],
)
def test_common_banglish_sentences_are_detected(text: str) -> None:
    assert analyze_language(text).detected in {L.BANGLISH, L.MIXED}


@pytest.mark.parametrize(
    "text",
    [
        "This keeps it gentle and gives your partner space to respond.",
        "My partner forgets our anniversary every year and I feel hurt.",
        "At my age, I worry that we are drifting apart.",
    ],
)
def test_english_sentences_are_not_banglish(text: str) -> None:
    assert analyze_language(text).detected == L.EN
