# Generation model selection

**Status (2026-10-15):** the default candidate has been downloaded (SHA-256 verified),
run locally on the target laptop and benchmarked. Measured results are below. Bangla quality
has only been inspected informally; a native-speaker review is still required.

## Constraints

- Windows 11, NVIDIA RTX 4060 Laptop GPU (8 GB VRAM, driver 592.00 verified with `nvidia-smi`)
- llama.cpp `llama-server` with an OpenAI-compatible endpoint
- 3B–4B instruction model, quantized GGUF, must leave headroom for the KV cache
- Embeddings run on CPU (PyTorch CPU wheel), so the GPU is reserved for generation

## Candidates (verified metadata)

| Candidate | Weights repo @ revision | GGUF source @ revision | Licence | Q4_K_M size |
|---|---|---|---|---|
| **Qwen3-4B-Instruct-2507** (default) | `Qwen/Qwen3-4B-Instruct-2507` @ `cdbee75f17c0` | `unsloth/Qwen3-4B-Instruct-2507-GGUF` @ `a06e946bb6b6` (community conversion) | Apache-2.0 | 2.50 GB |
| Qwen3-4B (hybrid thinking) | `Qwen/Qwen3-4B` | `Qwen/Qwen3-4B-GGUF` @ `bc640142c66e` (**official** Qwen GGUF) | Apache-2.0 | 2.50 GB |
| Qwen3.5-4B (compared, not default) | `Qwen/Qwen3.5-4B` @ `851bf6e8` | `unsloth/Qwen3.5-4B-GGUF` @ `e87f1764` (community conversion; text weights only) | Apache-2.0 | 2.74 GB |
| Gemma 3 4B Instruct | — | — | Gemma Terms of Use (must be reviewed and accepted) | not evaluated |
| Llama 3.2 3B Instruct | — | — | Llama 3.2 Community License (must be reviewed and accepted) | not evaluated |

Notes:

- **No official Qwen GGUF exists for Qwen3-4B-Instruct-2507** (checked via the Hugging Face
  API on 2026-10-14). The default therefore uses a community conversion pinned by revision,
  and the download script verifies each file's SHA-256 against the value Hugging Face reports.
  If you prefer an official artefact, use `Qwen/Qwen3-4B-GGUF`; its "thinking" output is
  stripped by the backend (`strip_reasoning`) and never shown to users.
- Qwen3-4B-Instruct-2507 is a non-thinking instruct model, which suits short, warm replies.
- `Qwen3.5-4B` was compared on 2026-10-15 (see below and `research/results_log.md`). It is served with
  `--reasoning off`; Qwen recommends a presence penalty of 1.5, available as
  `scripts\start-model.ps1 -ModelFile Qwen3.5-4B-Q4_K_M.gguf -PresencePenalty 1.5`.
- llama.cpp applies the chat template embedded in the GGUF (`--jinja`), so the backend does
  not hard-code any model family's template.

## VRAM budget (planning estimate; see measured values below)

Q4_K_M weights ≈ 2.5 GB. With `-c 4096` the KV cache for a 4B model is a few hundred MB, so a
full GPU offload (`-ngl 99`) is expected to fit in 8 GB. If llama-server reports
out-of-memory, the backend surfaces an actionable error; lower `-ngl` or `-c` in
`scripts/start-model.ps1`.

## Measured on the target laptop (2026-10-15)

llama.cpp b11603 (CUDA 12.4 build), `Qwen3-4B-Instruct-2507-Q4_K_M.gguf`, full GPU offload
(`-ngl 99`), single slot. `scripts/benchmark_model.py --runs 3`, 300 max tokens, no system prompt.

| Measure | English | Bangla | Banglish |
|---|---|---|---|
| Generation speed (median) | 79.8 tok/s | 80.1 tok/s | 80.8 tok/s |
| Wall time for the reply (median) | 3.91 s | 3.93 s | 2.85 s |

- VRAM in use: ~3.3 GB at 4k context, ~3.8 GB at 8k context (of 8 GB). GPU use confirmed: the
  server process is listed by `nvidia-smi --query-compute-apps`.
- **Tokenisation cost:** Bangla script ≈ 1.04 tokens per character vs ≈ 0.19 for English
  (measured with `/tokenize`), i.e. about 5–6× more tokens for the same content. Bangla replies
  therefore take longer end-to-end (a grounded Bangla reply took 10.4 s vs 3.9 s in English),
  and token budgets are now computed per script (`estimate_tokens`, `output_token_allowance`).
- Context raised to 8192 tokens so four Bangla passages, history and a Bangla reply fit.

### Qualitative observations (informal, not an evaluation)

| Language | Raw model (no system prompt / retrieval) | Through the CoupleCare pipeline |
|---|---|---|
| English | Good, warm, practical | Excellent: grounded, valid citations, concrete example wording |
| Bangla | Grammatical but partly semantically garbled | Natural and well grounded; leans heavily on retrieved wording |
| Banglish | Poor: misread *diner* ("of the day") as "dinner", repetitive, emojis, "bro" | Usable but drifts into English and contains some garbled phrases |

Banglish generation quality is the weakest point of the current model and needs either a
stronger model, few-shot examples in the prompt, or transliteration to Bangla script before
generation — to be tested as ablations.

## Still to do before calling the default "selected"

1. ~~Download and run locally; confirm GPU offload.~~ Done 2026-10-15.
2. ~~Measure tokens/s and VRAM.~~ Done; time-to-first-token not yet measured separately.
3. Run the evaluation dev split in English, Bangla and Banglish (A–D runs in `research/results_log.md`);
   have native Bangla speakers review fluency.
4. ~~Repeat for at least one alternative candidate.~~ Qwen3.5-4B compared 2026-10-15: faster (p50 10.7 s vs
   13.1 s), lighter (~3.1 GB vs ~3.8 GB VRAM) and keeps "apni" consistently in Banglish (2–4/20 mixed vs 13/20),
   but repeats sentences (6–13/20 replies), asks questions in half of ordinary answers (0.51 vs 0.32) and is not
   clearly better in Bangla/Banglish quality. **Default unchanged.** Gemma 3 / Llama 3.2 need their licences
   reviewed and accepted by the operator before download.
