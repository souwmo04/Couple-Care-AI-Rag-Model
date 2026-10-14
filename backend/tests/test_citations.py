from __future__ import annotations

from app.retrieval.citations import build_source_cards, format_context, validate_citations
from app.retrieval.retriever import RetrievalParams


def test_valid_citations_are_kept_and_recorded() -> None:
    check = validate_citations("Take a break [S1]. Listen first [S2].", available=2)
    assert check.text == "Take a break [S1]. Listen first [S2]."
    assert check.cited_ids == ["S1", "S2"]
    assert check.removed_markers == 0


def test_fabricated_citations_are_removed() -> None:
    check = validate_citations("Studies show this [S7]. Also true [S1].", available=2)
    assert "[S7]" not in check.text
    assert check.text == "Studies show this. Also true [S1]."
    assert check.removed_markers == 1
    assert check.cited_ids == ["S1"]


def test_grouped_and_variant_markers() -> None:
    check = validate_citations("Both apply [S1, S3]. See [Source 2].", available=2)
    assert check.text == "Both apply [S1]. See [S2]."
    assert check.cited_ids == ["S1", "S2"]
    assert check.removed_markers == 1


def test_no_sources_means_all_markers_removed() -> None:
    check = validate_citations("General advice [S1].", available=0)
    assert check.text == "General advice." and check.cited_ids == []


def test_source_cards_only_for_retrieved_passages(container) -> None:
    result = container.retriever.search("reflective listening calm moment", RetrievalParams(final_k=2))
    cards = build_source_cards(result.items, ["S1"])
    assert [c.citation_id for c in cards] == ["S1", "S2"][: len(cards)]
    assert cards[0].cited is True
    assert all(not c.cited for c in cards[1:])
    chunk_ids = {i.passage.chunk_id for i in result.items}
    assert {c.chunk_id for c in cards} == chunk_ids
    assert cards[0].synthetic is True and cards[0].license == "CC0-1.0"


def test_source_card_preserves_provenance(container) -> None:
    result = container.retriever.search("jealousy late-night texting", RetrievalParams(final_k=1))
    card = build_source_cards(result.items, [])[0]
    assert card.document_id == "test-jealousy"
    assert card.url == "https://example.org/jealousy"
    assert card.organization == "Test fixtures"


def test_context_labels_match_card_ids(container) -> None:
    result = container.retriever.search("reflective listening", RetrievalParams(final_k=2))
    context = format_context(result.items)
    for card in build_source_cards(result.items, []):
        assert f"[{card.citation_id}]" in context
    assert "synthetic example" in context
