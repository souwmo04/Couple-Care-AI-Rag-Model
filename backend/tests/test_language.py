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
