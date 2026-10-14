"""Grad-CAM: find which parts of the image made a model say "fake".

How it works, in short:
1. Run the image through the model and keep the output of one inner layer
   (a grid of "features", one cell per image area).
2. Ask PyTorch how much each feature would change the "fake" score (the gradient).
3. Areas whose features push the score up the most get the highest heat.

Works for CNNs (EfficientNet) and, with `to_grid`, for Vision Transformers (ViT).
"""

from typing import Callable

import numpy as np


def grad_cam(forward: Callable, layer, x, to_grid: Callable | None = None) -> np.ndarray:
    """Return a 2D map with values 0..1 (1 = most important for the "fake" score).

    forward: function that takes the input tensor and returns ONE number (the fake logit)
    layer:   the inner layer to look at (usually the last one before pooling)
    x:       input tensor, shape 1xCxHxW
    to_grid: turns the layer output into shape 1xCxHxW (needed for ViT, which outputs tokens)
    """
    import torch

    saved = {}

    def keep_output(_module, _inputs, output):
        saved["act"] = output[0] if isinstance(output, tuple) else output

    handle = layer.register_forward_hook(keep_output)
    try:
        with torch.enable_grad():
            logit = forward(x)
            # Gradient of the fake score with respect to this layer only
            # (cheaper than backward(), which would store gradients for every weight)
            (grad,) = torch.autograd.grad(logit, saved["act"])
    finally:
        handle.remove()

    act, grad = saved["act"].detach(), grad.detach()
    if to_grid is not None:
        act, grad = to_grid(act), to_grid(grad)

    # Importance of each feature channel = its average gradient
    weights = grad.mean(dim=(2, 3), keepdim=True)
    # Keep only areas that push towards "fake"
    cam = torch.relu((weights * act).sum(dim=1))[0]
    cam = cam / (cam.max() + 1e-8)
    return cam.numpy()


def vit_tokens_to_grid(tokens, has_cls_token: bool = True):
    """ViT gives a list of patch tokens; turn it back into a square grid 1xCxHxW."""
    if has_cls_token:
        tokens = tokens[:, 1:, :]  # drop the summary (CLS) token, keep image patches
    n = int(round(tokens.shape[1] ** 0.5))
    return tokens.reshape(tokens.shape[0], n, n, tokens.shape[2]).permute(0, 3, 1, 2)
