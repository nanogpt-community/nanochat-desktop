"""Settings management using TOML."""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel

try:
    import tomllib
except ImportError:
    import tomli as tomllib

import tomli_w

from .xdg import get_config_dir


class ServerSettings(BaseModel):
    """Server connection settings."""

    backend_url: str = ""


class UISettings(BaseModel):
    """UI preferences."""

    theme: str = "system"  # system, light, dark
    sidebar_width: int = 280


class ChatSettings(BaseModel):
    """Chat preferences."""

    default_model: str = ""


class Settings(BaseModel):
    """Application settings."""

    server: ServerSettings = ServerSettings()
    ui: UISettings = UISettings()
    chat: ChatSettings = ChatSettings()


class SettingsManager:
    """Manages application settings."""

    def __init__(self) -> None:
        self._settings_path = get_config_dir() / "config.toml"
        self._settings: Optional[Settings] = None

    @property
    def settings(self) -> Settings:
        if self._settings is None:
            self._settings = self._load()
        return self._settings

    def _load(self) -> Settings:
        """Load settings from file."""
        if self._settings_path.exists():
            with open(self._settings_path, "rb") as f:
                data = tomllib.load(f)
            return Settings.model_validate(data)
        return Settings()

    def save(self) -> None:
        """Save settings to file."""
        if self._settings:
            with open(self._settings_path, "wb") as f:
                tomli_w.dump(self._settings.model_dump(), f)

    def update(self, **kwargs: object) -> None:
        """Update settings and save."""
        # Update nested settings
        for key, value in kwargs.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
        self.save()
