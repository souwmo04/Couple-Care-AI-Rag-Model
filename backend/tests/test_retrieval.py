"""Deterministic retrieval tests on the synthetic test corpus (hashing embedder + BM25)."""

from __future__ import annotations

import numpy as np

from app.retrieval.bm25 import BM25Index
from app.retrieval.embeddings import HashingEmbedder
from app.retrieval.hybrid import Calibration, reciprocal_rank_fusion
from app.retrieval.retriever import RetrievalParams
from app.retrieval.vector_store import VectorStore


def top_doc(container, query: str, **kwargs) -> str | None:
    result = container.retriever.search(query, RetrievalParams(final_k=3, **kwargs))
    return result.items[0].passage.document_id if result.items else None


def test_english_query_finds_listening_document(container) -> None:
    assert top_doc(container, "my partner feels unheard, how do I do reflective listening") == "test-listening"


def test_inlaw_query_finds_inlaw_document(container) -> None:
    assert top_doc(container, "my mother-in-law criticises my household") == "test-inlaws"


def test_bangla_query_finds_bangla_document(container) -> None:
    assert top_doc(container, "ঝগড়া খুব উত্তপ্ত হয়ে যায়, বিরতি নেব কীভাবে") == "test-jhogra-bn"


def test_banglish_query_finds_banglish_document(container) -> None:
    assert top_doc(container, "partner er sathe durotto, kachakachi ashbo kivabe") == "test-durotto-banglish"


def test_banglish_expansion_reaches_english_document(container) -> None:
    result = container.retriever.search(
        "shashuri amar songshar niye kotha bole", RetrievalParams(final_k=5, mode="bm25")
    )
    assert "test-inlaws" in [i.passage.document_id for i in result.items]
    assert "in" in result.expanded_terms or "laws" in result.expanded_terms


def test_off_topic_query_has_no_relevant_passages(container) -> None:
    result = container.retriever.search("zzqx flurble wibble", RetrievalParams(final_k=3))
    assert result.relevant == []


def test_empty_index_returns_no_results(container) -> None:
    container.retriever.set_bundle(None)
    result = container.retriever.search("anything", RetrievalParams())
    assert result.items == [] and "index_missing" in result.notes


def test_dense_mode_falls_back_when_embedder_mismatched(container) -> None:
    holder = container.embedder
    holder.set_embedder(HashingEmbedder(dimension=64), "fallback")  # different model name/dimension
    result = container.retriever.search("reflective listening", RetrievalParams(mode="dense"))
    assert result.mode == "bm25" and "dense_unavailable" in result.notes


def test_language_and_topic_filters(container) -> None:
    result = container.retriever.search("partner", RetrievalParams(final_k=10, threshold=0, language_filter="bn"))
    assert all(i.passage.language == "bn" for i in result.items)
    result = container.retriever.search(
        "partner trust", RetrievalParams(final_k=10, threshold=0, topic_filter="trust_jealousy")
    )
    assert all(i.passage.topic == "trust_jealousy" for i in result.items)


def test_rrf_orders_by_combined_rank() -> None:
    fused = reciprocal_rank_fusion([(1, 0.9), (2, 0.8)], [(2, 9.0), (3, 5.0)], calibration=Calibration())
    assert fused[0].index == 2  # appears in both lists
    assert {h.index for h in fused} == {1, 2, 3}


def test_weighted_rrf_can_rank_by_dense_alone() -> None:
    dense = [(1, 0.9), (2, 0.8)]
    lexical = [(2, 9.0), (3, 7.0)]
    plain = [h.index for h in reciprocal_rank_fusion(dense, lexical)]
    dense_first = [h.index for h in reciprocal_rank_fusion(dense, lexical, lexical_weight=0.0)]
    assert plain[0] == 2  # in both lists
    assert dense_first == [1, 2, 3]  # dense order; lexical-only candidate kept, ranked last


def test_lexical_relevance_is_absolute_not_relative() -> None:
    cal = Calibration()
    weak = reciprocal_rank_fusion([], [(0, 0.5)], calibration=cal)
    assert weak[0].relevance < 0.35  # a weak best match must not look relevant


def test_vector_store_roundtrip(tmp_path) -> None:
    emb = HashingEmbedder()
    vecs = emb.embed_passages(["alpha beta", "gamma delta"])
    store = VectorStore(vecs.shape[1])
    store.add(vecs)
    store.save(tmp_path / "v.faiss")
    loaded = VectorStore.load(tmp_path / "v.faiss")
    hits = loaded.search(emb.embed_queries(["alpha beta"])[0], 1)
    assert hits[0][0] == 0
    scores = loaded.score_ids(emb.embed_queries(["gamma delta"])[0], [0, 1])
    assert scores[1] > scores[0]


def test_hashing_embedder_is_deterministic_and_normalized() -> None:
    emb = HashingEmbedder()
    a = emb.embed_queries(["ভালোবাসা and trust"])
    b = emb.embed_queries(["ভালোবাসা and trust"])
    assert np.allclose(a, b)
    assert abs(float(np.linalg.norm(a[0])) - 1.0) < 1e-5


def test_bm25_handles_empty_corpus() -> None:
    assert BM25Index([]).search(["x"], 3) == []


def _audience_hits():
    from app.retrieval.hybrid import FusedHit
    from app.retrieval.passages import Passage

    passages = [
        Passage("a::0", "general", "text", "General", "en", "communication"),
        Passage(
            "b::0", "meeting", "text", "Meeting someone", "en", "dating_commitment", extra={"audience": ["single"]}
        ),
    ]
    # The audience-tagged document starts ranked first.
    return passages, [FusedHit(1, rrf=0.030, relevance=0.8), FusedHit(0, rrf=0.025, relevance=0.7)]


def test_audience_documents_demoted_for_people_in_a_relationship() -> None:
    from app.retrieval.retriever import _apply_audience

    passages, hits = _audience_hits()
    ranked = _apply_audience(hits, passages, "married", "How do we stop arguing?")
    assert [h.index for h in ranked] == [0, 1] and ranked[1].relevance == round(0.8 * 0.6, 4)
    passages, hits = _audience_hits()
    ranked = _apply_audience(hits, passages, "unspecified", "My boyfriend never listens")  # partner word
    assert [h.index for h in ranked] == [0, 1]


def test_audience_documents_kept_or_boosted_for_singles() -> None:
    from app.retrieval.retriever import _apply_audience

    passages, hits = _audience_hits()
    assert [h.index for h in _apply_audience(hits, passages, "single", "How do I ask her out?")] == [1, 0]
    passages, hits = _audience_hits()
    unchanged = _apply_audience(hits, passages, "unspecified", "How do I start talking to someone I like?")
    assert [h.index for h in unchanged] == [1, 0] and unchanged[0].relevance == 0.8
