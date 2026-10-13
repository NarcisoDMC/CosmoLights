"""
api.py - Python-to-JavaScript Bridge API for CosmoLights.

Exposed directly to the Web UI via pywebview (window.pywebview.api).
Coordinates LED hardware, screen capture, procedural light patterns,
audio visualizers, calibration, and live telemetry.
Includes persistent storage in %APPDATA%/CosmoLights/config.json.
"""

from typing import Dict, Any, List, Optional
import os

from ..driver.led_driver import LedDriver
from ..capture.windows_dxgi import WindowsDXGICapture
from ..engine.ambilight import AmbilightEngine
from ..engine.effects import CustomEffectsEngine
from ..engine.config_manager import ConfigManager


class CosmoLightsAPI:
    """Bridge API exposed to the JavaScript frontend."""

    def __init__(self):
        self.config_mgr = ConfigManager.get_instance()
        saved = self.config_mgr.get_all()

        monitors = WindowsDXGICapture.list_monitors()
        valid_indices = [m["output_idx"] for m in monitors]
        selected_mon = int(saved.get("selected_monitor", 0))
        if selected_mon not in valid_indices and valid_indices:
            selected_mon = valid_indices[0]
            self.config_mgr.set("selected_monitor", selected_mon)

        self.driver = LedDriver()
        self.capture = WindowsDXGICapture(output_idx=selected_mon)

        # Initialize engine with saved parameters
        self.engine = AmbilightEngine(self.driver, self.capture, config=saved)
        self.effects = CustomEffectsEngine(self.driver)

        self._current_mode = "off"
        self._current_brightness = int(saved.get("brightness", 100))
        solid_list = saved.get("last_solid_rgb", [0, 240, 255])
        self._last_solid = tuple(solid_list) if len(solid_list) == 3 else (0, 240, 255)

        self.effects.set_speed(float(saved.get("effect_speed", 1.0)))
        self.effects.set_audio_sensitivity(float(saved.get("audio_sensitivity", 1.2)))
        self.effects.set_brightness(self._current_brightness)

    def initialize(self) -> Dict[str, Any]:
        """Initial connection, hardware check and settings restoration."""
        connected = self.driver.connect()
        monitors = WindowsDXGICapture.list_monitors()
        valid_indices = [m["output_idx"] for m in monitors]
        saved = self.config_mgr.get_all()
        selected_mon = int(saved.get("selected_monitor", 0))
        if selected_mon not in valid_indices and valid_indices:
            selected_mon = valid_indices[0]
            self.config_mgr.set("selected_monitor", selected_mon)

        cfg = dict(self.engine.config)
        cfg["brightness"] = self._current_brightness

        return {
            "connected": connected,
            "monitors": monitors,
            "selected_monitor": selected_mon,
            "current_mode": self._current_mode,
            "config": cfg,
            "brightness": self._current_brightness,
            "last_solid_rgb": list(self._last_solid),
            "last_effect_id": saved.get("last_effect_id", "rainbow_flow"),
            "effect_speed": saved.get("effect_speed", 1.0),
            "audio_sensitivity": saved.get("audio_sensitivity", 1.2),
            "effects_list": CustomEffectsEngine.EFFECTS_LIST
        }

    def list_monitors(self) -> List[Dict[str, Any]]:
        """Returns detected monitors with fresh system scan."""
        return WindowsDXGICapture.list_monitors()

    def set_monitor(self, output_idx: int) -> bool:
        """Switches capture to another monitor and saves preference."""
        output_idx = int(output_idx)
        self.config_mgr.set("selected_monitor", output_idx)
        was_running = self.engine.is_running
        if was_running:
            self.engine.stop()

        if hasattr(self.capture, "release"):
            self.capture.release()

        self.capture = WindowsDXGICapture(output_idx=output_idx)
        self.engine.capture = self.capture

        if was_running:
            return self.engine.start()
        return True

    def toggle_ambilight(self, enable: bool) -> Dict[str, Any]:
        """Starts or stops the live Ambilight screen capture stream."""
        if enable:
            if self.effects.is_running:
                self.effects.stop()
            success = self.engine.start()
            if success:
                self._current_mode = "ambilight"
                self.config_mgr.set("last_mode", "ambilight")
            return {"success": success, "mode": self._current_mode}
        else:
            self.engine.stop()
            self._current_mode = "off"
            self.config_mgr.set("last_mode", "off")
            return {"success": True, "mode": self._current_mode}

    def set_solid_color(self, r: int, g: int, b: int) -> bool:
        """Sets a uniform static color on the LED strip and persists it."""
        if self.engine.is_running:
            self.engine.stop()
        if self.effects.is_running:
            self.effects.stop()

        self._last_solid = (r, g, b)
        self.config_mgr.update({
            "last_solid_rgb": [r, g, b],
            "last_mode": "solid"
        })

        if not self.driver.is_connected:
            if not self.driver.connect():
                return False

        factor = self._current_brightness / 100.0
        sr = max(0, min(255, int(r * factor)))
        sg = max(0, min(255, int(g * factor)))
        sb = max(0, min(255, int(b * factor)))

        success = self.driver.set_solid_color(sr, sg, sb)
        if success:
            self._current_mode = "solid"
        return success

    def set_custom_effect(self, effect_id: str, speed: float = 1.0) -> bool:
        """Activates a custom software light pattern or audio visualizer and persists it."""
        if self.engine.is_running:
            self.engine.stop()

        if not self.driver.is_connected:
            if not self.driver.connect():
                return False

        self.effects.set_speed(speed)
        success = self.effects.start(effect_id)
        if success:
            self._current_mode = "effect"
            self.config_mgr.update({
                "last_effect_id": effect_id,
                "effect_speed": speed,
                "last_mode": "effect"
            })
        return success

    def set_effect_speed(self, speed: float) -> bool:
        """Adjusts the animation speed of the running effect."""
        self.effects.set_speed(speed)
        self.config_mgr.set("effect_speed", speed)
        return True

    def set_audio_sensitivity(self, sens: float) -> bool:
        """Adjusts the audio reactivity sensitivity."""
        self.effects.set_audio_sensitivity(sens)
        self.config_mgr.set("audio_sensitivity", sens)
        return True

    def set_brightness(self, level: int) -> bool:
        """Adjusts global brightness (0-100%) and persists."""
        self._current_brightness = max(0, min(100, int(level)))
        self.engine.update_config({"brightness": self._current_brightness})
        self.effects.set_brightness(self._current_brightness)
        self.config_mgr.set("brightness", self._current_brightness)

        # If solid color mode is active, update the hardware solid color with the scaled RGB
        if self._current_mode == "solid":
            r, g, b = self._last_solid
            factor = self._current_brightness / 100.0
            sr = max(0, min(255, int(r * factor)))
            sg = max(0, min(255, int(g * factor)))
            sb = max(0, min(255, int(b * factor)))
            if self.driver.is_connected:
                self.driver.set_solid_color(sr, sg, sb)

        return True

    def turn_off(self) -> bool:
        """Turns off the LEDs."""
        if self.engine.is_running:
            self.engine.stop()
        if self.effects.is_running:
            self.effects.stop()

        if self.driver.is_connected:
            self.driver.turn_off()

        self._current_mode = "off"
        self.config_mgr.set("last_mode", "off")
        return True

    def update_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Updates ambilight parameters and writes to disk."""
        self.engine.update_config(new_config)
        self.config_mgr.update(new_config)
        return {"success": True, "config": self.engine.config}

    def set_orientation(self, start_side: str, reverse_order: bool, zone_offset: int) -> Dict[str, Any]:
        """Calibrates the 3-module physical LED strip mapping and saves."""
        self.engine.set_orientation(
            start_side=start_side,
            reverse=bool(reverse_order),
            offset=int(zone_offset)
        )
        self.config_mgr.update({
            "start_side": start_side,
            "reverse_order": bool(reverse_order),
            "zone_offset": int(zone_offset)
        })
        return {"success": True, "config": self.engine.config}

    def get_stats(self) -> Dict[str, Any]:
        """Returns live FPS, running state, and current LED colors for UI preview."""
        if self._current_mode == "effect" and self.effects.is_running:
            stats = self.effects.get_stats()
            stats["running"] = False
            stats["is_ambilight_running"] = False
            stats["frames_processed"] = "-"
        elif self._current_mode == "solid":
            r, g, b = self._last_solid
            factor = self._current_brightness / 100.0
            sr = max(0, min(255, int(r * factor)))
            sg = max(0, min(255, int(g * factor)))
            sb = max(0, min(255, int(b * factor)))
            stats = {
                "running": False,
                "is_ambilight_running": False,
                "paused": False,
                "fps": 0.0,
                "target_fps": 0,
                "frames_processed": "-",
                "start_side": self.engine.config.get("start_side", "left"),
                "reverse_order": self.engine.config.get("reverse_order", False),
                "zone_offset": self.engine.config.get("zone_offset", 0),
                "led_preview": [[sr, sg, sb]] * 34
            }
        else:
            stats = self.engine.get_stats()
            stats["is_ambilight_running"] = self.engine.is_running and self._current_mode == "ambilight"
            stats["running"] = stats["is_ambilight_running"]

        stats["current_mode"] = self._current_mode
        stats["connected"] = self.driver.is_connected
        stats["brightness"] = self._current_brightness
        return stats

    def shutdown(self) -> None:
        """Clean shutdown when closing the application window."""
        self.turn_off()
        if self.capture.is_active:
            self.capture.stop()
        self.driver.disconnect()
