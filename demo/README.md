# Demo files

Twelve small files that show what ForenSight can (and cannot) detect. They are **not in git**;
build them with:

```bash
python3 -m pip install -r demo/requirements.txt
python3 backend/scripts/download_models.py     # needed for the face swap
python3 demo/make_demo_files.py                # -> demo/files/
```

The AI-voice files need macOS (`say` command). On other systems those files are skipped.

## Files and what ForenSight says

Results measured on 2026-10-14 with the current models (CPU, MacBook Air). Times are for
analysis only, after the models are loaded.

| # | File | What it is | ForenSight result | Time |
|---|------|-----------|-------------------|------|
| 01 | `01_real_photo.jpg` | Real photo (NASA astronaut portrait) | **Likely Authentic** 69 % | 5 s |
| 02 | `02_ai_portrait.png` | AI portrait of a fictional person, straight from Stable Diffusion | **AI-Generated** 80 % (model 100 %) | 2 s |
| 03 | `03_ai_image_no_metadata.jpg` | AI image saved again as JPEG (AI settings removed) | **AI-Generated** 80 % (model alone) | 1 s |
| 04 | `04_edited_photo.jpg` | Cat photo with part of another photo pasted in | Likely Authentic — **missed** (ELA finds the area but trusts itself little on compressed photos) | 1 s |
| 05 | `05_face_swap.jpg` | AI face blended onto the astronaut | Inconclusive — **missed** (face model 45 %) | 2 s |
| 06 | `06_real_voice.wav` | Real person reading (LibriSpeech, 29 s) | **Likely Authentic** 81 % | 12 s |
| 07 | `07_ai_voice.wav` | Synthetic "scam call" voice (macOS `say`) | **AI-Generated** 83 % | 4 s |
| 08 | `08_real_voice_with_ai_part.wav` | Real recording with the AI voice inserted in the middle | **Manipulated** 80 %, timeline red only on the AI part | 15 s |
| 09 | `09_ai_voice_note.ogg` | The AI voice as a WhatsApp-style voice note | **Inconclusive** — on purpose: compressed audio is too unreliable to accuse | 5 s |
| 10 | `10_real_video.mp4` | Real photo zoom + real voice | **Likely Authentic** 80 % | 20 s |
| 11 | `11_face_swap_video.mp4` | The face swap (05) as a video + real voice | **Manipulated** 68 % (face 93 % in frames) | 20 s |
| 12 | `12_ai_video.mp4` | Slideshow of AI images + AI voice | **AI-Generated** 81 % | 6 s |

Note: 05 is missed as a still image but caught as a video (11): the video gives the face
model 12 looks instead of one.

## Sources and licences

| Source | Used for | Licence |
|--------|----------|---------|
| scikit-image sample data v0.24.0: `astronaut` (NASA), `chelsea`, `coffee` | 01, 04, 05, 10, 11 | Public domain / CC0 |
| DiffusionDB (poloclub/diffusiondb, part-000001) | 02, 03, 05 (donor face), 12 | CC0 |
| LibriSpeech (hf-internal-testing/librispeech_asr_dummy) | 06, 08, 10, 11 | CC BY 4.0 — credit: V. Panayotov et al., "LibriSpeech: an ASR corpus based on public domain audio books", ICASSP 2015 |
| macOS `say` (voice "Samantha") | 07, 08, 09, 12 | Generated locally; not redistributed |

The face swap uses a **fictional AI-generated face**, never a real person's face.
