"""Make a downloadable PDF report for one analysis (with ReportLab).

The report contains: the verdict and confidence, the main reasons, evidence pictures
(heatmaps), a timeline for audio/video, a table with every check, what the user should
do next, and the limits of the tool.
"""

from datetime import datetime
from pathlib import Path

from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from xml.sax.saxutils import escape

PAGE_W = A4[0] - 36 * mm  # usable width

VERDICTS = {
    "likely_authentic": ("Likely Authentic", colors.HexColor("#047857"), colors.HexColor("#ecfdf5")),
    "ai_generated": ("AI-Generated", colors.HexColor("#be123c"), colors.HexColor("#fff1f2")),
    "manipulated": ("Manipulated", colors.HexColor("#b45309"), colors.HexColor("#fffbeb")),
    "inconclusive": ("Inconclusive", colors.HexColor("#334155"), colors.HexColor("#f1f5f9")),
}

# Plain advice for each verdict
NEXT_STEPS = {
    "ai_generated": [
        "Do not share this content as if it were real.",
        "If it asks for money, passwords or personal details, do not act on it.",
        "Look for the original source, for example the official account or news outlet.",
    ],
    "manipulated": [
        "Treat this content with caution: parts of it may have been changed.",
        "If it shows a person you know, contact them directly on a number or account you already trust.",
        "Look for the original, unedited version before believing or sharing it.",
    ],
    "inconclusive": [
        "ForenSight could not tell whether this content is real.",
        "If possible, get the original file (not a forwarded or compressed copy) and check it again.",
        "Verify through a trusted channel before acting on it, especially for money requests.",
    ],
    "likely_authentic": [
        "No signs of AI generation or editing were found, but this is not proof that it is real.",
        "If something still feels wrong (for example an urgent request for money), verify it anyway.",
    ],
}

LIMITATIONS = (
    "ForenSight combines several independent checks, but no detector is perfect. Very new AI tools "
    "may not be detected, and heavily compressed files (for example forwarded many times) are harder "
    "to judge. Use this report to support a human decision, not to replace it."
)

# Evidence pictures a check may have saved, with a caption
PICTURES = {
    "ai_heatmap.png": "AI-image model: red areas influenced the model most.",
    "faces.png": "Face-swap model: boxes show each face (red = suspicious), heat shows where the model looked.",
    "video_faces.png": "Most suspicious video frame: face boxes and where the face-swap model looked.",
    "ela.png": "Error Level Analysis: red areas recompress differently and may have been edited.",
}


def _styles():
    base = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=base["Normal"], fontName="Helvetica", fontSize=9.5, leading=13.5)
    return {
        "body": body,
        "small": ParagraphStyle("small", parent=body, fontSize=8, leading=10.5, textColor=colors.HexColor("#475569")),
        "h1": ParagraphStyle("h1", parent=body, fontName="Helvetica-Bold", fontSize=20, leading=24),
        "h2": ParagraphStyle("h2", parent=body, fontName="Helvetica-Bold", fontSize=12, leading=16,
                             spaceBefore=10, spaceAfter=4),
        "cell": ParagraphStyle("cell", parent=body, fontSize=8.5, leading=11),
        # Big verdict title: needs its own line height, or it overlaps the next line
        "verdict": ParagraphStyle("verdict", parent=body, fontSize=18, leading=22),
    }


def _text(s: str) -> str:
    """Make text safe for ReportLab paragraphs (they use a small HTML-like markup)."""
    return escape(str(s))


def _verdict_box(verdict: str, confidence: float | None, summary: str, st) -> Table:
    label, color, background = VERDICTS.get(verdict, VERDICTS["inconclusive"])
    title = Paragraph(f'<font color="{color.hexval()}"><b>{label}</b></font>', st["verdict"])
    lines = [title, Spacer(1, 4), Paragraph(_text(summary), st["body"])]
    if verdict != "inconclusive" and confidence is not None:
        lines.append(Paragraph(f"Confidence: <b>{round(confidence * 100)}%</b>", st["body"]))
    box = Table([[lines]], colWidths=[PAGE_W])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), background),
        ("BOX", (0, 0), (-1, -1), 1, color),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return box


def _score_color(score: float):
    if score >= 0.65:
        return colors.HexColor("#f43f5e")
    if score >= 0.5:
        return colors.HexColor("#fb923c")
    if score > 0.35:
        return colors.HexColor("#facc15")
    return colors.HexColor("#34d399")


