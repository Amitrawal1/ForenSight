Audio detectors.
- `splice.py` — finds places where the background sound suddenly changes shape
  (= recordings joined together). Gives timeline segments.
- `voice_clone.py` — AI-voice model (XLSR-SLS, ONNX, MIT) scored per ~4 s window → timeline.
