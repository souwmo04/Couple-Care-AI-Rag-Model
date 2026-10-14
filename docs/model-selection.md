# Generation model selection

**Status (2026-10-14):** a default *candidate* has been chosen and its metadata verified
from the Hugging Face API. Local inference, latency, memory use and Bangla quality have
**not yet been measured** on the target laptop. This document will be updated with
measured numbers; until then, nothing here is a performance claim.

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
| Gemma 3 4B Instruct | — | — | Gemma Terms of Use (must be reviewed and accepted) | not evaluated |
| Llama 3.2 3B Instruct | — | — | Llama 3.2 Community License (must be reviewed and accepted) | not evaluated |

Notes:

- **No official Qwen GGUF exists for Qwen3-4B-Instruct-2507** (checked via the Hugging Face
  API on 2026-10-14). The default therefore uses a community conversion pinned by revision,
  and the download script verifies each file's SHA-256 against the value Hugging Face reports.
  If you prefer an official artefact, use `Qwen/Qwen3-4B-GGUF`; its "thinking" output is
  stripped by the backend (`strip_reasoning`) and never shown to users.
- Qwen3-4B-Instruct-2507 is a non-thinking instruct model, which suits short, warm replies.
- A newer `Qwen/Qwen3.5-4B` also exists; it has not been reviewed.
- llama.cpp applies the chat template embedded in the GGUF (`--jinja`), so the backend does
  not hard-code any model family's template.

## VRAM budget (estimate, to be measured)

Q4_K_M weights ≈ 2.5 GB. With `-c 4096` the KV cache for a 4B model is a few hundred MB, so a
full GPU offload (`-ngl 99`) is expected to fit in 8 GB. If llama-server reports
out-of-memory, the backend surfaces an actionable error; lower `-ngl` or `-c` in
`scripts/start-model.ps1`.

## Still to do before calling the default "selected"

1. Download and run locally; confirm GPU offload in the llama-server log (`offloaded N/N layers to GPU`).
2. Measure tokens/s, time-to-first-token and peak VRAM (`nvidia-smi`) at `-c 4096`.
3. Run the evaluation dev split in English, Bangla and Banglish; have Bangla speakers review fluency.
4. Repeat for at least one alternative candidate; record results in `artifacts/evaluation_results/`.
