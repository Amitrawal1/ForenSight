"""Build the ForenSight demo files (images, audio, video) into demo/files/.

All sources are free to use (see demo/README.md):
- scikit-image sample photos (public domain / CC0)
- DiffusionDB Stable Diffusion images (CC0)
- LibriSpeech speech recordings (CC BY 4.0)
- AI voice: made on your Mac with the built-in `say` command

Run from the project root (macOS, needs internet the first time):

    python3 -m pip install -r demo/requirements.txt
    python3 backend/scripts/download_models.py        # face detector used for the face swap
    python3 demo/make_demo_files.py
"""

import io
import shutil
import ssl
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "files"
CACHE = ROOT / ".cache"
FACE_MODEL = ROOT.parent / "models" / "face_detection_yunet_2023mar.onnx"

SKIMAGE = "https://raw.githubusercontent.com/scikit-image/scikit-image/v0.24.0/skimage/data/"
DIFFUSIONDB_ZIP = "https://huggingface.co/datasets/poloclub/diffusiondb/resolve/main/images/part-000001.zip"
LIBRISPEECH = ("https://huggingface.co/datasets/hf-internal-testing/librispeech_asr_dummy/resolve/"
               "5be91486e11a2d616f4ec5db8d3fd248585ac07a/clean/validation-00000-of-00001.parquet")

# DiffusionDB images we use (file names inside part-000001.zip)
AI_PORTRAIT = "8257cf61-2e85-48da-bdf3-72404ce2665f.png"  # fictional person, used for face swap too
AI_SCENE = "0181d6f8-f366-448d-b0fd-8d0a8b45cea9.png"  # spaceships
SLIDESHOW = [
    "0181d6f8-f366-448d-b0fd-8d0a8b45cea9.png", "193cd9a2-4e2c-429e-842b-867d4cc1c0db.png",
    "294a438c-9f99-4027-9739-b58d3c00edbb.png", "2eb977dd-e63f-472d-af9b-dff63f039fb8.png",
    "49f8d327-f787-4af6-95ba-b6750fd86131.png", "4e1f3d61-f913-4f25-a866-d2c434045d38.png",
]

AI_VOICE_TEXT = (
    "Hi, it's me. I'm calling from a friend's phone because mine broke. "
    "I'm in a bit of trouble and I need you to send some money today. "
    "Please don't tell anyone, I'll explain everything later. "
    "I'll send you the account details in a message right after this call."
)

SR = 16_000


# ---------- small helpers ----------

def ssl_context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def download(url: str, name: str) -> Path:
    """Download once into demo/.cache and reuse it next time."""
    path = CACHE / name
    if not path.is_file():
        print(f"  downloading {name} ...")
        CACHE.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, context=ssl_context()) as r, path.open("wb") as f:
            shutil.copyfileobj(r, f)
    return path


class RemoteFile(io.RawIOBase):
    """Read parts of a big online file with HTTP range requests (so we don't download 600 MB)."""

    def __init__(self, url: str):
        self.url, self.pos = url, 0
        head = urllib.request.Request(url, method="HEAD")
        self.size = int(urllib.request.urlopen(head, context=ssl_context()).headers["Content-Length"])

    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos

    def seek(self, offset, whence=0):
        self.pos = {0: offset, 1: self.pos + offset, 2: self.size + offset}[whence]
        return self.pos

    def readinto(self, buffer):
        end = min(self.size, self.pos + len(buffer)) - 1
        if self.pos > end:
            return 0
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{end}"})
        data = urllib.request.urlopen(req, context=ssl_context()).read()
        buffer[: len(data)] = data
        self.pos += len(data)
        return len(data)


