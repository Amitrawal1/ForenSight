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
| Upload / status / history / delete API | `backend/app/api/routes/analysis.py` |
| Upload storage (generated names, size limit) | `backend/app/services/storage.py` |
| Job queue | `backend/app/workers/tasks.py` (Celery + Redis) |
| Orchestration (detectors → fusion → explain) | `backend/app/pipeline/runner.py` |
| Preprocessing (file type by magic bytes, thumbnail) | `backend/app/pipeline/preprocessing/` |
| Detectors | `backend/app/pipeline/detectors/{image,video,audio,metadata}/` |
| Detector contract (`MediaContext`, `DetectorResult`) | `backend/app/pipeline/detectors/base.py` |
| Fusion → verdict | `backend/app/pipeline/fusion/combiner.py` |
| Explanations (templates, heatmap overlay) | `backend/app/pipeline/explain/` |
| PDF report | `backend/app/reports/` (Phase 5) |
| History | MySQL table `analyses` (`backend/app/db/models.py`) |

### API (Phase 1)

| Method & path | Purpose |
|---|---|
| `POST /api/analyses` (multipart `file`) | Save upload, detect type, create row, queue job → 201 + analysis. 413 too large, 415 unsupported |
| `GET /api/analyses` | History list (newest first) |
| `GET /api/analyses/{id}` | Status + verdict + evidence (frontend polls every 1.5 s) |
| `GET /api/analyses/{id}/original` | The uploaded file |
| `GET /api/analyses/{id}/artifacts/{name}` | `thumb.jpg`, `ela.png`, `spectrum.png` (name regex-validated) |
| `DELETE /api/analyses/{id}` | Delete file, artifacts and row |

Files on disk: uploads in `storage/uploads/<random hex>`, generated images in
`storage/artifacts/<analysis id>/`.

### Evidence JSON (stored in `analyses.evidence`)
`{summary, reasons[top 3], notes[], detectors: [{name, label, fake_score, reliability,
fake_kind, reasons[], heatmap, segments[]}]}`. `reliability = 0` means "info only" —
shown to the user, ignored by fusion.

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
- [x] **Phase 1 — Upload → result loop with heuristics only** (2026-10-14): upload API, DB row,
      Celery task, metadata + ELA + FFT detectors, fusion, explanations, upload + result pages.
- [x] **Phase 2 — Pretrained image models** (2026-10-14): Community Forensics AI-image ViT,
      DFDC face-swap EfficientNet-B7, Grad-CAM heatmaps, per-kind fusion, result-page tabs.
- [x] **Phase 3 — Audio** (2026-10-14): XLSR-SLS AI-voice model per window, splice check,
      timeline, OGG voice notes.
- [x] **Phase 4 — Video** (2026-10-14): frame sampling, per-frame face-swap + AI-image
      checks, sound-track audio checks, video metadata, video player + timeline + worst frame.
      (Lip-sync and blink/head-pose checks not done — stretch goals.)
- [x] **Phase 5 — PDF report, history page, delete** (2026-10-14).
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

### 2026-10-13 — Session 1b: Git remote + full build plan
- **Git**: `git add .` failed with "'ForenSight/' does not have a commit checked out" because an
  empty nested repo (`ForenSight/ForenSight/.git`) existed — Git treats nested repos as
  submodules. User removed it. Remote `origin` = https://github.com/Amitrawal1/ForenSight.git.
  User commits/pushes manually.
- **Build plan PDF**: `~/Desktop/ForenSight_Build_Plan.pdf` (copy in `docs/build_plan.pdf`).
  Key decisions recorded there:
  - Pretrained-first, fine-tune on Colab/Kaggle GPU, never train from scratch.
  - Build order image → audio → video (video reuses both).
  - Image: metadata/C2PA (c2pa-python), ELA, FFT residual + logistic regression,
    CLIP ViT-L/14 linear probe (UnivFD) for AI images, EfficientNet face classifier + Grad-CAM.
  - Audio: AASIST or wav2vec2/XLS-R front end; splice + prosody heuristics (low reliability).
  - Video: per-frame face classifier, temporal consistency, blink/head-pose (MediaPipe),
    SyncNet lip-sync as stretch goal.
  - Fusion: weighted average now → calibrated logistic regression later; thresholds from validation.
  - Explanations: deterministic templates (no LLM-invented evidence).
  - Split data by identity/source; compression augmentation; cross-dataset evaluation.
  - Cut line if time is short: Phases 1–3 + simple PDF, video-lite.
- **Next**: user installs Docker, applies for gated datasets; then Phase 1.

### 2026-10-14 — Session 2: Phase 1 built (upload → result loop)
**What was built**
- Backend API: upload (streams to disk, 413 over limit, type detected from bytes → 415 if
  unsupported), get, list, delete, serve original + artifacts. Schemas in `app/schemas/analysis.py`.
