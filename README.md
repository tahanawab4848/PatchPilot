# PatchPilot — Self-Healing Software Engineer

> From failing tests to verified fixes.

PatchPilot is an autonomous debugging tool built for the **NVIDIA × Nebius Hackathon**. It accepts a repository and a bug description, reproduces the failure in an isolated sandbox, asks **NVIDIA Nemotron** (via Nebius Token Factory) to diagnose the root cause and propose a minimal patch, then runs real tests to prove whether the fix works — before reporting an evidence-backed result.

---

## Problem Statement

Debugging is expensive. Developers context-switch between error traces, test output, and source code, spending hours narrowing down root causes manually. Automated tools either hallucinate fixes without running tests, or run static analysis without understanding the intent behind the code.

PatchPilot closes that gap: the model reasons; the sandbox executes; the verification service determines the outcome.

---

## Solution Overview

1. **Upload** a ZIP archive or select the bundled demo project.
2. **Describe** the bug (or point to a failing test).
3. **Investigate** — PatchPilot indexes the repo, reproduces the failure in Docker, and collects diagnostic evidence.
4. **Diagnose** — NVIDIA Nemotron (via Nebius) analyzes the evidence and proposes a minimal patch.
5. **Review** — the user inspects the unified diff and approves or rejects.
6. **Verify** — the patch is applied to an isolated workspace; the test suite runs; results are compared to the baseline.
7. **Report** — an evidence-backed repair report shows exactly what was fixed, what tests pass, and any remaining warnings.

---

## Key Features

- Real sandbox execution via Docker (not simulated).
- NVIDIA Nemotron (Llama-3.1-Nemotron-70B-Instruct-HF) for diagnosis and patch generation.
- Strict human approval gate before any patch is applied.
- Unified diff patch review with syntax highlighting.
- Persistent job history (SQLite).
- Live investigation timeline with per-stage event log.
- Path-traversal and shell-injection protection throughout.
- Typed Python (FastAPI + Pydantic) backend, TypeScript (Next.js) frontend.

---

## Architecture

```
Browser
  │
  ▼
Next.js frontend  (TypeScript, Tailwind, App Router)
  │
  ▼
FastAPI backend  (Python 3.11+, Pydantic, SQLAlchemy)
  │
  ├── RepositoryService    — validates ZIP archives, indexes source files
  ├── JobService           — persistent lifecycle + event log (SQLite)
  ├── ToolRegistry         — bounded diagnostic tools (read, search, list, manifest)
  ├── NemotronClient       — OpenAI-compatible Nebius Token Factory client
  │      └── nvidia/Llama-3.1-Nemotron-70B-Instruct-HF  (Apache 2.0)
  ├── PatchService         — validates unified diffs, applies patches safely
  ├── ExecutionService     — Docker sandbox with resource limits & fail-closed security
  └── VerificationService  — compares baseline vs post-patch test results & computes metrics
```

### Agent lifecycle

| Stage | What happens |
|---|---|
| `queued` | Job created, waiting to start |
| `analyzing` | Repository indexed, languages and test frameworks detected |
| `reproducing` | Failing test or bug confirmed in sandbox |
| `diagnosing` | Nemotron produces root-cause hypotheses from evidence |
| `patch_proposed` | Minimal unified diff generated and validated |
| `awaiting_approval` | **User must approve before anything is applied** |
| `applying_patch` | Patch applied to a clean isolated workspace copy |
| `verifying` | Test suite re-run; results compared to baseline |
| `completed` / `failed` | Evidence-backed result recorded |

---

## NVIDIA and Nebius Integration

| Item | Detail |
|---|---|
| Model | `nvidia/Llama-3.1-Nemotron-70B-Instruct-HF` |
| License | Apache 2.0 |
| Provider | Nebius Token Factory (OpenAI-compatible endpoint) |
| Endpoint | `https://api.studio.nebius.ai/v1` |
| Client | `openai` Python library, pointed at the Nebius base URL |
| Used for | Root-cause diagnosis, patch generation, test-plan generation |
| Validation | Every model response is validated before use; JSON mode used for structured outputs |

The model does **not** determine success. A repair is `verified` only when the post-patch test run produces passing results that the baseline did not.

---

## Supported Languages

| Language | Repository analysis | Sandbox execution | Test detection |
|---|---|---|---|
| Python | ✅ | ✅ (via Docker) | pytest, unittest |
| JavaScript/TypeScript | Analysis only | Not yet | — |

Additional languages can be added by extending `ExecutionService` and the test-framework detection in `RepositoryService`.

---

## Security Design

- ZIP archives are validated for path traversal before extraction.
- Sandbox containers run as `nobody`, with no network, no privileges, and a read-only root filesystem.
- All sandbox commands go through an explicit allow-list — no shell string interpolation.
- Model outputs are treated as untrusted data; paths are validated against the repository root before use.
- API keys are server-side only; never returned to the browser or written to logs.
- Patches require explicit user approval and are applied only to isolated workspace copies.

