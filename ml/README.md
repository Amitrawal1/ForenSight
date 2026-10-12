# ML workspace

Training / evaluation code for the detectors. Runs in the `ml` Docker service:

    docker compose --profile ml up ml        # Jupyter → http://localhost:8888

- `training/{image,video,audio}/` — training scripts per modality
- `configs/` — YAML hyper-parameters
- `evaluation/` — metrics (AUC, EER, accuracy per dataset)
- `notebooks/` — exploration

Datasets go in `../data/raw/`, trained weights are exported to `../models/`
(mounted read-only into backend/worker).

Note: the ml image is CPU-only. For real training use a GPU machine / Colab and copy
the weights into `models/`.