- DB: added `mime_type` and `error` columns; enums stored by *value* (`likely_authentic` …)
  so MySQL rows are readable. Tables are still created with `create_all` (no Alembic yet) →
  if columns change later, wipe the dev DB with `docker compose down -v` or add Alembic.
- Celery task `run_analysis`: queued → processing → done/failed (error message saved).
- `pipeline/runner.py`: runs every applicable detector; one crashing detector only adds a
  note, it doesn't fail the analysis. Video/audio are accepted but return Inconclusive with a
  "coming in Phase 3/4" note.
- Detector contract changed: `run(ctx: MediaContext) -> DetectorResult | None`
  (None = check doesn't apply, e.g. ELA on PNG). Added `label` for the UI, `heatmap` is a
  file name inside the analysis' artifact folder.
- **Metadata detector**: IPTC DigitalSourceType (`trainedAlgorithmicMedia` → AI, `composite…`
  → manipulated, strong), Stable-Diffusion PNG fields (`parameters`, `prompt`, `workflow` …,
  strong), AI tool names (strong), editor names like Photoshop (weak, 0.3 reliability —
  editing ≠ fake), camera Make/Model (weak sign of authenticity). C2PA: only *presence* is
  detected (byte search for `c2pa`) — signature verification with `c2pa-python` is TODO.
  No metadata at all → info only (reliability 0), because social media strips it.
- **ELA detector** (JPEG only): re-save at q90, per-16px-block error **divided by local
  texture** (Sobel) so busy areas don't look edited, robust z-score (median/MAD), largest
  connected cluster of outlier blocks → score. Heatmap overlay `ela.png`. Reliability 0.35
  (0.15 if the image is heavily recompressed).
- **FFT detector**: spectrum of the median-filter noise residual, each frequency compared
  with others at the same radius (z-score on log magnitude), ≥2 peaks above z=4 → AI-like.
  JPEG 8×8 grid frequencies are masked **only for JPEGs** (first version masked them for all
  images, which also hid real generator artifacts — bug found during calibration).
  Reliability 0.3 PNG/WEBP, 0.15 JPEG. Saves `spectrum.png`.
- Explanations: template sentences only; top 3 reasons are picked from detectors that agree
  with the verdict, ranked by reliability × |score − 0.5|.
- Frontend: hash routes `#/` (upload, drag-and-drop) and `#/analysis/<id>` (polls every
  1.5 s → verdict card with confidence bar + "Why" reasons, image with ELA heatmap opacity
  slider, spectrum panel, per-check evidence list).
- Tests (15, all passing locally on SQLite with `CELERY_ALWAYS_EAGER=true` via
  `tests/conftest.py`): API flow, SD-PNG → ai_generated, wrong extension detected by bytes,
  bad type 415, artifact path validation, history + delete, metadata cases, fusion.
  Run in Docker: `docker compose run --rm backend pytest`.

**Calibration (synthetic, hand-tuned — NOT real accuracy numbers)**
- Test images: scikit-image sample photos saved as JPEG q92.
- ELA: 3/5 splices (q60 patch pasted, re-saved q92) flagged; 0/5 real photos flagged as
  fake (1 landed in the inconclusive band).
- FFT: 5/5 images with an added faint period-4 checkerboard flagged; 0/10 real flagged.
  Period-2 artifacts (at the spectrum corners) are **not** detected — known limitation.
- Why it matters: with these low reliabilities most real-world images will come out
  **Inconclusive** until Phase 2 adds a learned classifier. That is intended, not a bug.

**Why this order**: metadata/ELA/FFT need no training data or GPU, so the full
upload → verdict → explanation loop could be built and tested end-to-end first.

**Not verified yet**: nothing has run inside Docker (Docker still not installed). The
frontend was checked with `vite build` only, not clicked through in a browser.

**Next (Phase 2)**: CLIP ViT-L/14 linear probe for AI images (UnivFD) + face-swap classifier
with Grad-CAM; replace hand-set thresholds once data is available.

### 2026-10-14 — Session 2b: comment style
- User asked for **simple, basic comments** so other developers can read the code easily.
  Rule added to CLAUDE.md (#7). Rewrote comments in `ela.py`, `fft.py`, `heatmap.py` in
  plain English (no unexplained jargon like MAD / z-score / residual). No logic changed;
  15 tests still pass.

### 2026-10-14 — Session 2c: Docker testing deferred
- User chose to **skip Docker setup/testing for now** and do it later. Phase 1 is still
  only verified locally (pytest on SQLite + `vite build`). Run the Docker checks before the demo.

### 2026-10-14 — Session 3: Phase 2 plan + Part 2a (ML foundation)
**New workflow (user request)**: work in parts; after each important part Claude stops,
gives a one-line commit message, and waits for "ok continue". Rule #8 in CLAUDE.md.
Subagents may be used. Co-Authored-By lines are still **not** added (global rule unchanged).

**Phase 2 parts**: 2a ML foundation · 2b AI-image detector (+ training notebook) ·
2c face-swap detector + Grad-CAM · 2d frontend updates.

**2a — what was built**
- `pipeline/models/registry.py`: `load_cached()` keeps each model in memory per worker
  process (loading is slow); `model_path()` finds a file in `models/`; `ModelNotAvailable`
  exception; `require_torch()`.
- Runner: a detector raising `ModelNotAvailable` is **skipped with a note** shown to the
  user (e.g. "check was skipped: model file … is missing") instead of failing.
- `preprocessing/faces.py`: face detection with OpenCV **YuNet**
  (`face_detection_yunet_2023mar.onnx`, 230 KB, CPU, no PyTorch). Big images are shrunk to
  1280 px for speed; `crop_face()` adds a 30 % margin because deepfake traces sit at the
  face edges (jaw, hairline).
- **Why YuNet, not facenet-pytorch (MTCNN)**: facenet-pytorch 2.6 pins old torch, numpy <2
  and Pillow <10.3, which clash with our versions. Removed facenet-pytorch and grad-cam from
  `requirements-ml.txt` (Grad-CAM will be ~30 lines with PyTorch hooks).
- `backend/scripts/download_models.py`: plain-Python downloader with SHA-256 check, run from
  the project root: `python3 backend/scripts/download_models.py`. Uses `certifi` when
  installed because python.org Python on macOS hit `CERTIFICATE_VERIFY_FAILED`; prints the fix
  otherwise. SSL verification is never disabled. Model files are git-ignored.
  Docker note: `/models` is mounted read-only, so download on the host.
- Tests: 19 passing (face found in `tests/fixtures/face.jpg` — public-domain NASA
  "astronaut" photo from scikit-image; no face in a plain image; missing model → skipped
  with note). `tests/conftest.py` points `MODELS_DIR` at the project `models/` folder.

**Next**: 2b — AI-image detector (choice depends on research of pretrained checkpoints and
whether the user has a Kaggle account for CIFAKE).

### 2026-10-14 — Session 3b: Part 2b (AI-image detector)
**Model research** (background research agent, then verified live on Hugging Face):
- **Chosen: `buildborderless/CommunityForensics-DeepfakeDet-ViT`** — re-upload of the
  Community Forensics model (Owens Lab, CVPR 2025, arXiv 2411.04125). ViT-S/16 @ 384 px,
  trained on 2.7 M images from ~4,800 generators. MIT licence, 87 MB, ~65 ms/image on CPU
  (≈6 s first load). Pinned to commit `ac6ee457…`, SHA-256 checked in `download_models.py`.
  Files saved to `models/community_forensics_vit/` (git-ignored).
  - Its preprocessor needs transformers ≥ 5.4, so we preprocess ourselves exactly as the
    model card says: short side → 440 (bicubic), centre crop 384, CLIP mean/std. Output is one
    logit → sigmoid = AI probability.
  - Warning: this repo's weights were replaced recently because the earlier upload was wrong —
    that's why we pin the commit and tested it ourselves.
- **Dropped CLIP/UnivFD** (was in the build plan): official probe only trained on ProGAN →
  likely weak on SDXL/Midjourney/Flux, and ViT-L is 1.7 GB.
- **Dropped CIFAKE** for training: images are 32×32, poor for real photos. **No Kaggle needed.**
- Face model for 2c (to verify then): DFDC-winning EfficientNet-B7 (selimsef, MIT, 267 MB,
  ~0.5 s/face CPU). No face model publishes strong cross-dataset results — say so honestly.
- Grad-CAM: do it by hand with PyTorch hooks (no extra package).

**What was built**
- `detectors/image/ai_image.py` (`AiImageDetector`, reliability 0.7, kind ai_generated).
- **Decisive findings** (new `DetectorResult.decisive`): metadata written by the AI tool
  itself (IPTC trainedAlgorithmicMedia / composite…, Stable Diffusion PNG fields) now decides
  the verdict alone. Why: a synthetic test image with SD metadata was judged "real" by the
  model and the two cancelled out to Inconclusive. Nobody adds SD settings to a real photo.
  AI tool *names* in text are NOT decisive (a human could write "not Midjourney").
- **"Found nothing" counts less**: ELA with no suspicious region → reliability 0.15; FFT with
  no peaks → 0.1. Why: otherwise two weak "nothing found" votes dragged a confident model
  score (AI = 1.0) down to Inconclusive. Absence of evidence ≠ evidence of authenticity.
- `INSTALL_ML` now defaults to **true** (.env.example + docker-compose) — the main image
  detector needs PyTorch.
- Tests: 24 passing (new fixture `tests/fixtures/ai_sd.jpg`, a CC0 DiffusionDB image saved
  as JPEG so it has no AI metadata). Model tests skip if torch/model missing.

**Evaluation (small, our own — not a benchmark)**
- Model alone: 20/20 DiffusionDB Stable Diffusion images ≥ 0.96 (still 20/20 after JPEG
  q80); 8/9 real scikit-image photos ≈ 0.00.
- Full pipeline, metadata removed: **AI 40/40 → AI-Generated**; **real 14/16 → Likely
  Authentic**, 2/16 wrong = the Hubble deep-field image (JPEG and PNG). Heavily processed
  astronomy/scientific images look "AI" to the model — known false positive, mention in demo.
- Caveat: DiffusionDB is 2022 Stable Diffusion, probably in the model's training data. Still
  need tests on newer generators (Flux, Midjourney v6+, DALL-E 3, GPT-image) and on phone
  photos / WhatsApp forwards.

**Next**: 2c — face-swap detector (EfficientNet-B7) + Grad-CAM heatmaps.

### 2026-10-14 — Session 3c: Part 2c (face-swap detector + Grad-CAM)
**Model: DFDC challenge winner** (`selimsef/dfdc_deepfake_challenge`, MIT), checkpoint
`final_111_DeepFakeClassifier_tf_efficientnet_b7_ns_0_36` (267 MB, SHA-256 in
`download_models.py`, saved as `models/dfdc_efficientnet_b7.pt`). The winner averaged 7
checkpoints; we use 1 (CPU speed). ~1.1 s per face on CPU after a ~4 s first load.
- Preprocessing copied from their `kernel_utils.py`: face box + 1/3 of its size on each
  side → resize longest side to 380 (cubic up / area down) → paste in centre of black
  380×380 → ImageNet mean/std → EfficientNet-B7 (`timm` `tf_efficientnet_b7.ns_jft_in1k`,
  forward_features → avg pool → Linear(2560,1)) → sigmoid. Weights load with `strict=True`
  (all keys match).
- Our faces come from YuNet, theirs from MTCNN → boxes differ a bit; possible small accuracy loss.
- **Safe loading**: the checkpoint can't load with `torch.load(weights_only=True)` because it
  stores one numpy number (`bce_best`). We allow exactly `numpy.core.multiarray.scalar` +
  dtype via `torch.serialization.safe_globals` — never `weights_only=False` (that would run
  arbitrary code from the file).
- Max 3 faces, min 64 px face size; no face → check doesn't apply (returns None).
- Reliability 0.5 (lower than the AI-image model: face-swap models generalise poorly).

**Grad-CAM** (`explain/gradcam.py`, own code, no package): hook a layer, take
`torch.autograd.grad(fake_logit, layer_output)` (not `.backward()` — that would store
gradients for all 66 M weights ≈ 260 MB), weight channels by mean gradient, ReLU, normalise.
- Face model: layer `encoder.bn2`; heatmap mapped back from the 380 square to the face box;
  reason names the face part with most heat (eyes/forehead, nose/cheeks, mouth/jaw).
  Output `faces.png` = heatmap + boxes (red ≥ 50 % fake, green otherwise).
- AI-image model: layer `vit.encoder.layer[-1].layernorm_before`, tokens → 24×24 grid
  (drop CLS); placed on the centre crop the model saw. Output `ai_heatmap.png` (only when
  AI ≥ 50 %).

**Fusion redesigned (important)** — `fusion/combiner.py`:
- Evidence is scored **per kind of fake** ("ai_generated" vs "manipulated"). Why: a face swap
  caught at 0.99 was cancelled to Inconclusive by the AI-image model correctly saying
  "not AI-made". Not-AI-made is no evidence against a swapped face.
- Each kind's weighted average includes a **neutral 0.5 prior with weight 0.3**, so one weak
  check alone can't decide (replaces part of the old minimum-reliability rule).
- Fake if any kind > 0.65 (highest wins). Authentic if total trust ≥ 0.5 and every kind with
  trust ≥ 0.3 is < 0.35 (a kind seen only by ELA's weak "nothing found" doesn't count as
  checked). Otherwise Inconclusive. Decisive metadata still wins first.
- Explanations for a fake verdict now use reasons from checks of the same kind.

**Evaluation (own small tests, not a benchmark)**
- Face model on 100 real LFW faces (1 photo per person): mean 0.04, **2/100 ≥ 0.5**
  (3/100 after JPEG q60). AI-image model on the same faces: 0/100 false alarms.
- 30 crude face swaps (OpenCV seamlessClone of another LFW face): 14/30 caught (0.76–1.0),
  16 scored < 0.2. Real deepfakes still untested (FF++/Celeb-DF are gated).
- Full pipeline: Stable Diffusion 10/10 → AI-Generated; skimage real 14/16 → Likely Authentic
  (2 = Hubble image → AI-Generated, known); LFW real 37/40 → Likely Authentic, 2 Inconclusive,
  1 Manipulated (the face model's false alarm).
- Tests: 33 passing (fixture `face.jpg` is now 512×512 so the face is ≥ 64 px).

**Next**: 2d — frontend shows face boxes / AI heatmap / ELA, heatmap picker.

### 2026-10-14 — Session 3d: Part 2d (result page for the new checks)
- `EvidenceViewer.jsx`: tabs **Original / AI focus / Faces / Edited areas**, each with a
  one-line plain explanation and a "heatmap strength" slider. Default tab = the most trusted
  check that leans fake, else Faces, else first. Frequency spectrum stays in its own panel
  (it is not an overlay). Heatmap PNGs are full images (photo + colours), so fading them
  reveals the original underneath.
- `DetectorList.jsx`: sorted by trust; coloured fake-score bar (green ≤ 35 %, amber, red
  ≥ 65 %), "X% fake · trust Y%", "info only" for reliability 0, footnote explaining "trust".
- ELA now saves `ela.png` **only when it finds a suspicious region** — otherwise the UI
  showed an "Edited areas" tab for clean images, which implied edits.
- Verified visually for the first time: ran the API locally (uvicorn, SQLite, eager Celery)
  + Vite dev server, uploaded files, screenshotted with headless Chrome. Checked a
  Manipulated result (crude face swap, face 99 %) and an AI-Generated result (DiffusionDB PNG).
- Observed: a real face **cut off at the image edge** was also flagged red (face model
  false alarm on partial faces). Idea for later: skip or down-weight faces touching the border.
- Only the first reason of each check appears under "Why" (top 3 overall); extra faces'
  reasons are in the per-check evidence list.
- Tests: 33 passing. Docker still not tested (user deferred).

**Phase 2 complete.** Next: Phase 3 — audio (anti-spoofing model + splice check + timeline).

### 2026-10-14 — Session 4: Phase 3 plan + Part 3a (audio loading + player)
**Phase 3 parts**: 3a audio loading + player · 3b voice-clone/AI-speech model per window ·
3c splice/cut check · 3d fake-segment timeline. Research agent checking audio models (3b).

**3a — what was built**
- `preprocessing/audio.py`: `load_audio()` runs **ffmpeg** → 16 kHz mono float32 (what speech
  models expect), first 5 minutes only, 120 s timeout; clear `AudioDecodeError` for broken
  files / no sound track. Works for video files too (`-vn`), ready for Phase 4.
  `split_windows()`: 4 s windows every 2 s (overlap), last window aligned to the end if
  ≥ 1 s left. `is_silent()` (< −45 dB). `waveform_peaks()` → 400 values for drawing.
- `ffmpeg_exe()`: system ffmpeg (Docker image has it) else the pip package
  **imageio-ffmpeg** (only for local dev; this Mac has no ffmpeg and we didn't install system
  software). Tests needing ffmpeg skip if neither exists.
- `MediaContext.audio`: runner decodes once, every audio check reuses it. Unreadable audio →
  Inconclusive + note "The audio could not be analysed: …" (no crash).
- `Outcome.media` → `evidence.media` = `{duration_s, peaks}` for the result page.
- Frontend `AudioPanel.jsx`: `<audio>` player + SVG waveform (no extra library), click to
  seek, red playhead line. Shown for audio files.
- Tests: 41 passing (windows, silence, peaks, 44.1 kHz → 16 kHz decode, broken file, audio
  upload API, unreadable audio). Checked visually with headless Chrome using a clip made by
  macOS `say` (synthetic speech — also useful as a fake-voice sample in 3b).

### 2026-10-14 — Session 4b: Part 3c (audio splice check) — done before 3b
Order swapped: research for 3b was still running, and 3c needs no model.

**`detectors/audio/splice.py`** (`SpliceDetector`, kind manipulated, reliability 0.3; "nothing
found" → 0.2 / 0.15). Idea: every recording has its own background sound, heard in pauses;
a join makes it change suddenly.
- 32 ms frames → power spectrum (bands up to ~6 kHz, dB). Every 0.5 s compare the background
  of 3 s before vs 3 s after. Background = median spectrum of **real pauses**: quietest 10 %
  of frames that are also ≥ 15 dB below the **90th-percentile** (speech) level; need ≥ 6.
- Compare the **shape** only (each spectrum minus its own mean), so a louder speaker / volume
  change is ignored. Join if change ≥ 3.5 dB and ≥ 2.5 × the file's calm level
  (25th percentile of changes). Nearby hits merged. Needs ≥ 9 s of audio.
- Output: reason with times ("changes suddenly at 0:06"), timeline `segments` (±0.5 s).

**How we got there (bugs found by testing, keep for the write-up)**
1. Quiet frames picked from the whole file → after a join to louder noise, all "quiet"
   frames were on one side → nothing to compare. Fix: pick pauses per side.
2. "Quietest 30 %" were still speech (TTS has few pauses) → compared voices, and a louder
   voice looked like a join. Fix: quietest 10 % and clearly below speech level.
3. Baseline = median change → in short clips most comparisons cross the join, so the join
   didn't stand out. Fix: calm quarter (25th percentile).
4. Absolute level changes overlapped (join 7–8 dB vs louder voice ~5.5 dB). Fix: compare
   shape only → join 5.4–5.9 vs louder ≤ 2.0 vs same ≤ 1.8.
5. Pause reference = median loudness failed for speech with many pauses. Fix: 90th pct.

**Evaluation (synthetic only)**: macOS `say` voices (Samantha, Daniel, Karen) + background
noise. Joins (white −45 dB → low rumble −35 dB): **3/3 found at the right time (6.0 s vs
5.8–6.1 s)**. Controls: same noise 0/3, louder voice 0/3. Missed (by design): same noise
+3 dB level step only. Not yet tested on real recordings.
Tests: 5 new (`test_splice.py`, synthetic "speech" bursts, no `say` needed) → 46 passing.

**3b research (research agent, live-checked on HF/GitHub; nothing run yet)**
- AASIST (clovaai): great in-domain but **In-the-Wild EER 43 %** → don't use.
- **Best permissive option: `SpeechAntiSpoofingBenchmarks/XLSR-SLS`** (MIT, XLS-R 300M + SLS,
  trained ASVspoof2019 LA): **In-the-Wild EER 7.46 %**, ASVspoof2021 DF 3.93 %. ONNX file
  `xlsr-sls.onnx` 1.36 GB (pinned sha `6b99ebc9…`, file sha256 `0aa36298…`). Input exactly
  64,600 samples (4.04 s), raw waveform; output index 1 = **bona fide** (invert!). Python
  code files mentioned in its README are missing → ONNX via onnxruntime is the only route.
- Fallback: `Gustking/wav2vec2-large-xlsr-deepfake-audio-classification` (Apache-2.0, 1.26 GB,
  plain transformers, 0=real 1=fake, ASVspoof2019 EER 4.01 %, no cross-dataset result).
- Community wav2vec2-base models (MelodyMachine, mo-thecreator…): unknown/Kaggle data,
  likely overfit. Label order differs per model — always read `id2label`.
- Better models exist but are **non-commercial** (DF_Arena 500M, nii-yamagishilab, Spectra).
- Known pitfall: models trained on ASVspoof often call compressed/phone audio, silence or
  music "fake" → skip silent windows, calibrate on our own real clips.

### 2026-10-14 — Session 4c: Parts 3b + 3d (AI-voice model + timeline) and OGG support
User asked for bigger chunks per commit ("update more features then give commit msg").

**Model: `SpeechAntiSpoofingBenchmarks/XLSR-SLS`** (MIT; XLS-R 300M + SLS head, ACM MM 2024,
trained ASVspoof2019 LA; In-the-Wild EER 7.46 % per the benchmark). ONNX file
`models/xlsr_sls/xlsr-sls.onnx` (1.36 GB, pinned commit `6b99ebc9…`, SHA-256 checked) run with
**onnxruntime** (added to `requirements-ml.txt`). Input `wav` [batch, 64600] raw float
waveform, output `logits` [batch, 2] = **log-softmax, index 1 = bona fide** → fake = 1 − exp(out[1]).
Short audio is repeated (tiled) to 64,600 samples like the original ASVspoof code.
~0.8–1.1 s per window on this Mac's CPU; ≤ 40 windows per file (long files sampled sparser).
Silent windows skipped.

**Evaluation that shaped the design** (40 real LibriSpeech clips from
`hf-internal-testing/librispeech_asr_dummy` + 11 macOS `say` voices; also MP3 32 kbps and
8 kHz "phone" versions). Model output is almost binary (0 or 1 per window).
- TTS: 10/11 clips fully "fake", also after MP3/phone. One voice (score 0.15) missed.
- Real clean: worst-window ≥ 0.5 in 6/40 clips; **real MP3 14/40, real phone 16/40** →
  compression makes real voices look fake (the known ASVspoof pitfall).
- Real compressed false alarms looked *exactly* like TTS (all windows fake), often in short
  clips → no threshold separates them.

**Rules chosen (and why)**
- Clip score = **average** of windows, not the worst window (isolated fake windows are common
  on compressed real speech).
- **Trust 0.6** normally; **0.12** if the file is lossy (MP3/M4A/OGG), phone quality (almost no
  energy > 4 kHz), or < 3 windows (~8 s). 0.12 is too low to reach "AI-Generated" alone
  (with the 0.3 prior a single check needs trust > 0.13). The reason text says so.
- Kind: ≥ 60 % fake windows → ai_generated; some fake parts → manipulated (AI speech mixed
  into a real recording). For manipulated, if the longest run of fake windows is
  **≥ 4 in a row (~10 s)**, score = mean of that run (otherwise the real parts average it away).
  Runs of 2 or 3 caused false "Manipulated" on real clean speech in simulation (2 and 1
  clips); real speech never had 4 in a row.
- Simulated result: real clean 12/40 Likely Authentic, 28 Inconclusive, **0 false
  accusations**; all compressed (real and TTS) → Inconclusive; clean TTS ≥ 8 s → AI-Generated.
- **Main known limitation: compressed fakes (e.g. a cloned WhatsApp voice note) are not
  caught by the model alone** — verdict is Inconclusive with the model's opinion shown.
  Future: a model trained with compression/codec augmentation, or fine-tune on such data.

**Splice check change**: on lossy files trust 0.15 (Opus-compressed TTS gave a false join).

**OGG/Opus support** (`audio/ogg`): WhatsApp/Telegram voice notes — the main scam case.
Upload accept list, error message and upload page updated.

**3d timeline** (`AudioPanel.jsx`): one row per check with segments, coloured by fake score
(green ≤ 35 %, yellow, orange ≥ 50 %, red ≥ 65 %), tooltip per window, shared red playhead,
click anywhere to seek, legend.

**End-to-end check (local app + headless Chrome)**: long TTS → AI-Generated 83 %; long real
speech → Likely Authentic; real speech with a TTS sentence inserted → **Manipulated 77 %**
(voice row red exactly at 0:12–0:24, splice at 0:16); TTS as OGG voice note → Inconclusive.
Tests: 56 passing.

**Next**: Phase 4 — video (frames → face/AI-image checks per second + sound track → timeline).

### 2026-10-14 — Session 5: Phase 4 (video) in one chunk
**Frames** (`preprocessing/video.py`): duration parsed from `ffmpeg -i` output (no ffprobe
needed; imageio-ffmpeg has none). Up to **16 frames** evenly spread (max 1 fps), shrunk to
≤ 1280 px, JPEG q2 so we add few compression traces; temp files deleted after loading.
Frame time = (i + 0.5) / fps. `VideoDecodeError` → Inconclusive + note.
`MediaContext.frames` added. Runner: video → frames + thumbnail (middle frame) + sound
track (if none: note "only the picture was checked") → `media = {duration_s, peaks}`.

**Refactor**: `face_swap.py` now has `check_faces(rgb, with_heatmap)`, `draw_faces()`,
`face_label()` — shared by photos and video frames (photo behaviour unchanged, tests pass).

**Video checks**
- `video/faces.py` `VideoFaceSwapDetector` (manipulated, trust 0.5; 0.3 if faces in < 4
  frames): per-frame score = most suspicious face; video score = **DFDC "confident
  strategy"** (many frames > 0.8 → mean of those; > 90 % frames < 0.2 → mean of those; else
  mean). Grad-CAM only on the worst frame → `video_faces.png`. Timeline segments per frame.
- `video/ai_frames.py` `VideoAiFramesDetector` (ai_generated, trust 0.4 — model trained on
  stills, video compression differs): mean AI probability over frames, per-frame segments.
- Audio detectors (`voice_clone`, `splice`) now also run on videos. "Lossy" is now simply
  **anything except WAV** (video sound is AAC) → low trust, as decided in Phase 3.
- Metadata for video: scan first + last 4 MB for IPTC trainedAlgorithmicMedia (decisive),
  AI tool names (added Sora, Veo, Runway, Pika, Kling, Synthesia, HeyGen), C2PA presence.

**Frontend**: `AudioPanel.jsx` → **`MediaPanel.jsx`** (audio or video player, waveform,
timeline rows, plus "Most suspicious frame (m:ss)" card with heatmap and a Jump button).

**Evaluation (synthetic videos made with ffmpeg; no real deepfake videos available)**
| Video | Verdict | Time (this Mac, CPU) |
|---|---|---|
| Real face photo zoom + real speech | Likely Authentic | 26 s |
| Crude face swap zoom + real speech | **Manipulated 71 %** (12/12 frames 0.99, worst frame 0:05) | 45 s (2 faces/frame) |
| Stable Diffusion slideshow + TTS | **AI-Generated 74 %** (12/12 frames AI) | 5 s (no faces) |
| 10 real LFW faces, no sound | Likely Authentic (2/12 frames false alarm, DFDC strategy averaged them out) | 17 s |
Tests: 62 passing (frame spread/cap, not-a-video error, no-sound note, video upload API,
DFDC strategy). Checked in headless Chrome.

**Known gaps**: no lip-sync / blink / head-pose checks; no tests on real deepfake videos
(DFDC / FaceForensics++ / Celeb-DF need access requests); the face model's frames-from-photo
test videos are much easier than real deepfakes. Speed: ~1 s per face per frame on CPU.

**Next**: Phase 5 — PDF report + history page + delete button.

### 2026-10-14 — Session 6: Phase 5 (PDF report, history, delete)
- **PDF report** (`app/reports/pdf_report.py`, ReportLab): title + file/date/report ID,
  coloured verdict box (+ confidence unless inconclusive), "Why", **"What you should do next"**
  (plain advice per verdict, e.g. call the person back on a number you already trust),
  Evidence (timeline drawing for audio/video with time axis; heatmap pictures with captions),
  "Every check" table (fake %, trust %, finding), notes, limitations, page footer.
- `GET /api/analyses/{id}/report`: made **on first request, then cached** in
  `storage/reports/<id>.pdf` (409 if not finished). Download name
  `ForenSight-report-<file>.pdf`. Why on demand: no extra work for files nobody downloads, and
  the report always uses the current template. `delete_files()` now also deletes the PDF.
- Bug fixed during visual check: big verdict title overlapped the summary line (paragraph
  font size 18 with body line height) → own "verdict" style with leading 22.
- **History page** (`#/history`): thumbnails (icon for audio), file name, type, local time,
  verdict badge + confidence, Delete with confirmation. Header nav: New check / History /
  API status dot. Result page: **Download PDF report** + **Delete** buttons.
- README: "What it checks" table.
- Checked visually: 3 PDFs (video face swap, audio with TTS part, AI image) rendered to PNG;
  history + result pages in headless Chrome. Tests: 64 passing.

**Next ideas (Phase 6+)**: Docker run-through (still never tested!), real deepfake datasets
for evaluation, verify C2PA signatures (c2pa-python), skip faces cut off at the image edge,
Alembic migrations, auto-delete old uploads, demo script + sample files.

### 2026-10-14 — Session 7: Demo prep (+ 2 fixes found by it)
**Built**: `demo/make_demo_files.py` (standalone; numpy/Pillow/OpenCV/pyarrow/imageio-ffmpeg,
see `demo/requirements.txt`) → 12 files in `demo/files/` (git-ignored, with `demo/.cache/`).
Sources: scikit-image v0.24.0 astronaut (PD, NASA) / chelsea / coffee (CC0); DiffusionDB
part-000001 via HTTP range requests (CC0); LibriSpeech dummy parquet pinned to
`5be91486…` (CC BY 4.0, credit in demo/README); AI voice = macOS `say` (Samantha), generated
locally only. **Face swap uses a fictional AI face** (DiffusionDB 8257cf61…) — we avoided
DiffusionDB images of real celebrities and LFW (unclear licence).
`demo/README.md` = file table with measured results + licences; `demo/DEMO_SCRIPT.md` =
3-min flow (AI image → scam-call voice with timeline ⭐ → face-swap video → honest
Inconclusive voice note → PDF), checklist (warm up + pre-run all files into History),
judge Q&A with honest numbers, "what it misses", backup plan.

**Demo run exposed real problems (fixed in the product, not by tweaking the files):**
1. **AI video judged "Likely Authentic"**: (a) demo bug — ffmpeg concat of different-sized
   images froze on the first one (fixed: pad all to 640×640 first); (b) **letterbox black bars
   made the AI-image model score an AI frame 0 % (100 % without bars)** → new
   `trim_black_borders()` in `preprocessing/video.py`, used before the AI-image model on video
   frames; (c) **fusion flaw**: a check ≥ 90 % sure of "fake" with low trust (compressed
   voice = 1.0 @ 0.12) could not stop "Likely Authentic" → new rule `STRONG_FAKE = 0.9`: any
   such check blocks "authentic" (→ Inconclusive). Result now AI-Generated 81 %.
2. Real-voice demo first came out Inconclusive because the script **joined two recordings**
   — the splice check was right. Fixed the demo (one continuous recording).
3. Edited-photo demo first pasted a *more* compressed patch, which ELA cannot see (it finds
   *less*-compressed pastes). Changed to pristine patch in a q60 photo: ELA now finds the
   area (0.58) but trust is 0.15 (heavily compressed photo) → still "Likely Authentic".
   **Kept as an honest "missed" example**, like 05 (single-image face swap, face model 0.45;
   the same swap as video is caught at 0.93).

Final demo results: 10/12 as intended (see demo/README.md). Tests: 66 passing (new:
letterbox trim, strong-doubt fusion rule). Remaining pytest warnings come from starlette,
reportlab and torch (third-party), not our code.