def _timeline(detectors: list[dict], duration: float) -> Drawing | None:
    """One coloured row per check that scored parts of an audio/video file."""
    rows = [d for d in detectors if d.get("segments")]
    if not rows or duration <= 0:
        return None
    label_w, row_h, gap = 45 * mm, 12, 6
    bar_w = PAGE_W - label_w
    height = len(rows) * (row_h + gap) + 14
    drawing = Drawing(PAGE_W, height)
    for i, d in enumerate(rows):
        y = height - (i + 1) * (row_h + gap)
        drawing.add(String(0, y + 3, d["label"][:32], fontName="Helvetica", fontSize=8))
        drawing.add(Rect(label_w, y, bar_w, row_h, fillColor=colors.HexColor("#f1f5f9"), strokeColor=None))
        for seg in d["segments"]:
            x = label_w + bar_w * seg["start_s"] / duration
            w = max(1.0, bar_w * (min(seg["end_s"], duration) - seg["start_s"]) / duration)
            drawing.add(Rect(x, y, w, row_h, fillColor=_score_color(seg["score"]), strokeColor=None,
                             fillOpacity=0.85))
    # Time axis: start, middle, end
    drawing.add(Line(label_w, 8, label_w + bar_w, 8, strokeColor=colors.HexColor("#94a3b8"), strokeWidth=0.5))
    for frac in (0, 0.5, 1):
        t = duration * frac
        drawing.add(String(label_w + bar_w * frac - (14 if frac == 1 else 0), 0, f"{int(t // 60)}:{int(t % 60):02d}",
                           fontName="Helvetica", fontSize=7))
    return drawing


def _picture(path: Path, caption: str, st, max_w: float = PAGE_W * 0.6, max_h: float = 75 * mm) -> KeepTogether:
    img = Image(str(path))
    scale = min(max_w / img.imageWidth, max_h / img.imageHeight, 1.0)
    img.drawWidth, img.drawHeight = img.imageWidth * scale, img.imageHeight * scale
    img.hAlign = "LEFT"
    return KeepTogether([img, Spacer(1, 2), Paragraph(_text(caption), st["small"]), Spacer(1, 6)])


def _checks_table(detectors: list[dict], st) -> Table:
    data = [[Paragraph("<b>Check</b>", st["cell"]), Paragraph("<b>Fake score</b>", st["cell"]),
             Paragraph("<b>Trust</b>", st["cell"]), Paragraph("<b>Finding</b>", st["cell"])]]
    for d in sorted(detectors, key=lambda d: -d["reliability"]):
        info_only = d["reliability"] <= 0
        data.append([
            Paragraph(_text(d["label"]), st["cell"]),
            Paragraph("info only" if info_only else f"{round(d['fake_score'] * 100)}%", st["cell"]),
            Paragraph("-" if info_only else f"{round(d['reliability'] * 100)}%", st["cell"]),
            Paragraph(_text(" ".join(d["reasons"][:2])), st["cell"]),
        ])
    table = Table(data, colWidths=[38 * mm, 20 * mm, 15 * mm, PAGE_W - 73 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return table


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(18 * mm, 10 * mm, "ForenSight - explainable deepfake forensics")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_report(analysis, artifact_dir: Path, out_path: Path) -> Path:
    """Write the PDF for one finished analysis and return its path.

    `analysis` is the database row (app.db.models.Analysis).
    """
    st = _styles()
    ev = analysis.evidence or {}
    detectors = ev.get("detectors", [])
    verdict = analysis.verdict.value if analysis.verdict else "inconclusive"
    created = analysis.created_at or datetime.now()

    story = [
        Paragraph("ForenSight report", st["h1"]),
        Paragraph(
            f"File: <b>{_text(analysis.filename)}</b> ({analysis.media_type.value}) &nbsp;·&nbsp; "
            f"Checked: {created:%d %B %Y, %H:%M} &nbsp;·&nbsp; Report ID: {analysis.id[:8]}",
            st["small"],
        ),
        Spacer(1, 10),
        _verdict_box(verdict, analysis.confidence, ev.get("summary", ""), st),
    ]

    if ev.get("reasons"):
        story.append(Paragraph("Why", st["h2"]))
        story += [Paragraph(f"• {_text(r)}", st["body"]) for r in ev["reasons"]]

    story.append(Paragraph("What you should do next", st["h2"]))
    story += [Paragraph(f"• {_text(s)}", st["body"]) for s in NEXT_STEPS.get(verdict, [])]

    # Evidence pictures and timeline
    pictures = [(artifact_dir / name, caption) for name, caption in PICTURES.items()
                if any(d.get("heatmap") == name for d in detectors) and (artifact_dir / name).is_file()]
    timeline = _timeline(detectors, (ev.get("media") or {}).get("duration_s", 0))
    if pictures or timeline:
        story.append(Paragraph("Evidence", st["h2"]))
    if timeline:
        story += [Paragraph("Timeline (green = sounds/looks real, red = sounds/looks fake):", st["small"]),
                  Spacer(1, 4), timeline, Spacer(1, 8)]
    for path, caption in pictures:
        story.append(_picture(path, caption, st))

    if detectors:
        story.append(Paragraph("Every check", st["h2"]))
        story.append(_checks_table(detectors, st))
        story.append(Paragraph('"Trust" is how much each check counts in the final verdict.', st["small"]))

    if ev.get("notes"):
        story.append(Paragraph("Notes", st["h2"]))
        story += [Paragraph(f"• {_text(n)}", st["body"]) for n in ev["notes"]]

    story += [Paragraph("Limitations", st["h2"]), Paragraph(_text(LIMITATIONS), st["small"])]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(out_path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=18 * mm,
                            title=f"ForenSight report - {analysis.filename}", author="ForenSight")
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return out_path
