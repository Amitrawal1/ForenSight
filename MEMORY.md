# ForenSight — Project Memory

> **Read this first in every session.** This file is the single source of truth for
> *what* we are building, *why* each decision was made, *how* things are wired, and
> *what happened* so far. Append to the **History Log** at the end of every work session.
> Newest log entries go at the bottom.

---

## 1. What is ForenSight?

**Explainable multi-signal deepfake forensics for images, videos and audio.**

A web platform where a normal (non-technical) user uploads an image, video or audio file
and gets a clear verdict **plus the reasons**:

| Verdict            | Meaning                                                                 |
|--------------------|-------------------------------------------------------------------------|
| Likely Authentic   | No significant signs of AI generation or manipulation.                  |
| AI-Generated       | The whole content appears to be created by an AI model.                 |
| Manipulated        | Real content, but part of it changed (face swap, edited region, lip-sync, cloned voice segment). |
| Inconclusive       | Evidence is weak or mixed — we do **not** force a guess.                |

Source: hackathon idea submission → `docs/proposal.pdf`
(original: `~/Desktop/Forensight Forensics Hackathon Submission.pages`).

> Naming note: the proposal text says "TruthLens" in a few places (sections 2.1, 5, 6).
> That is a leftover from an earlier name. **The project name is ForenSight.**

## 2. Why are we building it? (the problem)

- Voice-clone scam calls (fake family member / bank officer asking for money).
- Fake videos of celebrities, leaders, CEOs promoting fake schemes.
- Edited images/videos spreading on WhatsApp & social media.
- Face-swapped videos used to cheat online KYC.

Existing detectors are research tools: one media type, a bare score like "0.83 fake",
no reason, hard to use. **ForenSight's bet: a reason matters more than a score.**

## 3. Core design idea — why "multiple checks instead of one model"

1. **Harder to fool** — an attacker must beat several independent signals, not one classifier.
2. **Explainable by construction** — each detector reports *what it found and where*,
   so the final explanation is just the list of detectors that fired.
3. **Future-proof** — new generators appear constantly; we add/replace a detector
   without rewriting the system (plugin-style `detectors/` package).
4. **Honest uncertainty** — when detectors disagree or are weak, fusion returns
   *Inconclusive* instead of guessing.

## 4. Pipeline (how a file flows)

```
Upload ─► Preprocessing ─► Detectors (parallel) ─► Fusion ─► Explanation ─► Report/History
          file type,        image / video /         one verdict   heatmaps,      PDF + DB row
          faces, frames,    audio / metadata        + confidence  timelines,
          audio chunks                                            plain reasons
```

| Step | Code location |
|------|---------------|
| Upload API | `backend/app/api/routes/analysis.py` |
| Job queue (long videos) | `backend/app/workers/tasks.py` (Celery + Redis) |
| Preprocessing | `backend/app/pipeline/preprocessing/` |
| Detectors | `backend/app/pipeline/detectors/{image,video,audio,metadata}/` |
| Detector contract | `backend/app/pipeline/detectors/base.py` |
| Fusion → verdict | `backend/app/pipeline/fusion/combiner.py` |
| Explanations | `backend/app/pipeline/explain/` |
| PDF report | `backend/app/reports/pdf_report.py` (ReportLab) |
| History | MySQL table `analyses` (`backend/app/db/models.py`) |

### Detection modules (from proposal §2.3)

| Module   | Checks | Detects |
|----------|--------|---------|
| Image    | CNN/ViT real-vs-fake; FFT frequency artifacts of generators; ELA + noise residual for edited regions | Synthetic faces, AI images, splicing |
| Video    | Per-frame face analysis; temporal flicker; blink rate, head pose, lighting; lip-sync vs speech | Face swap, lip-sync fakes, edited video |
| Audio    | Spectrogram + anti-spoofing model; unnatural tone, missing breaths, abrupt cuts | Voice cloning, TTS, spliced audio |
| Metadata | EXIF camera info, editing-software traces, C2PA content credentials | Edited files, AI-tool exports |

### Explanation outputs (proposal §2.4)
Heatmap overlay on images · fake-segment timeline for video/audio · plain-language
reasons ("Lip movement does not match voice 0:12–0:18") · confidence % with Inconclusive band.

## 5. Tech stack & why

| Part | Choice | Why |
|------|--------|-----|
| Frontend | React + Vite + Tailwind CSS | Fast dev server, simple utility styling; charts/waveform libs added later (e.g. Recharts, wavesurfer.js). |
| Backend | Python 3.11 + FastAPI | Same language as the ML code; async upload handling; auto OpenAPI docs at `/docs`. |
| ML | PyTorch, OpenCV, Librosa, Hugging Face pretrained models | Standard ecosystem; start from pretrained checkpoints, fine-tune on the datasets below. |
| Background jobs | Celery + Redis | Video analysis takes seconds–minutes; must not block the HTTP request. |
| Database | MySQL 8 | Stated in proposal; stores analysis history (thumbnail, verdict, date, evidence JSON). |
| Report | ReportLab | Pure-Python PDF generation. |
| Deployment | **Docker + docker compose** | One command brings up everything identically on any machine / for judges. |

## 6. Docker setup — how and why

**Everything runs in Docker** (user requirement). Nothing needs to be installed on the
host except Docker Desktop.

