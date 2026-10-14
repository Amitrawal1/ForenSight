import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import jpeg_bytes, photo_like, png_bytes


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def upload(client, name, data):
    return client.post("/api/analyses", files={"file": (name, data)})


def test_jpeg_upload_runs_pipeline(client):
    r = upload(client, "photo.jpg", jpeg_bytes(photo_like()))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "done"
    assert body["media_type"] == "image"
    assert body["verdict"] in {"likely_authentic", "ai_generated", "manipulated", "inconclusive"}
    names = {d["name"] for d in body["evidence"]["detectors"]}
    assert {"metadata", "ela", "fft"} <= names
    assert body["evidence"]["summary"]

    # thumbnail + heatmap are served
    aid = body["id"]
    assert client.get(f"/api/analyses/{aid}/artifacts/thumb.jpg").status_code == 200
    assert client.get(f"/api/analyses/{aid}/artifacts/ela.png").status_code == 200
    assert client.get(f"/api/analyses/{aid}/original").status_code == 200


def test_stable_diffusion_png_is_ai_generated(client):
    data = png_bytes(photo_like(seed=1), {"parameters": "a cat, Steps: 30, Sampler: Euler a, CFG scale: 7"})
    body = upload(client, "cat.png", data).json()
    assert body["verdict"] == "ai_generated"
    assert any("Stable Diffusion" in r for r in body["evidence"]["reasons"])


def test_extension_is_ignored_and_bad_types_rejected(client):
    r = upload(client, "notes.jpg", b"definitely not an image")
    assert r.status_code == 415


def test_png_renamed_jpg_detected_by_bytes(client):
    body = upload(client, "fake-ext.jpg", png_bytes(photo_like(seed=2))).json()
    assert body["mime_type"] == "image/png"
    # ELA only applies to real JPEGs
    assert "ela" not in {d["name"] for d in body["evidence"]["detectors"]}


def test_artifact_name_is_validated(client):
    aid = upload(client, "p.jpg", jpeg_bytes(photo_like(seed=3))).json()["id"]
    assert client.get(f"/api/analyses/{aid}/artifacts/..%2F..%2Ftest.db").status_code == 404
    assert client.get("/api/analyses/does-not-exist").status_code == 404


def test_history_and_delete(client):
    aid = upload(client, "del.jpg", jpeg_bytes(photo_like(seed=4))).json()["id"]
    ids = [a["id"] for a in client.get("/api/analyses").json()]
    assert aid in ids

    assert client.delete(f"/api/analyses/{aid}").status_code == 204
    assert client.get(f"/api/analyses/{aid}").status_code == 404
