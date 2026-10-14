"""Check the whole running app end to end, using the demo files.

Uploads every file in demo/files/ to the API, waits for each result, and compares it
with the result we expect (the table in demo/README.md). Also downloads one PDF report.

Run it after `docker compose up` (needs only plain Python, no extra packages):

    python3 demo/smoke_test.py                 # API at http://localhost:8000
    python3 demo/smoke_test.py http://host:8000
"""

import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

FILES = Path(__file__).resolve().parent / "files"

# What ForenSight said about each demo file when we tested it (see demo/README.md)
EXPECTED = {
    "01_real_photo.jpg": "likely_authentic",
    "02_ai_portrait.png": "ai_generated",
    "03_ai_image_no_metadata.jpg": "ai_generated",
    "04_edited_photo.jpg": "likely_authentic",  # known miss
    "05_face_swap.jpg": "inconclusive",  # known miss
    "06_real_voice.wav": "likely_authentic",
    "07_ai_voice.wav": "ai_generated",
    "08_real_voice_with_ai_part.wav": "manipulated",
    "09_ai_voice_note.ogg": "inconclusive",
    "10_real_video.mp4": "likely_authentic",
    "11_face_swap_video.mp4": "manipulated",
    "12_ai_video.mp4": "ai_generated",
}

TIMEOUT_S = 300  # per file; the first file also waits for the models to load


def call(url: str, data: bytes | None = None, headers: dict | None = None) -> bytes:
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def upload(api: str, path: Path) -> dict:
    """POST the file as multipart/form-data (what a browser upload sends)."""
    boundary = uuid.uuid4().hex
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{path.name}\"\r\n"
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    return json.loads(call(f"{api}/api/analyses", body, headers))


def wait_for_result(api: str, analysis_id: str) -> dict:
    start = time.time()
    while time.time() - start < TIMEOUT_S:
        a = json.loads(call(f"{api}/api/analyses/{analysis_id}"))
        if a["status"] in ("done", "failed"):
            return a
        time.sleep(2)
    raise TimeoutError(f"no result after {TIMEOUT_S} s")


def main() -> int:
    api = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
    try:
        print("API health:", json.loads(call(f"{api}/api/health"))["status"])
    except (urllib.error.URLError, OSError) as e:
        print(f"Cannot reach the API at {api}: {e}. Is `docker compose up` running?")
        return 1

    files = sorted(p for p in FILES.iterdir() if p.name in EXPECTED) if FILES.is_dir() else []
    if not files:
        print("No demo files. Run first: python3 demo/make_demo_files.py")
        return 1

    failures, last_id = 0, None
    for path in files:
        start = time.time()
        try:
            result = wait_for_result(api, upload(api, path)["id"])
        except Exception as e:  # keep going so we see every problem in one run
            print(f"ERROR {path.name:34s} {e}")
            failures += 1
            continue
        got, want = result["verdict"], EXPECTED[path.name]
        ok = result["status"] == "done" and got == want
        failures += not ok
        last_id = result["id"]
        conf = f"{round(result['confidence'] * 100)}%" if result.get("confidence") else ""
        extra = "" if ok else f"  (expected {want}; status {result['status']} {result.get('error') or ''})"
        print(f"{'ok   ' if ok else 'FAIL '} {path.name:34s} {got or '-':17s} {conf:>4s} {time.time() - start:5.0f}s{extra}")

    if last_id:
        pdf = call(f"{api}/api/analyses/{last_id}/report")
        pdf_ok = pdf.startswith(b"%PDF")
        failures += not pdf_ok
        print(f"{'ok   ' if pdf_ok else 'FAIL '} PDF report ({len(pdf) // 1024} KB)")

    print(f"\n{len(files) + 1 - failures} passed, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