| Service    | Image / build | Port | Purpose |
|------------|---------------|------|---------|
| `frontend` | `./frontend/Dockerfile` (node:20-alpine, Vite dev server) | 5173 | UI |
| `backend`  | `./backend/Dockerfile` (python:3.11-slim + ffmpeg, libgl) | 8000 | FastAPI API |
| `worker`   | same image as backend, runs `celery worker` | – | Runs the heavy pipeline |
| `redis`    | `redis:7-alpine` | 6379 (internal) | Celery broker + result backend |
| `mysql`    | `mysql:8.4` | 3306 (internal) | History DB |
| `ml` (profile `ml`) | `./ml/Dockerfile` | 8888 | Jupyter for training/experiments; only starts with `--profile ml` |

Decisions:
- **Backend and worker share one image** → identical code & deps, no drift.
- **ML deps are opt-in** (`INSTALL_ML=true` build arg) → the default image stays small and
  builds fast while we are still wiring the skeleton. Torch is ~1–2 GB.
- **Shared `./storage` volume** between backend and worker → worker reads the uploaded file
  and writes heatmaps/reports where the API can serve them.
- **`./models` mounted read-only** into backend/worker → trained weights are dropped in
  without rebuilding images.
- **Source code bind-mounted + auto-reload** in dev → edit on host, see changes instantly.
- **Healthchecks + `depends_on: condition: service_healthy`** → backend waits for MySQL to
  be ready (MySQL takes ~20 s on first boot).
- **Training is NOT run by Claude.** Claude writes training code and gives the commands;
  the user runs them locally / in the `ml` container.

### Everyday commands
```bash
cp .env.example .env          # first time only
docker compose up --build     # start everything
docker compose logs -f worker # watch the pipeline
docker compose down           # stop (add -v to wipe DB)
docker compose --profile ml up ml   # Jupyter for ML work → http://localhost:8888
```
URLs: UI http://localhost:5173 · API docs http://localhost:8000/docs

## 7. Datasets (proposal §2.7) — stored in `data/raw/` (git-ignored)

| Media | Datasets |
|-------|----------|
| Images | FaceForensics++, Celeb-DF, CIFAKE, GenImage |
| Video  | DFDC, Celeb-DF v2 |
| Audio  | ASVspoof 2019 / 2021, WaveFake, In-the-Wild |

Several (FF++, Celeb-DF, DFDC, ASVspoof) require a request form / license agreement —
apply early.

## 8. Limitations & responsible use
- Brand-new generators may slip through until models are updated.
- Heavy compression (WhatsApp forwards) lowers accuracy.
- ForenSight supports human decisions; it does not replace them.
- Uploads are private; user can delete anytime.

## 9. Folder map

```
ForenSight/
├── MEMORY.md            ← this file
├── CLAUDE.md            ← instructions for Claude sessions (points here)
├── README.md            ← quick start
├── docker-compose.yml   ← all services
├── .env.example         ← copy to .env
├── docs/                ← proposal.pdf, architecture notes
├── backend/             ← FastAPI + Celery + pipeline
│   └── app/
│       ├── api/routes/      health, analysis endpoints
│       ├── core/            config, celery app
│       ├── db/              SQLAlchemy session + models
│       ├── schemas/         Pydantic request/response models
│       ├── services/        file storage helpers
│       ├── workers/         Celery tasks
│       ├── pipeline/
│       │   ├── preprocessing/   file type, faces, frames, audio chunks
│       │   ├── detectors/       base + image/video/audio/metadata
│       │   ├── fusion/          combine scores → verdict
│       │   └── explain/         heatmaps, timelines, reasons
│       └── reports/         PDF generation
├── frontend/            ← React + Vite + Tailwind
├── ml/                  ← training code, configs, notebooks, evaluation
├── data/                ← datasets (git-ignored)
├── models/              ← trained weights (git-ignored)
└── storage/             ← uploads + generated reports (git-ignored)
```

## 10. Roadmap

- [x] **Phase 0 — Skeleton**: folder structure, Docker compose, health endpoint, memory file.
- [ ] **Phase 1 — Upload → result loop with heuristics only**: upload API, DB row, Celery
      task, metadata detector (EXIF/C2PA), image ELA + FFT detectors, fusion, result page.
- [ ] **Phase 2 — Pretrained image model** (HF checkpoint) + Grad-CAM heatmap.
- [ ] **Phase 3 — Audio**: spectrogram anti-spoofing model + segment timeline.
- [ ] **Phase 4 — Video**: frame sampling, face crops, temporal checks, lip-sync.
- [ ] **Phase 5 — Explanations & PDF report**, history page.
- [ ] **Phase 6 — Fine-tuning** on datasets, evaluation metrics, demo polish.

## 11. Open questions
- Which exact HF checkpoints to start from for image / audio? (decide in Phase 2/3)
- Auth/user accounts needed for the hackathon demo, or single-user history?
- Link upload ("paste a link") — which sites? yt-dlp? (legal/ToS check)
- Hackathon deadline? → fill in here.

---

## 12. History Log

### 2026-10-13 — Session 1: project bootstrap
- **What**: Read the hackathon submission (`.pages` + PDF). Created `ForenSight/` folder
  structure, this MEMORY.md, CLAUDE.md, README, docker-compose with frontend, backend,
  worker, redis, mysql and an opt-in `ml` profile. Backend skeleton: FastAPI app with
  `/api/health`, DB model `analyses`, Celery app + placeholder task, detector base class,
  fusion combiner with an explicit Inconclusive band. Frontend: Vite + React + Tailwind
  upload page that calls the health endpoint.
- **Why**: User asked to start with structure + a single memory file holding all history
  and reasoning, with everything running in Docker.
- **Notes**: Docker was **not installed** on the Mac at this time → install Docker Desktop
  before first `docker compose up`. Nothing has been built/run yet.
- **Next**: Phase 1 — real upload endpoint + metadata & image heuristic detectors.
