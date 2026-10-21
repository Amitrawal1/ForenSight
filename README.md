# ForenSight

Explainable multi-signal deepfake forensics for images, videos and audio.

Upload a file → get **Likely Authentic / AI-Generated / Manipulated / Inconclusive**,
with heatmaps, timelines and plain-language reasons.

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

**Demo:** sample files and their measured results are in [`demo/README.md`](demo/README.md).

## Quick start (Docker)

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/) running, with
**≥ 6 GB memory** (Settings → Resources) and **~10 GB free disk**.

```bash
cp .env.example .env                         # 1. settings (change the passwords for real use)
python3 backend/scripts/download_models.py   # 2. model files -> models/ (~1.7 GB, once)
docker compose up --build                    # 3. build + start (first build: 10-20 min)
```

| What        | URL                          |
|-------------|------------------------------|
| Web UI      | http://localhost:5173        |
| API docs    | http://localhost:8000/docs   |
| Health      | http://localhost:8000/api/health |

Check that everything works (in a second terminal, while the app runs):

```bash
python3 demo/make_demo_files.py   # demo files (once; see demo/README.md)
python3 demo/smoke_test.py        # uploads all demo files, compares with expected results
docker compose run --rm backend pytest   # unit + API tests inside the container
```

### Troubleshooting

| Problem | Fix |
|---------|-----|
| A check says "skipped: model file … is missing" | Run step 2, then `docker compose restart worker` |
| Result stays "Waiting in queue" | `docker compose logs -f worker` — the worker may still be loading models or out of memory |
| Worker exits with code 137 | Out of memory: give Docker more memory (≥ 6 GB) |
| `download_models.py` fails with an SSL error | Run "Install Certificates.command" in your Python folder, or `pip install certifi` |
| Port 3306/5173/8000 already in use | Stop the other program, or change the port on the left side in `docker-compose.yml` |
| Start from a clean database | `docker compose down -v` (deletes all saved analyses) |

ML / training environment (Jupyter):

```bash
docker compose --profile ml up ml     # http://localhost:8888
```
