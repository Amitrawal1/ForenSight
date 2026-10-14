"""AI-generated video check: run the AI-image model on sampled frames.

Catches videos made entirely by AI (text-to-video tools). The model was trained on
still images, not video frames, and video compression changes images, so we trust it
less here than on photos.
"""

import numpy as np
from PIL import Image

from app.pipeline.detectors.base import Detector, DetectorResult, MediaContext, Segment
from app.pipeline.detectors.image.ai_image import fake_probability

RELIABILITY = 0.4


class VideoAiFramesDetector(Detector):
    name = "video_ai_frames"
    label = "AI-image model (video frames)"
    media_types = ("video",)

    def run(self, ctx: MediaContext) -> DetectorResult | None:
        if not ctx.frames:
            return None
        step = ctx.frames[1].time_s - ctx.frames[0].time_s if len(ctx.frames) > 1 else 1.0

        probs = [fake_probability(Image.fromarray(f.rgb)) for f in ctx.frames]
        segments = [Segment(round(max(0.0, f.time_s - step / 2), 2), round(f.time_s + step / 2, 2), round(p, 3))
                    for f, p in zip(ctx.frames, probs)]
        p = np.array(probs)
        share = float((p >= 0.5).mean())
        score = float(p.mean())

        if share >= 0.5:
            reason = (f"{int((p >= 0.5).sum())} of {len(p)} frames look AI-generated (average {round(score * 100)}%), "
                      "which suggests the video was made with an AI video tool.")
        else:
            reason = f"The frames look like real camera footage (average AI score {round(score * 100)}%)."
        return DetectorResult(self.name, fake_score=score, reliability=RELIABILITY, fake_kind="ai_generated",
                              reasons=[reason], segments=segments)
