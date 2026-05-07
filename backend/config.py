from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    """Environment-backed application settings for the dynamic world pipeline."""

    world_store_mode: str = "memory"
    world_data_dir: Path = Path("data")
    provider_timeout_seconds: float = 10.0
    provider_max_retries: int = 2
    booking_fetch_enabled: bool = True
    geocoding_enabled: bool = True
    overpass_enabled: bool = True
    search_enabled: bool = True
    enable_image_generation: bool = False
    enable_inline_image_data: bool = False
    inline_image_model: str = "gpt-image-2"
    inline_image_size: str = "816x816"
    inline_image_quality: str = "low"
    inline_image_output_format: str = "jpeg"
    research_max_agent_steps: int = 3

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            world_store_mode=os.environ.get("WORLD_STORE_MODE", "memory").strip().lower() or "memory",
            world_data_dir=Path(os.environ.get("WORLD_DATA_DIR", "data")),
            provider_timeout_seconds=_read_float_env("PROVIDER_TIMEOUT_SECONDS", 10.0),
            provider_max_retries=_read_int_env("PROVIDER_MAX_RETRIES", 2),
            booking_fetch_enabled=_read_bool_env("ENABLE_BOOKING_FETCH", True),
            geocoding_enabled=_read_bool_env("ENABLE_GEOCODING", True),
            overpass_enabled=_read_bool_env("ENABLE_OVERPASS", True),
            search_enabled=_read_bool_env("ENABLE_SEARCH", True),
            enable_image_generation=_read_bool_env("ENABLE_IMAGE_GENERATION", False),
            enable_inline_image_data=_read_bool_env("ENABLE_INLINE_IMAGE_DATA", False),
            inline_image_model=os.environ.get("INLINE_IMAGE_MODEL", os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-2")).strip() or "gpt-image-2",
            inline_image_size=os.environ.get("INLINE_IMAGE_SIZE", os.environ.get("OPENAI_IMAGE_SIZE", "816x816")).strip() or "816x816",
            inline_image_quality=os.environ.get("INLINE_IMAGE_QUALITY", os.environ.get("OPENAI_IMAGE_QUALITY", "low")).strip() or "low",
            inline_image_output_format=os.environ.get("INLINE_IMAGE_OUTPUT_FORMAT", os.environ.get("OPENAI_IMAGE_OUTPUT_FORMAT", "jpeg")).strip().lower() or "jpeg",
            research_max_agent_steps=_read_int_env("RESEARCH_MAX_AGENT_STEPS", 3),
        )


def _read_bool_env(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _read_int_env(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


def _read_float_env(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None:
        return default

    try:
        return float(value)
    except ValueError:
        return default
