"""Download the small model files ForenSight needs into the models/ folder.

Run from the project root (only needs plain Python, no extra packages):

    python backend/scripts/download_models.py

Files are checked with a SHA-256 checksum, so a broken or changed download is rejected.
"""

import argparse
import hashlib
import shutil
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

# AI-image model: pinned to one exact version (commit) so results never change by surprise
CF_URL = (
    "https://huggingface.co/buildborderless/CommunityForensics-DeepfakeDet-ViT/resolve/"
    "ac6ee457bea904a373065754107451793b56db00"
)

# file path inside models/ -> (download url, sha256 checksum to make sure the file is correct)
MODELS = {
    # Face detector (OpenCV YuNet, 230 KB)
    "face_detection_yunet_2023mar.onnx": (
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
    ),
    # AI-image detector (Community Forensics ViT, 87 MB, MIT licence)
    "community_forensics_vit/config.json": (
        f"{CF_URL}/config.json",
        "4b425d089842fecf8f25fc52aa44d09f49607ef89a0e2ff685ced6ec1c70e9b1",
    ),
    "community_forensics_vit/model.safetensors": (
        f"{CF_URL}/model.safetensors",
        "275ba982236ddd6afddf7131f8133e89f537574b964cf8fa5825b4956d741692",
    ),
    # Face-swap detector (DFDC challenge winner, EfficientNet-B7, 267 MB, MIT licence)
    "dfdc_efficientnet_b7.pt": (
        "https://github.com/selimsef/dfdc_deepfake_challenge/releases/download/0.0.1/"
        "final_111_DeepFakeClassifier_tf_efficientnet_b7_ns_0_36",
        "9db77ab9318863e2f8ab287c8eb83c2232584b82dc2fb41f1d614ddd7900cccb",
    ),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ssl_context() -> ssl.SSLContext:
    """Use the certifi certificate bundle if installed (fixes SSL errors on some Macs)."""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def download(url: str, dest: Path) -> None:
    with urllib.request.urlopen(url, context=ssl_context()) as resp, dest.open("wb") as f:
        shutil.copyfileobj(resp, f)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="models", help="folder to save models in (default: models)")
    out = Path(parser.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)

    for name, (url, checksum) in MODELS.items():
        dest = out / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_file() and sha256(dest) == checksum:
            print(f"ok       {name} (already downloaded)")
            continue
        print(f"download {name} ...")
        tmp = dest.with_suffix(".part")
        try:
            download(url, tmp)
        except urllib.error.URLError as e:
            print(f"ERROR    {name}: {e.reason}", file=sys.stderr)
            if isinstance(e.reason, ssl.SSLError):
                print("         Fix on macOS: open the 'Install Certificates.command' file in your "
                      "Python folder (Applications > Python 3.x), or run: pip install certifi",
                      file=sys.stderr)
            return 1
        if sha256(tmp) != checksum:
            tmp.unlink()
            print(f"ERROR    {name}: checksum does not match, file not saved", file=sys.stderr)
            return 1
        tmp.rename(dest)
        print(f"ok       {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
