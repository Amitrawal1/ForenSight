"""Take sample frames from a video with ffmpeg.

We don't check every frame (a 1-minute video has ~1,800). Instead we take up to
MAX_FRAMES frames spread evenly over the video, which is enough to find a fake part
and keeps the face model (about 1 s per face) fast enough.
"""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from app.pipeline.preprocessing.audio import ffmpeg_exe

MAX_FRAMES = 16
MAX_FPS = 1.0  # short videos: at most one frame per second
MAX_SIDE = 1280  # shrink big videos (4K) first; faces are still big enough


class VideoDecodeError(Exception):
    """ffmpeg could not read the video."""


@dataclass
class Frame:
    time_s: float
    rgb: np.ndarray


def video_duration(path: Path) -> float:
    """Length of the video in seconds (read from ffmpeg's file info)."""
    exe = ffmpeg_exe()
    if exe is None:
        raise VideoDecodeError("ffmpeg is not installed")
    # "ffmpeg -i file" prints file info (and exits with an error because there is no output)
    info = subprocess.run([exe, "-nostdin", "-i", str(path)], capture_output=True, timeout=60).stderr.decode(
        "utf-8", "ignore"
    )
    match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", info)
    if not match or "Video:" not in info:
        raise VideoDecodeError("no video stream found")
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def sample_frames(path: Path, work_dir: Path) -> tuple[list[Frame], float]:
    """Return (frames spread over the video, video duration in seconds)."""
    duration = video_duration(path)
    if duration <= 0:
        raise VideoDecodeError("the video has no length")
    fps = min(MAX_FPS, MAX_FRAMES / duration)

    work_dir.mkdir(parents=True, exist_ok=True)
    pattern = work_dir / "frame_%03d.jpg"
    cmd = [
        ffmpeg_exe(), "-nostdin", "-v", "error", "-y",
        "-i", str(path),
        # fps=...: take evenly spaced frames; scale: limit size, keep shape (-2 = even number)
        "-vf", f"fps={fps:.6f},scale='min({MAX_SIDE},iw)':-2",
        "-frames:v", str(MAX_FRAMES),
        "-q:v", "2",  # high JPEG quality, so we don't add compression traces
        str(pattern),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=300)
    except subprocess.TimeoutExpired:
        raise VideoDecodeError("reading the video took too long")

    files = sorted(work_dir.glob("frame_*.jpg"))
    if result.returncode != 0 or not files:
        raise VideoDecodeError("could not read frames from the video")

    frames = []
    for i, f in enumerate(files):
        with Image.open(f) as img:
            # The fps filter's frame number i sits at time i / fps (middle of its slot)
            frames.append(Frame(round(min(duration, (i + 0.5) / fps), 2), np.asarray(img.convert("RGB"))))
        f.unlink()  # we keep the pixels in memory; no need for the temporary file
    return frames, duration


def trim_black_borders(rgb: np.ndarray, threshold: float = 16.0) -> np.ndarray:
    """Cut off black bars (letterboxing) around a video frame.

    Many videos have black bars above/below or left/right. They confuse the AI-image
    model a lot: in our test an AI frame scored 0% with bars and 100% without.
    A row/column counts as a bar if it is almost black on average.
    """
    brightness = rgb.max(axis=2).astype(np.float32)
    rows = np.flatnonzero(brightness.mean(axis=1) > threshold)
    cols = np.flatnonzero(brightness.mean(axis=0) > threshold)
    if len(rows) < 32 or len(cols) < 32:
        return rgb  # (almost) all black: nothing sensible to trim
    return rgb[rows[0] : rows[-1] + 1, cols[0] : cols[-1] + 1]
