# Troubleshooting

Start with the diagnostic: `scripts\diagnose.ps1`. It reports what it actually observes.

| Symptom | Cause | Fix |
|---|---|---|
| UI shows **"AI generation offline"** | llama-server not running / still loading | `scripts\start-model.ps1`; check `logs\model-server.err.log` |
| **"Backend not running"** | FastAPI not started | `scripts\start-backend.ps1` |
| `COUPLECARE_HOST must be a loopback address` | `.env` binds publicly | Use `127.0.0.1` (public binding is intentionally refused) |
| `COUPLECARE_LLM_BASE_URL must point to a loopback address` | Remote model URL configured | Run llama-server locally |
| Reply error mentions **GPU memory** | VRAM exhausted | `scripts\start-model.ps1 -GpuLayers 20` or `-Context 2048`; close other GPU apps |
| llama-server exits immediately | Missing CUDA runtime / old driver | Re-run `download-model.ps1` (installs cudart); update NVIDIA driver; or use `-Cpu` |
| GPU not used | CPU build downloaded, or `-Cpu` | `download-model.ps1 -Backend cuda`; confirm `offloaded N/N layers to GPU` in the log |
| Knowledge page: **"Keyword search only"** | Index built without embeddings | `scripts\build-index.ps1` (needs the E5 model download once) |
| **"Semantic search unavailable"** | Index built with a different embedder than configured | Rebuild the index |
| Rebuild returns 409 | Embedder still loading, or a rebuild is running | Wait and retry |
| First request slow | E5 loads in the background on startup (~1–2 min on CPU) | Wait for `/api/health` → `embeddings: ready` |
| `UnicodeEncodeError` in a console | Windows code page | Set `$env:PYTHONIOENCODING='utf-8'` (scripts do this) |
| HF symlink warning on Windows | Developer Mode off | Harmless; enable Developer Mode to save disk space |
| PowerShell refuses scripts | Execution policy | `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1` |
| Port already in use | Old process | `scripts\stop.ps1` |
