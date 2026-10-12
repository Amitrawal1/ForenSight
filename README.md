# ForenSight

Explainable multi-signal deepfake forensics for images, videos and audio.

Upload a file → get **Likely Authentic / AI-Generated / Manipulated / Inconclusive**,
with heatmaps, timelines and plain-language reasons.

See [`MEMORY.md`](MEMORY.md) for the full design, decisions and history.

## Quick start (Docker)

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
cp .env.example .env
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
