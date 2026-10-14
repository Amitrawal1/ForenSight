"""Metadata check: EXIF camera info, editing-software tags, AI-tool signatures,
IPTC "digital source type" and Content Credentials (C2PA).

Metadata is easy to strip or fake, so on its own it is weak evidence — except for
explicit AI markers written by the generator itself, which are strong.
"""

import re
from dataclasses import dataclass

from PIL import Image

from app.pipeline.detectors.base import Detector, DetectorResult, MediaContext

# EXIF tag ids
SOFTWARE, MAKE, MODEL, DESCRIPTION, ARTIST = 0x0131, 0x010F, 0x0110, 0x010E, 0x013B

AI_TOOLS = {
    "midjourney": "Midjourney",
    "dall-e": "DALL-E",
    "dall·e": "DALL-E",
    "stable diffusion": "Stable Diffusion",
    "stablediffusion": "Stable Diffusion",
    "novelai": "NovelAI",
    "comfyui": "ComfyUI",
    "invokeai": "InvokeAI",
    "automatic1111": "Stable Diffusion (AUTOMATIC1111)",
    "adobe firefly": "Adobe Firefly",
    "leonardo.ai": "Leonardo.ai",
    "ideogram": "Ideogram",
}

EDITORS = {
    "photoshop": "Adobe Photoshop",
    "gimp": "GIMP",
    "affinity photo": "Affinity Photo",
    "pixelmator": "Pixelmator",
    "picsart": "PicsArt",
    "snapseed": "Snapseed",
    "facetune": "Facetune",
    "canva": "Canva",
    "photopea": "Photopea",
    "paint.net": "Paint.NET",
}

# PNG text keys written by Stable Diffusion front ends
SD_PNG_KEYS = ("parameters", "prompt", "workflow", "sd-metadata", "invokeai_metadata")

XMP_RE = re.compile(rb"<x:xmpmeta.*?</x:xmpmeta>", re.DOTALL)


@dataclass
class Finding:
    fake_score: float
    reliability: float
    fake_kind: str
    reason: str


class MetadataDetector(Detector):
    name = "metadata"
    label = "File metadata"
    media_types = ("image",)

    def run(self, ctx: MediaContext) -> DetectorResult | None:
        if ctx.media_type not in self.media_types:
            return None

        raw = ctx.path.read_bytes()
        with Image.open(ctx.path) as img:
            exif = img.getexif()
            png_text = {k.lower(): str(v) for k, v in img.info.items() if isinstance(v, (str, bytes))}

        xmp_match = XMP_RE.search(raw)
        xmp = xmp_match.group(0).decode("utf-8", "ignore") if xmp_match else ""

        text_fields = [str(exif.get(t, "")) for t in (SOFTWARE, DESCRIPTION, ARTIST)]
        text_fields += list(png_text.values()) + [xmp]
        haystack = "\n".join(text_fields).lower()

        findings: list[Finding] = []
        notes: list[str] = []

        # 1. IPTC digital source type — written by Firefly, Google, OpenAI and others
        if "compositewithtrainedalgorithmicmedia" in haystack:
            findings.append(Finding(0.9, 0.8, "manipulated",
                                    "Metadata declares the image was edited with generative AI "
                                    "(IPTC: composite with trained algorithmic media)."))
        elif "trainedalgorithmicmedia" in haystack:
            findings.append(Finding(0.95, 0.9, "ai_generated",
                                    "Metadata declares the image was created by generative AI "
                                    "(IPTC: trained algorithmic media)."))

        # 2. Stable Diffusion style PNG parameters
        sd_keys = [k for k in SD_PNG_KEYS if k in png_text]
        if sd_keys:
            findings.append(Finding(0.95, 0.9, "ai_generated",
                                    f"The file contains AI generation settings (PNG field '{sd_keys[0]}'), "
                                    "as written by Stable Diffusion tools."))

        # 3. Named AI tools / editors anywhere in the metadata text
        ai_tool = next((v for k, v in AI_TOOLS.items() if k in haystack), None)
        if ai_tool:
            findings.append(Finding(0.9, 0.8, "ai_generated", f"Metadata mentions the AI image tool {ai_tool}."))

        editor = next((v for k, v in EDITORS.items() if k in haystack), None)
        if editor:
            findings.append(Finding(0.6, 0.3, "manipulated",
                                    f"The file was saved by {editor}. Editing software alone does not "
                                    "prove manipulation, but the image was opened in an editor."))

        # 4. Content Credentials (C2PA) — presence only; signature verification comes later
        if b"c2pa" in raw:
            notes.append("The file carries Content Credentials (C2PA). Their signature is not verified "
                         "in this version.")

        # 5. Camera information
        make, model = str(exif.get(MAKE, "")).strip(), str(exif.get(MODEL, "")).strip()
        camera = model if make and model.startswith(make) else f"{make} {model}".strip()
        if camera and not findings:
            findings.append(Finding(0.3, 0.25, "manipulated",
                                    f"Camera information is present ({camera}). Metadata can be edited, "
                                    "so this is weak evidence of authenticity."))

        if not findings:
            notes.append("No camera, software or AI information was found in the metadata. This is common "
                         "for images shared on social media and is not evidence either way.")
            return DetectorResult(self.name, fake_score=0.5, reliability=0.0, reasons=notes)

        main = max(findings, key=lambda f: f.reliability)
        return DetectorResult(
            self.name,
            fake_score=main.fake_score,
            reliability=main.reliability,
            fake_kind=main.fake_kind,
            reasons=[f.reason for f in sorted(findings, key=lambda f: -f.reliability)] + notes,
        )
