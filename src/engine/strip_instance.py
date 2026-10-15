"""
strip_instance.py - Autonomous Controller Container for an Independent LED Strip.

Encapsulates hardware driver, screen capture binding, Ambilight engine,
custom effects, color calibration, and mode state for a single strip.
"""

from typing import Dict, Any, Optional, Tuple, List
import threading

from ..driver.base_driver import BaseLedDriver
from ..capture.base import BaseCapture
from .ambilight import AmbilightEngine
from .effects import CustomEffectsEngine


class StripInstance:
    """Manages state, calibration, and streaming engines for an individual LED strip."""

    DEFAULT_STRIP_CONFIG: Dict[str, Any] = {
        "start_side": "left",
        "reverse_order": False,
        "zone_offset": 0,
        "target_fps": 30,
        "smoothing": 0.40,
        "saturation_boost": 1.25,
        "brightness": 100,
        "border_depth": 0.08,
        "aspect_ratio": "auto",
        "black_cutoff": 15,
        "gamma": 2.0,
        "selected_monitor": 0,
        "num_left": 9,
        "num_top": 16,
        "num_right": 9,
    }

    def __init__(
        self,
        strip_id: str,
        name: str,
        driver: BaseLedDriver,
        capture: Optional[BaseCapture] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.strip_id = strip_id
        self.name = name
        self.driver = driver
        self._capture = capture
        self._lock = threading.Lock()

        # Initialize config
        self.config = dict(self.DEFAULT_STRIP_CONFIG)
        if config:
            self.config.update(config)

        self._current_mode = self.config.get("last_mode", "off")
        self._brightness = int(self.config.get("brightness", 100))
        solid_list = self.config.get("last_solid_rgb", [0, 240, 255])
        self._last_solid: Tuple[int, int, int] = tuple(solid_list) if len(solid_list) == 3 else (0, 240, 255)
        self._active_effect = self.config.get("last_effect_id", "rainbow_flow")
        self._effect_speed = float(self.config.get("effect_speed", 1.0))
        self._audio_sensitivity = float(self.config.get("audio_sensitivity", 1.2))

        # Autonomous engines
        self.engine = AmbilightEngine(self.driver, self._capture, config=self.config) if self._capture else None
        self.effects = CustomEffectsEngine(self.driver)
        self.effects.set_speed(self._effect_speed)
        self.effects.set_audio_sensitivity(self._audio_sensitivity)
        self.effects.set_brightness(self._brightness)

    @property
    def mode(self) -> str:
        return self._current_mode

    @property
    def brightness(self) -> int:
        return self._brightness

    @property
    def capture(self) -> Optional[BaseCapture]:
        return self._capture

    @capture.setter
    def capture(self, new_capture: BaseCapture) -> None:
        with self._lock:
            self._capture = new_capture
            if self.engine is not None:
                was_running = self.engine.is_running
                if was_running:
                    self.engine.stop()
                self.engine.capture = new_capture
                if was_running:
                    self.engine.start()
            else:
                self.engine = AmbilightEngine(self.driver, new_capture, config=self.config)

    def set_mode(self, mode: str) -> bool:
        """Transitions strip mode safely between ambilight, solid, effect, and off."""
        with self._lock:
            if mode == "ambilight":
                return self.start_ambilight()
            elif mode == "solid":
                r, g, b = self._last_solid
                return self.set_solid_color(r, g, b)
            elif mode == "effect":
                return self.set_effect(self._active_effect, self._effect_speed)
            elif mode == "off":
                return self.turn_off()
            return False

    def start_ambilight(self) -> bool:
        """Starts real-time Ambilight capture stream on this strip."""
        if self.effects.is_running:
            self.effects.stop()

        if self.engine is None or self._capture is None:
            print(f"[StripInstance:{self.strip_id}] No capture provider bound.")
            return False

        success = self.engine.start()
        if success:
            self._current_mode = "ambilight"
            self.config["last_mode"] = "ambilight"
        return success

    def stop_ambilight(self) -> None:
        """Stops Ambilight stream on this strip."""
        if self.engine and self.engine.is_running:
            self.engine.stop()
        self._current_mode = "off"
        self.config["last_mode"] = "off"

    def set_solid_color(self, r: int, g: int, b: int) -> bool:
        """Sets a uniform static color on this strip."""
        if self.engine and self.engine.is_running:
            self.engine.stop()
        if self.effects.is_running:
            self.effects.stop()

        self._last_solid = (r, g, b)
        self.config["last_solid_rgb"] = [r, g, b]
        self.config["last_mode"] = "solid"

        if not self.driver.is_connected:
            if not self.driver.connect():
                return False

        factor = self._brightness / 100.0
        sr = max(0, min(255, int(r * factor)))
        sg = max(0, min(255, int(g * factor)))
        sb = max(0, min(255, int(b * factor)))

        success = self.driver.set_solid_color(sr, sg, sb)
        if success:
            self._current_mode = "solid"
        return success

    def set_effect(self, effect_id: str, speed: Optional[float] = None) -> bool:
        """Activates a procedural or audio-reactive light pattern on this strip."""
        if self.engine and self.engine.is_running:
            self.engine.stop()

        if not self.driver.is_connected:
            if not self.driver.connect():
                return False

        if speed is not None:
            self._effect_speed = float(speed)
            self.effects.set_speed(self._effect_speed)
            self.config["effect_speed"] = self._effect_speed

        self._active_effect = effect_id
        self.config["last_effect_id"] = effect_id
        self.config["last_mode"] = "effect"

        success = self.effects.start(effect_id)
        if success:
            self._current_mode = "effect"
        return success

    def set_brightness(self, level: int) -> bool:
        """Updates brightness for this strip across running modes."""
        self._brightness = max(0, min(100, int(level)))
        self.config["brightness"] = self._brightness
        self.effects.set_brightness(self._brightness)
        if self.engine:
            self.engine.update_config({"brightness": self._brightness})

        if self._current_mode == "solid":
            r, g, b = self._last_solid
            factor = self._brightness / 100.0
            sr = max(0, min(255, int(r * factor)))
            sg = max(0, min(255, int(g * factor)))
            sb = max(0, min(255, int(b * factor)))
            if self.driver.is_connected:
                self.driver.set_solid_color(sr, sg, sb)

        return True

    def set_effect_speed(self, speed: float) -> bool:
        self._effect_speed = float(speed)
        self.effects.set_speed(self._effect_speed)
        self.config["effect_speed"] = self._effect_speed
        return True

    def set_audio_sensitivity(self, sens: float) -> bool:
        self._audio_sensitivity = float(sens)
        self.effects.set_audio_sensitivity(self._audio_sensitivity)
        self.config["audio_sensitivity"] = self._audio_sensitivity
        return True

    def turn_off(self) -> bool:
        """Turns off this strip's LEDs and stops streaming engines."""
        if self.engine and self.engine.is_running:
            self.engine.stop()
        if self.effects.is_running:
            self.effects.stop()

        if self.driver.is_connected:
            self.driver.turn_off()

        self._current_mode = "off"
        self.config["last_mode"] = "off"
        return True

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """Updates calibration and color settings for this strip."""
        with self._lock:
            self.config.update(new_config)
            if self.engine:
                self.engine.update_config(new_config)
            if "brightness" in new_config:
                self.set_brightness(new_config["brightness"])
            if "effect_speed" in new_config:
                self.set_effect_speed(new_config["effect_speed"])
            if "audio_sensitivity" in new_config:
                self.set_audio_sensitivity(new_config["audio_sensitivity"])

    def get_state(self) -> Dict[str, Any]:
        """Returns full runtime telemetry and configuration snapshot for this strip."""
        with self._lock:
            fps = 0.0
            frames = 0
            detected_aspect = "16:9"
            crop_pct = 0.0
            led_preview: List[List[int]] = []

            if self._current_mode == "ambilight" and self.engine and self.engine.is_running:
                stats = self.engine.get_stats()
                fps = stats["fps"]
                frames = stats["frames_processed"]
                detected_aspect = stats["detected_aspect"]
                crop_pct = stats["crop_top_pct"]
                led_preview = stats["led_preview"]
            elif self._current_mode == "effect" and self.effects.is_running:
                led_preview = self.effects.get_live_colors()
                fps = 40.0
            elif self._current_mode == "solid":
                factor = self._brightness / 100.0
                r, g, b = self._last_solid
                scaled = [int(r * factor), int(g * factor), int(b * factor)]
                led_preview = [scaled] * 34
            else:
                led_preview = [[0, 0, 0]] * 34

            return {
                "id": self.strip_id,
                "name": self.name,
                "driver": self.driver.device_info,
                "connected": self.driver.is_connected,
                "mode": self._current_mode,
                "brightness": self._brightness,
                "last_solid_rgb": list(self._last_solid),
                "active_effect": self._active_effect,
                "effect_speed": self._effect_speed,
                "audio_sensitivity": self._audio_sensitivity,
                "config": dict(self.config),
                "fps": fps,
                "frames_processed": frames,
                "detected_aspect": detected_aspect,
                "crop_top_pct": crop_pct,
                "led_preview": led_preview,
            }
