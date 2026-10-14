"""Splice check: was this audio joined together from different recordings?

Idea: every recording has its own background sound (room hum, street noise, mic hiss).
You hear it in the pauses between words. If two recordings are glued together, that
background suddenly changes at the join.

How:
1. Cut the audio into tiny 32 ms frames and measure the sound level per pitch band
   (a "spectrum").
2. Keep only real pauses: the quietest frames, clearly quieter than the speech.
3. Every half second, compare the background of the 3 seconds before with the 3 seconds after.
4. A change much bigger than the usual changes in this file = possible join.

Numbers were picked by hand on test clips; tune them with real data later.
"""

import numpy as np

from app.pipeline.detectors.base import Detector, DetectorResult, MediaContext, Segment
from app.pipeline.preprocessing.audio import SAMPLE_RATE

FRAME = 512  # 32 ms
HOP = 256  # 16 ms
CONTEXT_S = 3.0  # compare 3 s before vs 3 s after each point
MIN_QUIET_FRAMES = 6  # need this many pause frames on each side to compare
QUIET_SHARE = 10  # pauses = the quietest 10% of frames...
PAUSE_BELOW_DB = 15.0  # ...that are also at least 15 dB quieter than the speech
MIN_CHANGE_DB = 3.5  # background shape must change by at least this much on average...
TIMES_USUAL = 2.5  # ...and be this many times bigger than the file's calm parts
DIGITAL_SILENCE_DB = -90.0  # perfect silence has no background to compare
RELIABILITY = 0.3  # a simple check: natural noise changes (a car passing) can fool it
# Compression (MP3, voice notes) changes the quiet parts between words, which can look
# like a join. In our tests it caused a false alarm, so trust it less there.
LOSSY_MIMES = {"audio/mpeg", "audio/mp4", "audio/ogg"}
LOSSY_RELIABILITY = 0.15


def frame_spectra(audio: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (loudness in dB per frame, spectrum in dB per frame and pitch band)."""
    n = 1 + (len(audio) - FRAME) // HOP
    idx = np.arange(FRAME)[None, :] + HOP * np.arange(n)[:, None]
    frames = audio[idx] * np.hanning(FRAME).astype(np.float32)
    power = np.abs(np.fft.rfft(frames, axis=1)) ** 2 + 1e-12
    loudness = 10 * np.log10(power.mean(axis=1))
    # Keep bands up to ~6 kHz (where background noise differences show up best)
    spectrum = 10 * np.log10(power[:, 2:192])
    return loudness, spectrum


def background_changes(audio: np.ndarray) -> list[tuple[float, float]]:
    """Return [(time in seconds, size of change in dB)] for every likely join."""
    if len(audio) < 3 * CONTEXT_S * SAMPLE_RATE:
        return []
    loudness, spectrum = frame_spectra(audio)
    times = (np.arange(len(loudness)) * HOP + FRAME / 2) / SAMPLE_RATE

    # Perfect digital silence has no background to compare, so skip it
    real = loudness > DIGITAL_SILENCE_DB

    def background(mask: np.ndarray) -> np.ndarray | None:
        """Typical spectrum of the real pauses inside `mask`, or None if there are too few."""
        frames = np.flatnonzero(mask & real)
        if len(frames) == 0:
            return None
        level = loudness[frames]
        # Speech level = the loud parts. (Not the middle value: normal talking is 30-40%
        # pauses, so the middle value can itself be a pause.)
        speech = np.percentile(level, 90)
        is_pause = (level <= np.percentile(level, QUIET_SHARE)) & (level < speech - PAUSE_BELOW_DB)
        quiet = frames[is_pause]
        if len(quiet) < MIN_QUIET_FRAMES:
            return None  # e.g. non-stop speech or music: no background to compare
        return np.median(spectrum[quiet], axis=0)

    # Compare background before / after each point, every 0.5 s.
    # Pauses are chosen on each side separately: after a join to a louder background,
    # the quietest frames of the whole file would all sit on one side.
    points, changes = [], []
    for t in np.arange(CONTEXT_S, times[-1] - CONTEXT_S, 0.5):
        before = background((times >= t - CONTEXT_S) & (times < t))
        after = background((times >= t) & (times < t + CONTEXT_S))
        if before is None or after is None:
            continue
        # Compare the SHAPE of the background, not its overall level: someone simply
        # speaking louder (or a volume change) shifts all bands up by the same amount,
        # while a different recording place changes which bands are noisy.
        diff = np.abs((before - before.mean()) - (after - after.mean())).mean()
        points.append(float(t))
        changes.append(float(diff))
    if len(changes) < 3:
        return []

    # "Calm" level of change in this file. Not the middle value: in a short clip most
    # comparisons cross the join, so we use the calmest quarter instead.
    usual = float(np.percentile(changes, 25))
    limit = max(MIN_CHANGE_DB, TIMES_USUAL * usual)
    found = [(t, c) for t, c in zip(points, changes) if c > limit]

    # Neighbouring points around the same join: keep only the strongest one
    joins: list[tuple[float, float]] = []
    for t, c in found:
        if joins and t - joins[-1][0] <= CONTEXT_S:
            if c > joins[-1][1]:
                joins[-1] = (t, c)
        else:
            joins.append((t, c))
    return joins


def mmss(seconds: float) -> str:
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


class SpliceDetector(Detector):
    name = "audio_splice"
    label = "Audio splice check"
    media_types = ("audio",)

    def run(self, ctx: MediaContext) -> DetectorResult | None:
        if ctx.audio is None:
            return None
        if len(ctx.audio) < 3 * CONTEXT_S * SAMPLE_RATE:
            return None  # under 9 seconds: too short to compare before/after

        joins = background_changes(ctx.audio)
        if not joins:
            return DetectorResult(self.name, fake_score=0.2, reliability=0.15, fake_kind="manipulated",
                                  reasons=["The background sound stays consistent; no sign that "
                                           "recordings were joined together."])

        biggest = max(c for _, c in joins)
        score = min(0.95, 0.6 + 0.02 * biggest)
        places = ", ".join(mmss(t) for t, _ in joins[:3])
        reasons = [f"The background sound changes suddenly at {places}, which can mean different "
                   "recordings were joined together."]
        lossy = ctx.mime in LOSSY_MIMES
        if lossy:
            reasons.append("The file is compressed, which can also cause such changes, so this counts less.")
        return DetectorResult(
            self.name, fake_score=score, reliability=LOSSY_RELIABILITY if lossy else RELIABILITY,
            fake_kind="manipulated", reasons=reasons,
            segments=[Segment(max(0.0, t - 0.5), t + 0.5, score) for t, _ in joins],
        )
