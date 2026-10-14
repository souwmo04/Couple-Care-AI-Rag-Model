# Related work (working notes)

> **Verify every reference against the original publication before citing it in a paper.**
> These notes list works that the implementation directly builds on; they are not yet a
> literature review. Domain literature (couple and family therapy, intimate-partner-violence
> safety planning, Bangla NLP for mental-health contexts) still needs a systematic search.

## Retrieval-augmented generation and retrieval

- Lewis, P., et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.*
  NeurIPS 2020. — The RAG formulation followed here (retrieve passages, condition generation on them).
- Karpukhin, V., et al. (2020). *Dense Passage Retrieval for Open-Domain Question Answering.*
  EMNLP 2020. — Dense bi-encoder retrieval.
- Robertson, S., & Zaragoza, H. (2009). *The Probabilistic Relevance Framework: BM25 and Beyond.*
  Foundations and Trends in Information Retrieval. — BM25 lexical retrieval (implemented via `rank-bm25`).
- Cormack, G. V., Clarke, C. L. A., & Büttcher, S. (2009). *Reciprocal Rank Fusion Outperforms
  Condorcet and Individual Rank Learning Methods.* SIGIR 2009. — RRF with k = 60 (`hybrid.py`).
- Wang, L., et al. (2024). *Multilingual E5 Text Embeddings: A Technical Report.* arXiv:2402.05672.
  — The embedding family used (`intfloat/multilingual-e5-small`), including the `query:` /
  `passage:` prefix convention.

## Evaluation

- Järvelin, K., & Kekäläinen, J. (2002). *Cumulated Gain-Based Evaluation of IR Techniques.*
  ACM TOIS. — nDCG.
- Cohen, J. (1960). *A Coefficient of Agreement for Nominal Scales.* Educational and
  Psychological Measurement. — Cohen's κ for annotator agreement.

## Models and tooling

- Qwen Team (2025). *Qwen3 Technical Report.* (arXiv) — the default generator family; confirm the
  exact identifier and version-specific details (2507 instruct release) before citing.
- llama.cpp (ggml-org) — local GGUF inference; cite the repository and the exact release tag used
  (recorded in `models/model.json`).

## Bangla / Banglish NLP (to expand)

- Bangla pre-trained encoders and benchmarks (e.g., BanglaBERT and related work) — to be
  reviewed for evaluation resources and for Romanized-Bangla handling.
- Transliteration between Romanized Bangla and Bengali script — candidate mitigation for the
  cross-script retrieval gap observed in `results_log.md`.

## Gaps this project could address

- Few systems evaluate RAG for relationship support in Bangla/Banglish, especially with
  code-switching.
- Safety evaluation that separates *risk detection* from *inappropriate escalation* of ordinary
  conflict across languages.
- Feasibility on 8 GB consumer GPUs with fully local processing.
