# ForenSight — 3-minute demo script

**Goal:** show that ForenSight gives a clear verdict **and the reason**, for images, audio
and video, and that it is honest when it isn't sure.

Files are in `demo/files/` (see `demo/README.md`).

---

## Before the demo (checklist)

- [ ] App running: `docker compose up` → open http://localhost:5173, green dot in the header.
- [ ] **Warm up the models**: upload `01_real_photo.jpg` and `06_real_voice.wav` once
      (first use loads the models: 5–10 s extra).
- [ ] **Pre-run every demo file** so all results are in **History**. If the live upload is
      slow or the Wi-Fi fails, open the result from History instead.
- [ ] Download one PDF report in advance (e.g. from file 08) and keep it open in a tab.
- [ ] Close other heavy apps (video analysis uses the CPU for ~20 s).
- [ ] Browser zoom ~110 % so judges can read the reasons.

---

## The flow (≈ 3 minutes)

### 0:00 — The problem (20 s)
> "Voice-clone scam calls, fake celebrity videos and face-swapped KYC videos are already
> costing people money. Existing detectors give you a number like '0.83 fake' — no reason,
> one media type, made for experts. ForenSight checks images, audio and video, and tells
> you **why**."

### 0:20 — AI image (30 s) → `03_ai_image_no_metadata.jpg`
- Drag the file in. Result: **AI-Generated**.
- Click the **AI focus** tab: heatmap of where the model looked.
> "This image had its AI settings removed, so there's no label to read. Our AI-image model,
> trained on images from about 4,800 different generators, still recognises it."
- *(Optional, 10 s)* Upload `02_ai_portrait.png`: two reasons — the file itself says it was
  made by Stable Diffusion, and the model agrees. "A fake profile photo of a person who
  doesn't exist."

### 0:50 — The scam call (50 s) → `08_real_voice_with_ai_part.wav` ⭐ main moment
- Result: **Manipulated**.
- Point at the **timeline**: the AI-voice row is green, then **red in the middle**, then
  green. The splice row marks where recordings were joined.
- Click the red part → the player jumps there → let it play 3 seconds.
> "This is a real recording with an AI voice inserted — 'send me money, don't tell anyone'.
> ForenSight doesn't just say fake: it shows **which seconds** are fake and why."

### 1:40 — Face swap in a video (35 s) → `11_face_swap_video.mp4`
- Result: **Manipulated**. Face-swap row red across the video.
- Show **Most suspicious frame** → heatmap on the face → **Jump to** button.
> "The model behind this check won Facebook's Deepfake Detection Challenge. The heatmap shows
> it focused on the face — the part that was swapped."

### 2:15 — Honesty (25 s) → `09_ai_voice_note.ogg`
- Result: **Inconclusive**. Open the AI-voice check: the model thinks it's AI, but…
> "This is the same AI voice as a WhatsApp voice note. In our tests, compression made real
> voices look fake too — so instead of risking a false accusation, ForenSight says
> Inconclusive and explains why. **A wrong confident answer is worse than no answer.**"

### 2:40 — Report + wrap-up (20 s)
- Click **Download PDF report** (or show the pre-downloaded one): verdict, reasons, timeline,
  **what to do next** ("contact the person on a number you already trust").
- Show **History** for a second.
> "Several independent checks, plain-language reasons, heatmaps and timelines, a report a
> normal person can use — and the honesty to say 'not sure'."

---

## Likely judge questions

**How accurate is it?**
Be honest — these are our own small tests, not a benchmark:
- AI images: 40/40 Stable Diffusion images caught, metadata removed. 14/16 real photos
  correct (misses: a processed astronomy image).
- Faces: 2 false alarms in 100 real face photos.
- Voice: on clean audio of 8 s or more, 8 of 11 synthetic voices caught and **0 false
  accusations** on 40 real voices; on compressed audio we deliberately say Inconclusive.
- The voice model's published error on real-world deepfakes ("In-the-Wild") is about 7.5 %.

**What does it miss?** (show if asked)
- `04_edited_photo.jpg`: a pasted region in an already-compressed photo → missed (ELA is a
  weak check on compressed photos).
- `05_face_swap.jpg`: the same face swap as file 11, but as a single photo → Inconclusive.
  The video is caught because it gives the model many frames.
- Cloned voices in compressed voice notes → Inconclusive, not "AI".
- Very new generators may not be detected until the models are updated.

**Why several checks instead of one model?**
Harder to fool, each check explains itself, and new checks can be added without
rewriting the system. Fusion scores "AI-made" and "edited" separately, so they don't
cancel each other out.

**Which models?** All freely licensed (MIT): Community Forensics ViT (CVPR 2025) for AI
images, the DFDC-winning EfficientNet-B7 for faces, XLSR-SLS (ACM MM 2024) for voices,
plus our own heatmaps (Grad-CAM), metadata, ELA, frequency and splice checks.

**Privacy?** Files stay on the server, can be deleted from History; nothing is sent to
third-party services.

**What's next?** Fine-tuning with compression augmentation (for WhatsApp audio), testing on
real deepfake datasets (FaceForensics++, Celeb-DF, DFDC), lip-sync detection, verifying C2PA
content credentials.

---

## Backup plan

| Problem | Do this |
|---------|---------|
| Upload is slow | Talk through the problem slide while it runs; or open the pre-run result from **History** |
| App down | Show the pre-downloaded PDF reports + screenshots |
| A result differs from this script | Say so — "this is a live system" — and explain what the checks say; don't hide it |
