"""
api.py - Python-to-JavaScript Bridge API for CosmoLights.

Exposed directly to the Web UI via pywebview (window.pywebview.api).
Coordinates multi-strip orchestration, screen capture pool, procedural lighting,
audio visualizers, calibration, and live telemetry across all connected hardware.
Includes persistent storage in %APPDATA%/CosmoLights/config.json without simulated data.
"""

from typing import Dict, Any, List, Optional
import os

from ..driver.base_driver import BaseLedDriver
from ..driver.led_driver import LedDriver
from ..driver.serial_driver import SerialLedDriver
from ..capture.windows_dxgi import WindowsDXGICapture
from ..engine.strip_instance import StripInstance
from ..engine.orchestrator import StripOrchestrator
from ..engine.effects import CustomEffectsEngine
from ..engine.config_manager import ConfigManager


class CosmoLightsAPI:
    """Bridge API exposed to the JavaScript frontend."""

    def __init__(self):
        self.config_mgr = ConfigManager.get_instance()
        saved = self.config_mgr.get_all()

        monitors = WindowsDXGICapture.list_monitors()
        valid_mon_indices = [m["output_idx"] for m in monitors]
        default_mon = valid_mon_indices[0] if valid_mon_indices else 0

        self.orchestrator = StripOrchestrator()

        # Load real strips from persistent config or initialize the primary physical strip
        saved_strips = saved.get("strips")
        if saved_strips and isinstance(saved_strips, list) and len(saved_strips) > 0:
            for s_data in saved_strips:
                s_id = s_data.get("id", "strip_1")
                name = s_data.get("name", "Tira LED Principal")
                dev_type = s_data.get("device_type", "qinheng")
                dev_idx = int(s_data.get("device_index", 0))
                port = s_data.get("port", "COM3")
                total_leds = int(s_data.get("total_leds", 63))
                s_cfg = dict(s_data.get("config", {}))

                # Ensure monitor index is valid
                if s_cfg.get("selected_monitor") not in valid_mon_indices and valid_mon_indices:
                    s_cfg["selected_monitor"] = default_mon

                driver: BaseLedDriver
                if dev_type == "serial":
                    driver = SerialLedDriver(port=port, total_leds=total_leds)
                else:
                    driver = LedDriver(device_index=dev_idx, total_leds=total_leds)

                instance = StripInstance(
                    strip_id=s_id,
                    name=name,
                    driver=driver,
                    config=s_cfg
                )
                self.orchestrator.add_strip(instance)
        else:
            # First run or empty config: Initialize exactly ONE real strip for the primary hardware
            base_cfg = dict(saved)
            if base_cfg.get("selected_monitor") not in valid_mon_indices and valid_mon_indices:
                base_cfg["selected_monitor"] = default_mon

            primary_driver = LedDriver(device_index=0, total_leds=63)
            primary_strip = StripInstance(
                strip_id="strip_1",
                name="Tira LED Principal",
                driver=primary_driver,
                config=base_cfg
            )
            self.orchestrator.add_strip(primary_strip)

        active_id = saved.get("active_strip_id", "strip_1")
        self.orchestrator.set_active_strip(active_id)

        # Connect active strip hardware
        active = self.orchestrator.get_active_strip()
        if active and not active.driver.is_connected:
            active.driver.connect()

        self._save_strips_state()

    def _save_strips_state(self) -> None:
        """Saves current real strip configurations to config.json."""
        strips_data = []
        for s in self.orchestrator._strips.values():
            dev_idx = getattr(s.driver, "device_index", 0)
            port = getattr(s.driver, "port", "COM3")
            strips_data.append({
                "id": s.strip_id,
                "name": s.name,
                "device_type": s.driver.driver_type,
                "device_index": dev_idx,
                "port": port,
                "total_leds": getattr(s.driver, "total_leds", 63),
                "config": s.config,
            })
        self.config_mgr.set("strips", strips_data)
        self.config_mgr.set("active_strip_id", self.orchestrator.active_strip_id)

    @property
    def active_strip(self) -> Optional[StripInstance]:
        return self.orchestrator.get_active_strip()

    # -------------------------------------------------------------------------
    # Core API Endpoints
    # -------------------------------------------------------------------------

    def initialize(self) -> Dict[str, Any]:
        """Initial connection, hardware check and settings restoration."""
        monitors = WindowsDXGICapture.list_monitors()
        active = self.active_strip
        if active and not active.driver.is_connected:
            active.driver.connect()

        connected = active.driver.is_connected if active else False
        cfg = dict(active.config) if active else {}
        cfg["brightness"] = active.brightness if active else 100

        strips_list = self.orchestrator.list_strips()

        return {
            "connected": connected,
            "monitors": monitors,
            "strips": strips_list,
            "active_strip_id": self.orchestrator.active_strip_id,
            "selected_monitor": cfg.get("selected_monitor", 0),
            "current_mode": active.mode if active else "off",
            "config": cfg,
            "brightness": active.brightness if active else 100,
            "last_solid_rgb": list(active._last_solid) if active else [0, 240, 255],
            "last_effect_id": active._active_effect if active else "rainbow_flow",
            "effect_speed": active._effect_speed if active else 1.0,
            "audio_sensitivity": active._audio_sensitivity if active else 1.2,
            "effects_list": CustomEffectsEngine.EFFECTS_LIST,
        }

    def list_monitors(self) -> List[Dict[str, Any]]:
        """Returns detected monitors with fresh system scan."""
        return WindowsDXGICapture.list_monitors()

    # -------------------------------------------------------------------------
    # Multi-Strip Management
    # -------------------------------------------------------------------------

    def list_strips(self) -> List[Dict[str, Any]]:
        """Returns list of currently configured real strips."""
        return self.orchestrator.list_strips()

    def set_active_strip(self, strip_id: str) -> Dict[str, Any]:
        """Switches the UI focused strip and updates connection."""
        self.orchestrator.set_active_strip(strip_id)
        self.config_mgr.set("active_strip_id", strip_id)
        active = self.active_strip
        if active and not active.driver.is_connected:
            active.driver.connect()

        return {
            "success": True,
            "active_strip_id": self.orchestrator.active_strip_id,
            "state": active.get_state() if active else None,
        }

    def enumerate_hardware(self) -> Dict[str, Any]:
        """Discovers real physical controllers connected to USB and Serial ports."""
        qinheng_devices = LedDriver.enumerate_devices()
        serial_ports = SerialLedDriver.list_ports()
        return {
            "qinheng": qinheng_devices,
            "serial": serial_ports,
        }

    def add_strip(
        self,
        name: str,
        device_type: str = "qinheng",
        device_index: int = 0,
        port: str = "COM3",
        total_leds: int = 63,
        selected_monitor: int = 0,
    ) -> Dict[str, Any]:
        """Adds a newly detected real physical LED strip."""
        strip_count = len(self.orchestrator._strips) + 1
        new_id = f"strip_{strip_count}"

        driver: BaseLedDriver
        if device_type == "serial":
            driver = SerialLedDriver(port=port, total_leds=int(total_leds))
        else:
            driver = LedDriver(device_index=int(device_index), total_leds=int(total_leds))

        new_strip = StripInstance(
            strip_id=new_id,
            name=name.strip() or f"Tira LED {strip_count}",
            driver=driver,
            config={
                "selected_monitor": int(selected_monitor),
                "brightness": 100,
                "black_cutoff": 15,
                "gamma": 2.0,
                "saturation_boost": 1.25,
                "smoothing": 0.40,
                "target_fps": 30,
                "aspect_ratio": "auto",
            }
        )

        self.orchestrator.add_strip(new_strip)
        new_strip.driver.connect()
        self._save_strips_state()

        return {
            "success": True,
            "strip": new_strip.get_state(),
            "strips": self.orchestrator.list_strips(),
        }

    def remove_strip(self, strip_id: str) -> Dict[str, Any]:
        """Removes a secondary strip."""
        if len(self.orchestrator._strips) <= 1:
            return {"success": False, "error": "No se puede eliminar la tira principal."}

        success = self.orchestrator.remove_strip(strip_id)
        if success:
            self._save_strips_state()

        return {
            "success": success,
            "strips": self.orchestrator.list_strips(),
            "active_strip_id": self.orchestrator.active_strip_id,
        }

    def rename_strip(self, strip_id: str, new_name: str) -> Dict[str, Any]:
        """Renames a strip."""
        strip = self.orchestrator.get_strip(strip_id)
        if strip:
            strip.name = new_name.strip()
            self._save_strips_state()
            return {"success": True, "name": strip.name}
        return {"success": False}

    def turn_off_all(self) -> bool:
        """Master Power Off: Shuts off all configured LED strips."""
        self.orchestrator.turn_off_all()
        self._save_strips_state()
        return True

    def set_master_brightness(self, level: int) -> bool:
        """Sets brightness across all strips simultaneously."""
        self.orchestrator.set_master_brightness(level)
        self._save_strips_state()
        return True

    # -------------------------------------------------------------------------
    # Active Strip Delegated Controls (Backward Compatible)
    # -------------------------------------------------------------------------

    def set_monitor(self, output_idx: int) -> bool:
        """Switches capture monitor for the active strip."""
        active = self.active_strip
        if not active:
            return False

        output_idx = int(output_idx)
        active.config["selected_monitor"] = output_idx

        # Re-bind capture from pool
        new_capture = self.orchestrator.capture_pool.acquire(output_idx)
        active.capture = new_capture

        self._save_strips_state()
        return True

    def toggle_ambilight(self, enable: bool) -> Dict[str, Any]:
        """Starts or stops live Ambilight screen capture on the active strip."""
        active = self.active_strip
        if not active:
            return {"success": False, "mode": "off"}

        if enable:
            success = active.start_ambilight()
        else:
            active.stop_ambilight()
            success = True

        self._save_strips_state()
        return {"success": success, "mode": active.mode}

    def set_solid_color(self, r: int, g: int, b: int) -> bool:
        """Sets a uniform static color on the active strip."""
        active = self.active_strip
        if not active:
            return False

        success = active.set_solid_color(r, g, b)
        if success:
            self._save_strips_state()
        return success

    def set_custom_effect(self, effect_id: str, speed: float = 1.0) -> bool:
        """Activates a lighting effect on the active strip."""
        active = self.active_strip
        if not active:
            return False

        success = active.set_effect(effect_id, speed)
        if success:
            self._save_strips_state()
        return success

    def set_effect_speed(self, speed: float) -> bool:
        active = self.active_strip
        if not active:
            return False
        res = active.set_effect_speed(speed)
        self._save_strips_state()
        return res

    def set_audio_sensitivity(self, sens: float) -> bool:
        active = self.active_strip
        if not active:
            return False
        res = active.set_audio_sensitivity(sens)
        self._save_strips_state()
        return res

    def set_brightness(self, level: int) -> bool:
        """Adjusts brightness on the active strip."""
        active = self.active_strip
        if not active:
            return False
        res = active.set_brightness(level)
        self._save_strips_state()
        return res

    def turn_off(self) -> bool:
        """Turns off the active strip."""
        active = self.active_strip
        if not active:
            return False
        res = active.turn_off()
        self._save_strips_state()
        return res

    def update_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Updates parameters for the active strip."""
        active = self.active_strip
        if not active:
            return {"success": False, "config": {}}
        active.update_config(new_config)
        self._save_strips_state()
        return {"success": True, "config": active.config}

    def set_orientation(self, start_side: str, reverse_order: bool, zone_offset: int) -> Dict[str, Any]:
        """Calibrates physical strip mapping for the active strip."""
        return self.update_config({
            "start_side": start_side,
            "reverse_order": bool(reverse_order),
            "zone_offset": int(zone_offset)
        })

    def get_stats(self) -> Dict[str, Any]:
        """Returns live FPS, running state, and current LED preview for the active strip."""
        active = self.active_strip
        if not active:
            return {
                "running": False,
                "is_ambilight_running": False,
                "current_mode": "off",
                "connected": False,
                "brightness": 100,
                "fps": 0.0,
                "target_fps": 30,
                "frames_processed": "-",
                "start_side": "left",
                "reverse_order": False,
                "zone_offset": 0,
                "led_preview": [[0, 0, 0]] * 34,
                "strips": self.orchestrator.list_strips(),
                "active_strip_id": None,
            }

        state = active.get_state()
        is_ambi = (state["mode"] == "ambilight")
        stats = {
            "running": is_ambi,
            "is_ambilight_running": is_ambi,
            "paused": False,
            "fps": state["fps"],
            "target_fps": active.config.get("target_fps", 30),
            "frames_processed": state["frames_processed"],
            "start_side": active.config.get("start_side", "left"),
            "reverse_order": active.config.get("reverse_order", False),
            "zone_offset": active.config.get("zone_offset", 0),
            "detected_aspect": state["detected_aspect"],
            "crop_top_pct": state["crop_top_pct"],
            "led_preview": state["led_preview"],
            "current_mode": state["mode"],
            "connected": state["connected"],
            "brightness": state["brightness"],
            "strips": self.orchestrator.list_strips(),
            "active_strip_id": self.orchestrator.active_strip_id,
        }
        return stats

    def shutdown(self) -> None:
        """Clean shutdown when closing the application window."""
        self.orchestrator.turn_off_all()
        for s in self.orchestrator._strips.values():
            s.driver.disconnect()
