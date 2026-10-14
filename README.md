# CoupleCare AI

**Understand Each Other Better.** A private, bilingual (English · বাংলা · Banglish)
relationship-support assistant that runs entirely on your own computer, using a local language
model and retrieval-augmented generation (RAG) with source citations and an independent safety layer.

> CoupleCare offers educational support. It is not therapy, diagnosis, legal advice or a crisis
> service. If you are in immediate danger, contact your local emergency number.

> **Screenshots:** _placeholder — screenshots will be added after the first full run with the local model._

## Status

| Area | State |
|---|---|
| Landing, chat, settings, knowledge, about/privacy/safety pages | Implemented, tested (Vitest + axe-core) |
| FastAPI backend, hybrid RAG, citations, safety layer, storage | Implemented, 206 backend tests passing |
| Multilingual E5 + FAISS + BM25 index | Built and measured on the synthetic corpus |
| Local generation (llama.cpp + Qwen3-4B-Instruct-2507 GGUF) | Adapter implemented and tested with a mocked server; **not yet run on real weights** |
| Evaluation framework | Retrieval and safety suites measured (see `research/results_log.md`); generation suite awaits the model |

## System requirements

- Windows 11 (macOS/Linux work with equivalent commands), Python 3.11+ (tested 3.12.10), Node.js 20+ (tested 24.15)
- ~6 GB free disk (dependencies ≈ 2 GB, embedding model ≈ 0.5 GB, GGUF ≈ 2.5 GB)
- Recommended: NVIDIA GPU with 8 GB VRAM (target: RTX 4060 Laptop). CPU-only also works, slowly.

## Install (PowerShell)

```powershell
git clone https://github.com/souwmo04/Couple-Care-AI-Rag-Model.git
cd Couple-Care-AI-Rag-Model
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

`setup.ps1` creates `.venv`, installs **CPU-only PyTorch** (so the GPU stays free for the
language model), installs pinned backend and frontend dependencies, and copies `.env.example` to `.env`.

## Download the local model

```powershell
scripts\download-model.ps1              # llama.cpp b11603 (CUDA 12.4) + Qwen3-4B-Instruct-2507 Q4_K_M (2.50 GB)
scripts\download-model.ps1 -Backend cpu # CPU-only llama.cpp build
```

The script pins the GGUF to `unsloth/Qwen3-4B-Instruct-2507-GGUF@a06e946b` and **verifies the
SHA-256** reported by Hugging Face. Licence: Apache-2.0. Qwen does not publish an official GGUF
for this release; see [docs/model-selection.md](docs/model-selection.md) for the alternatives
(including the official `Qwen/Qwen3-4B-GGUF`) and what still needs measuring.

## Build the knowledge index

```powershell
scripts\build-index.ps1                 # downloads intfloat/multilingual-e5-small on first run
```

The bundled knowledge base contains **synthetic example documents** written for development
(labelled as such everywhere). To add real sources you have permission to use, see
[data/raw/README.md](data/raw/README.md).

## Run

```powershell
scripts\start-all.ps1                   # model server + backend + frontend
# or individually:
scripts\start-model.ps1                 # 127.0.0.1:18080  (-GpuLayers 20 / -Context 2048 / -Cpu)
scripts\start-backend.ps1               # 127.0.0.1:8000  (API docs: /api/docs)
scripts\start-frontend.ps1              # 127.0.0.1:5173
scripts\stop.ps1                        # stop everything
scripts\diagnose.ps1                    # check Python, Node, deps, index, model server, GPU
```

Without a model server the app still runs and clearly shows **"AI generation offline"** — it
never substitutes canned text for model output.

## Test

```powershell
scripts\test.ps1                        # ruff + pytest (backend) and tsc + oxlint + vitest (frontend)
```

Tests never download a model: they use a deterministic hashing embedder, a fake model server and
a small synthetic corpus.

## Evaluate (research)

```powershell
.venv\Scripts\python scripts\build_eval_dataset.py
.venv\Scripts\python scripts\run_evaluation.py --split dev --suites retrieval,safety
.venv\Scripts\python scripts\run_evaluation.py --split dev --suites ablation
.venv\Scripts\python scripts\run_evaluation.py --split dev --suites generation --configs A,B,C,D   # needs the model
```

Results (JSON + CSV + manifest) go to `artifacts/evaluation_results/`. The held-out test split
requires `--final`. See [research/experimental_protocol.md](research/experimental_protocol.md).

## Configuration

All options are in [.env.example](.env.example). Host and model-server URL must be loopback
addresses. User-adjustable settings (temperature, retrieval depth, persistence, support region …)
are bounded and validated via `/api/settings`.

## Documentation

- [Architecture](docs/architecture.md) · [API](docs/api.md) · [Privacy](docs/privacy.md) ·
  [Safety policy](docs/safety_policy.md) · [Troubleshooting](docs/troubleshooting.md)
- [Model selection](docs/model-selection.md) · [Retrieval calibration](docs/retrieval-calibration.md) ·
  [Design decisions](docs/design-decisions.md) · [Project plan](PROJECT_PLAN.md)
- Research: [protocol](research/experimental_protocol.md) · [dataset card](research/dataset_card.md) ·
  [annotation guidelines](research/annotation_guidelines.md) · [related work](research/related_work.md) ·
  [results log](research/results_log.md)

## Privacy limitations

Conversations are processed locally and, by default, are not written to disk. Local processing
does not protect against malware, a compromised computer, shared accounts or physical access, and
the optional SQLite history is not encrypted. Details: [docs/privacy.md](docs/privacy.md).

## Licence

Code: MIT ([LICENSE](LICENSE)). Model weights, embedding models and third-party documents keep
their own licences.
