"""Face-swap check for videos: run the face-swap model on sampled frames.

Each frame gets a score (the most suspicious face in it). The scores become a
timeline, and the worst frame gets a heatmap so the user can see where the model looked.
"""

import cv2
import numpy as np

from app.pipeline.detectors.base import Detector, DetectorResult, MediaContext, Segment
from app.pipeline.detectors.image.face_swap import check_faces, draw_faces, face_part

HEATMAP_NAME = "video_faces.png"
FAKE_FRAME = 0.8  # a frame counts as clearly fake above this
RELIABILITY = 0.5
FEW_FACES_RELIABILITY = 0.3  # faces in only a few frames = less evidence
MIN_FACE_FRAMES = 4


def mmss(seconds: float) -> str:
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


def video_score(probs: list[float]) -> float:
    """Combine frame scores the way the DFDC-winning team did ("confident strategy"):
    - if many frames are clearly fake, use the average of those fake frames
    - if almost all frames are clearly real, use the average of those
    - otherwise use the plain average
    """
    p = np.array(probs)
    fakes = p[p > FAKE_FRAME]
    if len(fakes) > len(p) / 2.5 and len(fakes) >= 3:
        return float(fakes.mean())
    reals = p[p < 0.2]
    if len(reals) > 0.9 * len(p):
        return float(reals.mean())
    return float(p.mean())


class VideoFaceSwapDetector(Detector):
    name = "video_face_swap"
    label = "Face-swap model (video)"
    media_types = ("video",)

    def run(self, ctx: MediaContext) -> DetectorResult | None:
        if not ctx.frames:
            return None
        step = ctx.frames[1].time_s - ctx.frames[0].time_s if len(ctx.frames) > 1 else 1.0

        scored = []  # (frame, highest face score in that frame)
        for frame in ctx.frames:
            checks = check_faces(frame.rgb, with_heatmap=False)
            if checks:
                scored.append((frame, max(c.prob for c in checks)))
        if not scored:
            return None  # no faces in the video: this check does not apply

        probs = [p for _, p in scored]
        score = video_score(probs)
        segments = [Segment(round(max(0.0, f.time_s - step / 2), 2), round(f.time_s + step / 2, 2), round(p, 3))
                    for f, p in scored]

        # Heatmap for the most suspicious frame
        worst_frame, worst = max(scored, key=lambda item: item[1])
        checks = check_faces(worst_frame.rgb, with_heatmap=True)
        cv2.imwrite(str(ctx.out_dir / HEATMAP_NAME), draw_faces(worst_frame.rgb, checks))

        fake_times = [f.time_s for f, p in scored if p >= 0.5]
        if fake_times:
            cam = next((c.cam for c in checks if c.cam is not None), None)
            focus = f"; the model focused most on the {face_part(cam)}" if cam is not None else ""
            reasons = [f"The face looks swapped or altered in {len(fake_times)} of {len(scored)} checked frames "
                       f"(around {mmss(fake_times[0])}-{mmss(fake_times[-1])}, up to {round(worst * 100)}%){focus}. "
                       f"The most suspicious frame is at {mmss(worst_frame.time_s)}."]
        else:
            reasons = [f"Faces were checked in {len(scored)} frames; none looks swapped "
                       f"(highest {round(worst * 100)}%)."]

        few = len(scored) < MIN_FACE_FRAMES
        if few:
            reasons.append(f"A face was found in only {len(scored)} frame(s), so this check counts less.")
        return DetectorResult(self.name, fake_score=score,
                              reliability=FEW_FACES_RELIABILITY if few else RELIABILITY,
                              fake_kind="manipulated", reasons=reasons, heatmap=HEATMAP_NAME, segments=segments)
