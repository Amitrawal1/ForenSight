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
