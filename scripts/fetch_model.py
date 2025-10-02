from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from urllib.request import urlopen

BUFFER_SIZE = 1024 * 1024
MODEL_URL = "https://huggingface.co/TinyLlama/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/TinyLlama-1.1B-Chat-v1.0-q4_k_m.gguf?download=1"
EXPECTED_SHA256 = "50c06cbd2d51b400ebd5af4c7cb3f7023bf67b7e20e5c662cf4d34850f9c1925"


def download_model(target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        print(f"Model already exists at {target}")
        return
    print(f"Downloading TinyLlama model to {target} ...")
    response = urlopen(MODEL_URL)
    hasher = hashlib.sha256()
    with target.open("wb") as fh:
        while True:
            chunk = response.read(BUFFER_SIZE)
            if not chunk:
                break
            fh.write(chunk)
            hasher.update(chunk)
    digest = hasher.hexdigest()
    if digest != EXPECTED_SHA256:
        target.unlink(missing_ok=True)
        raise SystemExit(f"Checksum mismatch for model: expected {EXPECTED_SHA256}, got {digest}")
    print("Model download complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download the default TinyLlama GGUF model.")
    parser.add_argument("--output", type=Path, default=Path("models/TinyLlama-1.1B-Chat-q4_k_m.gguf"))
    args = parser.parse_args()
    download_model(args.output.resolve())


if __name__ == "__main__":
    main()
