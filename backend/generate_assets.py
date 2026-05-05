from __future__ import annotations

import argparse
import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

from npc_agent.assets import (
    ImageAssetSpec,
    build_static_asset_specs,
    ensure_generated_directories,
)
from npc_agent.openai_utils import load_env_file

DEFAULT_IMAGE_MODEL = "gpt-image-1"
DEFAULT_IMAGE_SIZE = "1024x1024"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate cached scene backgrounds and NPC headshots for the web client."
    )
    parser.add_argument(
        "--kind",
        choices=("all", "scenes", "npcs"),
        default="all",
        help="Which assets to generate.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate assets even if the cached PNG already exists.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be generated without calling the OpenAI API.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OPENAI_IMAGE_MODEL", DEFAULT_IMAGE_MODEL),
        help="OpenAI image model name.",
    )
    parser.add_argument(
        "--size",
        default=os.getenv("OPENAI_IMAGE_SIZE", DEFAULT_IMAGE_SIZE),
        help="Requested image size.",
    )
    return parser.parse_args()


def generate_assets(*, kind: str, force: bool, dry_run: bool, model: str, size: str) -> None:
    ensure_generated_directories()
    specs = build_static_asset_specs(kind)

    if not specs:
        print("No assets found to generate.")
        return

    if dry_run:
        for spec in specs:
            status = "exists" if spec.output_path.is_file() else "missing"
            print(f"[{status}] {spec.kind}: {spec.label} -> {spec.output_path}")
        return

    client = _build_openai_client()

    for spec in specs:
        if spec.output_path.is_file() and not force:
            print(f"[skip] {spec.kind}: {spec.label} -> {spec.output_path}")
            continue

        print(f"[generate] {spec.kind}: {spec.label}")
        image_bytes = _generate_image_bytes(client=client, prompt=spec.prompt, model=model, size=size)
        _write_asset_files(spec=spec, image_bytes=image_bytes, model=model, size=size)
        print(f"[saved] {spec.output_path}")


def _build_openai_client():
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "The 'openai' package is required to generate image assets. "
            "Install it with `pip install openai`."
        ) from exc

    load_env_file()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    return OpenAI(api_key=api_key)


def _generate_image_bytes(*, client, prompt: str, model: str, size: str) -> bytes:
    response = client.images.generate(
        model=model,
        prompt=prompt,
        size=size,
    )

    if not getattr(response, "data", None):
        raise RuntimeError("Image API returned no data.")

    first_image = response.data[0]
    b64_json = getattr(first_image, "b64_json", None)
    if b64_json:
        return base64.b64decode(b64_json)

    image_url = getattr(first_image, "url", None)
    if image_url:
        with urlopen(image_url) as response_stream:
            return response_stream.read()

    raise RuntimeError("Image API response did not contain b64_json or url image data.")


def _write_asset_files(*, spec: ImageAssetSpec, image_bytes: bytes, model: str, size: str) -> None:
    spec.output_path.parent.mkdir(parents=True, exist_ok=True)
    spec.metadata_path.parent.mkdir(parents=True, exist_ok=True)
    spec.output_path.write_bytes(image_bytes)

    metadata = {
        "kind": spec.kind,
        "key": spec.key,
        "label": spec.label,
        "model": model,
        "size": size,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "relative_path": spec.relative_path,
        "prompt": spec.prompt,
        "source": spec.source,
    }
    spec.metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


if __name__ == "__main__":
    args = parse_args()
    generate_assets(
        kind=args.kind,
        force=args.force,
        dry_run=args.dry_run,
        model=args.model,
        size=args.size,
    )
