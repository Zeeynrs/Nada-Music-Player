"""Paths and persisted settings."""

import json
import os
from pathlib import Path

APP_ID = "nada"
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / APP_ID
CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / APP_ID
SETTINGS_FILE = CONFIG_DIR / "settings.json"
TOKENS_FILE = CONFIG_DIR / "tokens.json"
LIBRESPOT_CACHE = CACHE_DIR / "librespot"

REDIRECT_PORT = 8898
REDIRECT_URI = f"http://127.0.0.1:{REDIRECT_PORT}/login"

DEFAULTS = {
    "client_id": "",
    "device_name": "Nada",
    "bitrate": 320,
    "visualizer": True,
    "visualizer_style": "bars",
    "start_librespot": True,
    "normalize": False,
    # librespot softvol range in dB: 60 is librespot's default and very quiet mid-slider
    "volume_range": 20,
}


def write_private(path: Path, data: dict) -> None:
    """Write JSON readable only by the current user."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


class Settings:
    def __init__(self):
        self._data = {**DEFAULTS, **read_json(SETTINGS_FILE)}

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        if self._data.get(key) != value:
            self._data[key] = value
            write_private(SETTINGS_FILE, self._data)