**Known limitations:**
- Docker alone is not a complete security boundary for untrusted code.
- For production use, consider gVisor, Firecracker, or a dedicated sandboxing service.
- SQLite is suitable for the MVP; a production deployment should use PostgreSQL and a durable job queue.
- No multi-user authentication in this version.

---

## Prerequisites

- Python 3.11+ (tested on 3.14)
- Node.js 18+ (tested on 24)
- Docker (required for sandbox execution)
- A Nebius API key with access to `nvidia/Llama-3.1-Nemotron-70B-Instruct-HF`

---

## Local Setup

### 1. Clone and configure environment

```bash
cd patchpilot
cp .env.example .env
# Edit .env and set NEBIUS_API_KEY
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend starts at `http://localhost:8000`.  
Swagger UI: `http://localhost:8000/docs`

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend starts at `http://localhost:3000`.

### 4. Docker Compose (optional, full stack)

```bash
docker-compose up --build
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `NEBIUS_API_KEY` | Yes | — | Nebius Token Factory API key |
| `NEBIUS_API_BASE_URL` | No | `https://api.studio.nebius.ai/v1` | Inference endpoint |
| `NEBIUS_MODEL_ID` | No | `nvidia/Llama-3.1-Nemotron-70B-Instruct-HF` | Model identifier |
| `DATABASE_URL` | No | `sqlite:///./patchpilot.db` | Database connection string |
| `ALLOWED_ORIGINS` | No | `http://localhost:3000` | CORS allowed origins |
| `SANDBOX_ENABLED` | No | `true` | Enable Docker sandbox |
| `MAX_UPLOAD_SIZE_MB` | No | `50` | Max ZIP archive size |
| `AGENT_MAX_REPAIR_ITERATIONS` | No | `3` | Retry budget for repairs |

---

## Running Tests

### Backend

```bash
cd backend
python -m pytest tests/ -v
```

Expected: **32 tests pass**.

### Frontend

```bash
cd frontend
npm run test
```

Expected: **11 tests pass**.

### Demo project (confirms the bug reproduces)

```bash
cd demo_projects/python_buggy_app
pip install pytest
pytest -v
```

Expected: 9 pass, **2 fail** (`test_divide_by_zero`, `test_divide_by_zero_message`).

---

## Demo Project

`demo_projects/python_buggy_app` contains a deliberately broken Python calculator library.

**Bug:** `divide(a, b)` returns `0.0` instead of raising `ZeroDivisionError` when `b == 0`.  
**Fix:** Change `return 0.0` to `raise ZeroDivisionError("division by zero")` in `src/calculator.py`.  
**Reference patch:** `demo_projects/python_buggy_app/known_fix.patch`

---

## Troubleshooting

| Problem | Resolution |
|---|---|
| Backend returns 404 for all routes | Check that nothing else is already on port 8000 (`netstat -ano \| findstr ":8000"`) |
| `no such table: jobs` | Run `python -m uvicorn app.main:app` once to trigger `init_db()` |
| Sandbox reports unavailable | Install Docker Desktop and ensure the Docker daemon is running |
| Nebius inference fails | Check `NEBIUS_API_KEY` is set and not the placeholder value |
| Python 3.14 pip hangs | Install dependencies one package at a time; pydantic-core wheels are available for 3.14 from PyPI |

---

## Deployment

The backend requires access to the Docker daemon for sandbox execution. A hosting platform that supports only serverless functions cannot run this application.

Recommended deployment:
- Backend: a VM or container instance with Docker installed (e.g., AWS EC2, GCP Compute Engine, DigitalOcean Droplet).
- Frontend: Vercel, Netlify, or the same VM behind nginx.
- Database: upgrade to PostgreSQL for production.

---

## Known Limitations

- Sandbox requires Docker on the backend host.
- Only Python projects are fully supported for execution and verification.
- No multi-user authentication.
- Agent runs synchronously in the background task; for scale, use Celery or similar.
- SQLite is not suitable for concurrent multi-user production workloads.

---

## Future Roadmap

- JavaScript/TypeScript project support.
- GitHub/GitLab repository import (with safe URL validation).
- Async job queue (Celery + Redis).
- Multi-user authentication.
- Interactive patch editing before approval.
- Regression test generation.
- Support for additional NVIDIA models via the same Nebius endpoint.

---

## License

MIT — see `LICENSE`.

---

## Attribution

- Model: [nvidia/Llama-3.1-Nemotron-70B-Instruct-HF](https://huggingface.co/nvidia/Llama-3.1-Nemotron-70B-Instruct-HF) — Apache 2.0
- Inference: [Nebius Token Factory / Nebius AI Cloud](https://nebius.ai)
- Built for the NVIDIA × Nebius Hackathon 2026
