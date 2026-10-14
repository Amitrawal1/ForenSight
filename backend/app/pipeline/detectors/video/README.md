Video detectors (run on frames sampled by preprocessing/video.py).
- `faces.py` — face-swap model (DFDC B7) per frame → timeline + heatmap of the worst frame.
- `ai_frames.py` — AI-image model per frame → catches fully AI-generated videos.
The sound track is checked by the audio detectors (voice_clone, splice), which also run on videos.
