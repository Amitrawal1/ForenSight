Image detectors.
- `ai_image.py` — learned AI-image detector (Community Forensics ViT, MIT). Strongest check.
  Grad-CAM heatmap `ai_heatmap.png` when it says AI.
- `face_swap.py` — face-swap detector (DFDC-winning EfficientNet-B7, MIT). Runs on each face
  found by YuNet; heatmap + face boxes in `faces.png`.
- `ela.py` — Error Level Analysis (JPEG only), heatmap `ela.png`.
- `fft.py` — hidden repeating patterns left by AI generators, `spectrum.png`.
