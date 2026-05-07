from __future__ import annotations

import argparse
import base64
import json
import logging
import os
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

from backend.npc_agent.assets import (
    ImageAssetSpec,
    build_npc_asset_spec,
    build_scene_asset_spec,
    build_static_asset_specs,
    ensure_generated_directories,
)
from backend.npc_agent.openai_utils import load_env_file

logger = logging.getLogger(__name__)

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
    generate_asset_specs(specs=specs, force=force, dry_run=dry_run, model=model, size=size)


def generate_asset_specs(
    *,
    specs: list[ImageAssetSpec],
    force: bool,
    dry_run: bool,
    model: str,
    size: str,
    best_effort: bool = False,
) -> None:
    ensure_generated_directories()

    if not specs:
        print("No assets found to generate.")
        return

    if dry_run:
        for spec in specs:
            status = "exists" if spec.output_path.is_file() else "missing"
            print(f"[{status}] {spec.kind}: {spec.label} -> {spec.output_path}")
        return

    try:
        client = _build_openai_client()
    except Exception:
        if best_effort:
            return
        raise

    for spec in specs:
        if spec.output_path.is_file() and not force:
            print(f"[skip] {spec.kind}: {spec.label} -> {spec.output_path}")
            continue

        print(f"[generate] {spec.kind}: {spec.label}")
        try:
            image_bytes = _generate_image_bytes(client=client, prompt=spec.prompt, model=model, size=size)
            _write_asset_files(spec=spec, image_bytes=image_bytes, model=model, size=size)
            print(f"[saved] {spec.output_path}")
        except Exception as exc:
            logger.warning("file asset generation failed | kind=%s | label=%s | size=%s | error=%s", spec.kind, spec.label, size, exc)
            if not best_effort:
                raise


def generate_inline_asset_data_urls(
    *,
    specs: list[ImageAssetSpec],
    model: str,
    size: str,
    best_effort: bool = False,
) -> dict[str, str]:
    if not specs:
        return {}

    try:
        client = _build_openai_client()
    except Exception:
        if best_effort:
            return {}
        raise

    generated: dict[str, str] = {}
    for spec in specs:
        try:
            image_bytes = _generate_image_bytes(client=client, prompt=spec.prompt, model=model, size=size)
            generated[f"{spec.kind}:{spec.key}"] = f"data:image/png;base64,{base64.b64encode(image_bytes).decode('ascii')}"
        except Exception as exc:
            logger.warning("inline asset generation failed | kind=%s | label=%s | size=%s | error=%s", spec.kind, spec.label, size, exc)
            if not best_effort:
                raise
    return generated


def build_runtime_specs_for_scene(
    *,
    scene_label: str,
    location: str,
    narrator_text: str,
    npc_profile,
    travel_options: list[dict] | None = None,
    scene_description: str = "",
    system_context: dict | None = None,
) -> list[ImageAssetSpec]:
    system_context = system_context or {}
    specs = [
        _enrich_scene_spec(
            build_scene_asset_spec(location=location, narrator_text=narrator_text, label=scene_label),
            scene_description=scene_description,
            system_context=system_context,
        ),
        _enrich_npc_spec(
            build_npc_asset_spec(npc_profile),
            system_context=system_context,
        ),
    ]
    for option in travel_options or []:
        specs.append(
            _enrich_scene_spec(
                build_scene_asset_spec(
                    location=str(option.get("location", option.get("label", ""))),
                    narrator_text=str(option.get("narrator_text", option.get("description", ""))),
                    label=str(option.get("label", "")),
                ),
                scene_description=str(option.get("description", "")),
                system_context=system_context,
            )
        )
    unique: dict[str, ImageAssetSpec] = {f"{spec.kind}:{spec.key}": spec for spec in specs}
    return list(unique.values())


def _enrich_scene_spec(spec: ImageAssetSpec, *, scene_description: str, system_context: dict) -> ImageAssetSpec:
    research_report = system_context.get("research_report") if isinstance(system_context, dict) else {}
    location_context = system_context.get("location_context") if isinstance(system_context, dict) else {}
    place_metadata = system_context.get("place_metadata") if isinstance(system_context, dict) else {}
    scene_seed = system_context.get("scene_seed") if isinstance(system_context, dict) else {}

    research_lines = [
        f"Scene description: {scene_description}." if scene_description else "",
        f"Area summary: {research_report.get('area_summary', '')}." if isinstance(research_report, dict) and research_report.get("area_summary") else "",
        f"Tone keywords: {', '.join(research_report.get('tone_keywords', [])[:5])}." if isinstance(research_report, dict) and research_report.get("tone_keywords") else "",
        f"Social norms: {', '.join(research_report.get('social_norms', [])[:4])}." if isinstance(research_report, dict) and research_report.get("social_norms") else "",
        f"Common hobbies: {', '.join(research_report.get('common_hobbies', [])[:4])}." if isinstance(research_report, dict) and research_report.get("common_hobbies") else "",
        f"Place metadata: {json.dumps(place_metadata, ensure_ascii=False)}." if place_metadata else "",
        f"Location context: {json.dumps({k: location_context.get(k) for k in ('canonical_name', 'city', 'neighborhood', 'region', 'country') if isinstance(location_context, dict) and location_context.get(k)}, ensure_ascii=False)}." if isinstance(location_context, dict) and location_context else "",
        f"Scene seed: {json.dumps(scene_seed, ensure_ascii=False)}." if scene_seed else "",
        "Do not use any reference image. Infer the setting from this context and create a grounded, specific environment.",
    ]
    enriched_prompt = spec.prompt + " " + " ".join(line for line in research_lines if line)
    return replace(spec, prompt=enriched_prompt)


def _enrich_npc_spec(spec: ImageAssetSpec, *, system_context: dict) -> ImageAssetSpec:
    research_report = system_context.get("research_report") if isinstance(system_context, dict) else {}
    location_context = system_context.get("location_context") if isinstance(system_context, dict) else {}
    scene_category = system_context.get("scene_category", "") if isinstance(system_context, dict) else ""

    context_lines = [
        f"Scene category: {scene_category}." if scene_category else "",
        f"Area summary: {research_report.get('area_summary', '')}." if isinstance(research_report, dict) and research_report.get("area_summary") else "",
        f"Tone keywords: {', '.join(research_report.get('tone_keywords', [])[:5])}." if isinstance(research_report, dict) and research_report.get("tone_keywords") else "",
        f"Location context: {json.dumps({k: location_context.get(k) for k in ('city', 'neighborhood', 'region', 'country') if isinstance(location_context, dict) and location_context.get(k)}, ensure_ascii=False)}." if isinstance(location_context, dict) and location_context else "",
        "Do not use any reference image. Use the NPC profile and local context to imply a believable setting and appearance.",
    ]
    enriched_prompt = spec.prompt + " " + " ".join(line for line in context_lines if line)
    return replace(spec, prompt=enriched_prompt)


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
