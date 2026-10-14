"""AI voice / voice-clone detector.

Uses the XLSR-SLS model (ACM Multimedia 2024, MIT licence): a large speech model
(XLS-R, 300 M parameters) plus a small classifier that looks at all of its layers.
On "In-the-Wild" (real-world deepfakes of public figures, not seen in training) it
gets an error rate of about 7.5%, the best of the freely usable models we found.

The model hears exactly 64,600 samples (about 4 seconds) at a time, so we score the
audio window by window. That gives a score for each part of the clip, which the
result page shows as a timeline.

The model file is ONNX (a portable model format) and runs with onnxruntime.
"""

import numpy as np

from app.pipeline.detectors.base import Detector, DetectorResult, MediaContext, Segment
from app.pipeline.models.registry import ModelNotAvailable, load_cached, model_path
from app.pipeline.preprocessing.audio import SAMPLE_RATE, is_silent, split_windows

MODEL_FILE = "xlsr_sls/xlsr-sls.onnx"
INPUT_SAMPLES = 64_600  # fixed input size of the model (4.04 s)
HOP_S = 2.0  # start a new window every 2 seconds
MAX_WINDOWS = 40  # about 1 s per window on CPU, so long files are sampled more sparsely
FAKE_WINDOW = 0.5  # a window counts as "fake" above this
RELIABILITY = 0.6
# Compressed (MP3, M4A, WhatsApp/OGG, video sound), phone-quality or short audio: in our tests real
# voices then often looked exactly like AI voices. So we trust the model much less:
# low enough that it can never call a file "AI-generated" on its own.
LOW_RELIABILITY = 0.12
MIN_WINDOWS = 3  # fewer windows (under ~8 s of speech) = too little evidence
# A partly-fake recording needs at least this many fake windows in a row (~10 s).
# In our tests real speech sometimes had up to 3 odd windows in a row, never 4.
MIN_FAKE_RUN = 4


def _load_session():
    try:
        import onnxruntime as ort
    except ImportError:
        raise ModelNotAvailable("onnxruntime is not installed. Set INSTALL_ML=true in .env and rebuild.")
    return ort.InferenceSession(str(model_path(MODEL_FILE)), providers=["CPUExecutionProvider"])


def repeat_to_length(samples: np.ndarray, length: int = INPUT_SAMPLES) -> np.ndarray:
    """Short audio is repeated until it is long enough (same as the model's original code)."""
    if len(samples) >= length:
        return samples[:length]
    times = length // len(samples) + 1
    return np.tile(samples, times)[:length]


def fake_probability(samples: np.ndarray) -> float:
    """Chance (0..1) that this piece of speech is AI-generated or cloned."""
    session = load_cached("xlsr_sls", _load_session)
    x = repeat_to_length(samples.astype(np.float32))[None, :]
    log_probs = session.run(None, {"wav": x})[0][0]
    # The model's class 1 means "real human speech" (bona fide), so fake = 1 - real
    return float(1.0 - np.exp(log_probs[1]))


def is_phone_quality(audio: np.ndarray) -> bool:
    """True if almost no sound above 4 kHz (phone calls and some voice apps cut it off)."""
    spectrum = np.abs(np.fft.rfft(audio[: 60 * SAMPLE_RATE])) ** 2
    freqs = np.fft.rfftfreq(min(len(audio), 60 * SAMPLE_RATE), 1 / SAMPLE_RATE)
    return spectrum[freqs > 4000].sum() < 0.002 * spectrum.sum()


def mmss(seconds: float) -> str:
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


def longest_fake_run(segments: list[Segment]) -> list[float]:
    """Scores of the longest run of fake windows in a row."""
    best: list[float] = []
    current: list[float] = []
    for seg in segments:
        current = current + [seg.score] if seg.score >= FAKE_WINDOW else []
        if len(current) > len(best):
            best = current
    return best


def merge_fake_parts(segments: list[Segment]) -> list[tuple[float, float]]:
    """Join overlapping fake windows into longer parts, e.g. 0:04-0:12."""
    parts: list[tuple[float, float]] = []
    for seg in segments:
        if seg.score < FAKE_WINDOW:
            continue
        if parts and seg.start_s <= parts[-1][1]:
            parts[-1] = (parts[-1][0], max(parts[-1][1], seg.end_s))
        else:
            parts.append((seg.start_s, seg.end_s))
    return parts


class VoiceCloneDetector(Detector):
    name = "voice_clone"
    label = "AI-voice model"
    media_types = ("audio", "video")

    def run(self, ctx: MediaContext) -> DetectorResult | None:
        if ctx.audio is None:
            return None
        duration = len(ctx.audio) / SAMPLE_RATE
        window_s = INPUT_SAMPLES / SAMPLE_RATE
        # Long files: spread the windows out so we never run more than MAX_WINDOWS
        hop = max(HOP_S, (duration - window_s) / (MAX_WINDOWS - 1)) if duration > window_s else HOP_S

        segments = []
        for w in split_windows(ctx.audio, window_s=window_s, hop_s=hop):
            if is_silent(w.samples):
                continue  # no speech to judge; models often call silence "fake"
            segments.append(Segment(round(w.start_s, 2), round(w.end_s, 2), round(fake_probability(w.samples), 3)))
        if not segments:
            return None  # silent file

        scores = np.array([s.score for s in segments])
        fake_share = float((scores >= FAKE_WINDOW).mean())
        # Overall score = average over the clip. Not the worst window: on compressed
        # real speech single windows often look fake, so one window is not enough.
        score = float(scores.mean())
        parts = merge_fake_parts(segments)
        run = longest_fake_run(segments)

        # How much can we trust the model on this recording?
        problems = []
        # Everything except WAV is compressed (MP3, M4A, voice notes, and the sound of videos)
        if ctx.mime != "audio/x-wav":
            problems.append("compressed (e.g. MP3 or a messaging-app voice note)")
        elif is_phone_quality(ctx.audio):
            problems.append("phone quality")
        if len(segments) < MIN_WINDOWS:
            problems.append("short")
        reliability = LOW_RELIABILITY if problems else RELIABILITY

        if parts:
            where = ", ".join(f"{mmss(a)}-{mmss(b)}" for a, b in parts[:3])
            if fake_share >= 0.6:
                kind = "ai_generated"
                reason = f"The voice sounds AI-generated or cloned in most of the clip ({where})."
            else:
                kind = "manipulated"
                reason = (f"Parts of the voice sound AI-generated or cloned ({where}); the rest sounds "
                          "like a real person, so AI speech may have been mixed into a real recording.")
                # A long fake part is strong evidence on its own; don't let the real
                # parts of the clip average it away
                if len(run) >= MIN_FAKE_RUN:
                    score = float(np.mean(run))
        else:
            kind = "ai_generated"
            reason = (f"The voice sounds like a real person throughout "
                      f"(highest AI-voice score {round(scores.max() * 100)}%).")

        reasons = [reason]
        if problems:
            reasons.append(f"This recording is {' and '.join(problems)}. In our tests the AI-voice model "
                           "was often wrong on such audio, so this check counts for little in the verdict.")
        return DetectorResult(self.name, fake_score=score, reliability=reliability, fake_kind=kind,
                              reasons=reasons, segments=segments)
