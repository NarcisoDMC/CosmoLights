"""
config_manager.py - Persistent Local Configuration Management for CosmoLights.

Stores user settings in %APPDATA%/CosmoLights/config.json so calibration,
brightness, aspect ratio, monitor preferences, and last active mode persist across restarts.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any


def get_config_dir() -> Path:
    """Returns the platform-standard config directory for CosmoLights."""
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            base = Path(appdata)
        else:
            base = Path.home() / "AppData" / "Roaming"
    else:
        base = Path.home() / ".config"

    cfg_dir = base / "CosmoLights"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir


def get_config_file() -> Path:
    return get_config_dir() / "config.json"


DEFAULT_APP_CONFIG: Dict[str, Any] = {
    # Hardware & Strip calibration
    "start_side": "left",
    "reverse_order": False,
    "zone_offset": 0,
    # Ambilight Parameters
    "target_fps": 30,
    "smoothing": 0.40,
    "saturation_boost": 1.25,
    "brightness": 100,
    "border_depth": 0.08,
    "aspect_ratio": "auto",
    "black_cutoff": 15,
    "gamma": 2.0,
    "selected_monitor": 0,
    # Mode & Color presets
    "last_mode": "ambilight",  # "ambilight", "solid", "effect", "off"
    "last_solid_rgb": [0, 240, 255],
    "last_effect_id": "rainbow_flow",
    "effect_speed": 1.0,
    "audio_sensitivity": 1.2,
}


class ConfigManager:
    """Thread-safe persistent configuration store."""

    _instance = None

    def __init__(self):
        self._file_path = get_config_file()
        self._data = dict(DEFAULT_APP_CONFIG)
        self.load()

    @classmethod
    def get_instance(cls) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = ConfigManager()
        return cls._instance

    def load(self) -> Dict[str, Any]:
        """Loads configuration from JSON file or writes defaults if missing."""
        if self._file_path.exists():
            try:
                with open(self._file_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    if isinstance(saved, dict):
                        self._data.update(saved)
            except Exception as e:
                print(f"[ConfigManager] Error reading config file {self._file_path}: {e}")
        else:
            self.save()

        return dict(self._data)

    def save(self) -> bool:
        """Writes current configuration to JSON file safely."""
        try:
            temp_file = self._file_path.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            temp_file.replace(self._file_path)
            return True
        except Exception as e:
            print(f"[ConfigManager] Error saving config: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    def update(self, new_values: Dict[str, Any]) -> None:
        self._data.update(new_values)
        self.save()

    def get_all(self) -> Dict[str, Any]:
        return dict(self._data)
