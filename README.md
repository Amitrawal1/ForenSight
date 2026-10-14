# ForenSight

Explainable multi-signal deepfake forensics for images, videos and audio.

Upload a file → get **Likely Authentic / AI-Generated / Manipulated / Inconclusive**,
with heatmaps, timelines and plain-language reasons.

See [`MEMORY.md`](MEMORY.md) for the full design, decisions and history.

## What it checks

| Media | Checks |
|-------|--------|
| Images (JPG, PNG, WEBP) | AI-image model (Community Forensics ViT), face-swap model (DFDC EfficientNet-B7), metadata / AI labels / C2PA, error level analysis, frequency analysis |
| Audio (WAV, MP3, M4A, OGG voice notes) | AI-voice model (XLSR-SLS) per ~4 s window, splice check (background-noise changes) |
| Video (MP4, MOV, AVI) | Face-swap and AI-image models on sampled frames, all audio checks on the sound track, metadata |

Every result shows **why**: heatmaps (Grad-CAM), a clickable timeline for audio/video,
plain-language reasons, and a downloadable **PDF report**. Past checks are kept on the
**History** page and can be deleted.

Model files (~1.7 GB in total) are downloaded once with `backend/scripts/download_models.py`
and checked with SHA-256.

**Demo:** sample files and a 3-minute presentation script are in [`demo/`](demo/)
(`demo/README.md`, `demo/DEMO_SCRIPT.md`).

## Quick start (Docker)

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
cp .env.example .env
python3 backend/scripts/download_models.py   # small model files -> models/
docker compose up --build
```

| What        | URL                          |
|-------------|------------------------------|
| Web UI      | http://localhost:5173        |
| API docs    | http://localhost:8000/docs   |
| Health      | http://localhost:8000/api/health |

ML / training environment (Jupyter):

```bash
docker compose --profile ml up ml     # http://localhost:8888
```