def diffusiondb_images(names: list[str]) -> dict[str, Path]:
    missing = [n for n in names if not (CACHE / n).is_file()]
    if missing:
        print(f"  reading {len(missing)} images from DiffusionDB ...")
        CACHE.mkdir(parents=True, exist_ok=True)
        z = zipfile.ZipFile(io.BufferedReader(RemoteFile(DIFFUSIONDB_ZIP), buffer_size=1 << 20))
        for n in missing:
            (CACHE / n).write_bytes(z.read(n))
    return {n: CACHE / n for n in names}


def ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def run_ffmpeg(*args: str) -> None:
    subprocess.run([ffmpeg(), "-v", "error", "-y", *args], check=True)


def load_wav16(path: Path) -> np.ndarray:
    """Any audio file -> 16 kHz mono float32."""
    out = subprocess.run([ffmpeg(), "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.float32).copy()


def save_wav(audio: np.ndarray, path: Path) -> None:
    import wave

    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())


def biggest_face(rgb: np.ndarray, detector) -> tuple[int, int, int, int]:
    detector.setInputSize((rgb.shape[1], rgb.shape[0]))
    _, found = detector.detect(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    if found is None:
        raise RuntimeError("no face found")
    x, y, w, h = max(found, key=lambda r: r[2] * r[3])[:4].astype(int)
    return int(x), int(y), int(w), int(h)


def face_swap(target: np.ndarray, donor: np.ndarray) -> np.ndarray:
    """Paste the donor's face onto the target's face and blend the edges (a simple face swap)."""
    detector = cv2.FaceDetectorYN.create(str(FACE_MODEL), "", (320, 320))
    tx, ty, tw, th = biggest_face(target, detector)
    dx, dy, dw, dh = biggest_face(donor, detector)
    face = cv2.resize(donor[dy : dy + dh, dx : dx + dw], (tw, th))
    mask = np.zeros((th, tw), np.uint8)
    cv2.ellipse(mask, (tw // 2, th // 2), (int(tw * 0.42), int(th * 0.48)), 0, 0, 360, 255, -1)
    return cv2.seamlessClone(face, target.copy(), mask, (tx + tw // 2, ty + th // 2), cv2.NORMAL_CLONE)


def jpeg(rgb: np.ndarray, quality: int) -> np.ndarray:
    """Compress with JPEG and decode again (to make an image 'already compressed')."""
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, "JPEG", quality=quality)
    return np.array(Image.open(buf).convert("RGB"))  # np.array (not asarray): an editable copy


def video_from_image(image: Path, audio: Path | None, out: Path, seconds: float = 12) -> None:
    """A slow zoom into a still image, with an optional sound track."""
    zoom = "scale=1024:1024,zoompan=z='1+0.0015*on':d=1:s=640x640:fps=25"
    args = ["-loop", "1", "-i", str(image)]
    if audio:
        args += ["-i", str(audio)]
    args += ["-filter_complex", f"[0]{zoom}[v]", "-map", "[v]"]
    if audio:
        args += ["-map", "1:a", "-c:a", "aac"]
    run_ffmpeg(*args, "-t", str(seconds), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out))


# ---------- the demo files ----------

def main() -> int:
    if not FACE_MODEL.is_file():
        print("Face model missing. Run first: python3 backend/scripts/download_models.py")
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    print("Sources:")
    astronaut = np.asarray(Image.open(download(SKIMAGE + "astronaut.png", "astronaut.png")).convert("RGB"))
    chelsea = np.asarray(Image.open(download(SKIMAGE + "chelsea.png", "chelsea.png")).convert("RGB"))
    coffee = np.asarray(Image.open(download(SKIMAGE + "coffee.png", "coffee.png")).convert("RGB"))
    sd = diffusiondb_images(sorted(set([AI_PORTRAIT, AI_SCENE] + SLIDESHOW)))

    print("Images:")
    # 1. A real photo
    Image.fromarray(astronaut).save(OUT / "01_real_photo.jpg", quality=92)
    # 2. AI portrait of a fictional person, as made by Stable Diffusion (with its settings in the file)
    shutil.copy(sd[AI_PORTRAIT], OUT / "02_ai_portrait.png")
    # 3. AI image saved again as JPEG: the AI settings are gone, so only the model can catch it
    Image.open(sd[AI_SCENE]).convert("RGB").save(OUT / "03_ai_image_no_metadata.jpg", quality=90)
    # 4. Edited photo: the cat photo was already compressed (like most photos online), then a
    #    sharp, uncompressed piece of another photo was pasted in. ELA sees the pasted piece
    #    because it recompresses differently.
    edited = jpeg(chelsea, 60)
    edited[60:220, 130:330] = coffee[120:280, 200:400]
    Image.fromarray(edited).save(OUT / "04_edited_photo.jpg", quality=92)
    # 5. Face swap: the AI portrait's face blended onto the astronaut
    swapped = face_swap(astronaut, np.asarray(Image.open(sd[AI_PORTRAIT]).convert("RGB")))
    Image.fromarray(swapped).save(OUT / "05_face_swap.jpg", quality=92)

    print("Audio:")
    import pyarrow.parquet as pq

    rows = pq.read_table(download(LIBRISPEECH, "librispeech_dummy.parquet")).to_pylist()
    # One continuous recording. (Joining two recordings would be a real splice, and the
    # splice check correctly flags that.)
    longest = max(rows, key=lambda r: len(r["audio"]["bytes"]))
    real = load_wav16(_bytes_to_file(longest["audio"]["bytes"], "real_voice.flac"))
    save_wav(real, OUT / "06_real_voice.wav")

    if shutil.which("say") is None:
        print("  `say` not found (not a Mac): skipping the AI-voice files")
    else:
        aiff = CACHE / "ai_voice.aiff"
        subprocess.run(["say", "-v", "Samantha", "-o", str(aiff), AI_VOICE_TEXT], check=True)
        ai = load_wav16(aiff)
        save_wav(ai, OUT / "07_ai_voice.wav")
        # Real recording with the AI voice inserted in the middle
        mid = len(real) // 2
        save_wav(np.concatenate([real[:mid], 0.8 * ai, real[mid:]]), OUT / "08_real_voice_with_ai_part.wav")
        # The AI voice as a WhatsApp-style voice note (Opus): compressed -> expect Inconclusive
        run_ffmpeg("-i", str(OUT / "07_ai_voice.wav"), "-c:a", "libopus", "-b:a", "24k", str(OUT / "09_ai_voice_note.ogg"))

    print("Video:")
    video_from_image(OUT / "01_real_photo.jpg", OUT / "06_real_voice.wav", OUT / "10_real_video.mp4")
    video_from_image(OUT / "05_face_swap.jpg", OUT / "06_real_voice.wav", OUT / "11_face_swap_video.mp4")
    if (OUT / "07_ai_voice.wav").is_file():
        # Every picture must have the same size, or ffmpeg's concat only shows the first one
        slides = []
        for n in SLIDESHOW:
            img = Image.open(sd[n]).convert("RGB")
            img.thumbnail((640, 640))
            path = CACHE / f"slide_{n}"
            canvas = Image.new("RGB", (640, 640))
            canvas.paste(img, ((640 - img.width) // 2, (640 - img.height) // 2))
            canvas.save(path)
            slides.append(path)
        listing = CACHE / "slideshow.txt"
        listing.write_text("".join(f"file '{p}'\nduration 2\n" for p in slides) + f"file '{slides[-1]}'\n")
        run_ffmpeg("-f", "concat", "-safe", "0", "-i", str(listing), "-i", str(OUT / "07_ai_voice.wav"),
                   "-vf", "fps=25",
                   "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(OUT / "12_ai_video.mp4"))

    print(f"\nDone: {len(list(OUT.iterdir()))} files in {OUT}")
    return 0


def _bytes_to_file(data: bytes, name: str) -> Path:
    path = CACHE / name
    path.write_bytes(data)
    return path


if __name__ == "__main__":
    sys.exit(main())
