import numpy as np
import pytest

torch = pytest.importorskip("torch")

from app.pipeline.explain.gradcam import grad_cam, vit_tokens_to_grid  # noqa: E402


def test_gradcam_points_at_the_bright_area():
    # Tiny "model": score = sum of the top-left quarter of a feature map
    conv = torch.nn.Conv2d(1, 4, kernel_size=1)
    torch.nn.init.constant_(conv.weight, 1.0)
    torch.nn.init.zeros_(conv.bias)

    def forward(x):
        return conv(x)[:, :, :4, :4].sum()

    x = torch.zeros(1, 1, 8, 8)
    x[:, :, :4, :4] = 1.0
    cam = grad_cam(forward, conv, x)
    assert cam.shape == (8, 8)
    assert cam[:4, :4].min() > 0.9 and cam[4:, 4:].max() == 0.0


def test_vit_tokens_to_grid_drops_cls_token():
    tokens = torch.zeros(1, 1 + 24 * 24, 384)
    assert tuple(vit_tokens_to_grid(tokens).shape) == (1, 384, 24, 24)
