"""XDG Base Directory helpers."""

import os
from pathlib import Path


def get_config_dir() -> Path:
    """Get XDG config directory for NanoChat."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
    config_dir = Path(xdg_config) / "nanochat"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_data_dir() -> Path:
    """Get XDG data directory for NanoChat."""
    xdg_data = os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
    data_dir = Path(xdg_data) / "nanochat"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_cache_dir() -> Path:
    """Get XDG cache directory for NanoChat."""
    xdg_cache = os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")
    cache_dir = Path(xdg_cache) / "nanochat"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir
