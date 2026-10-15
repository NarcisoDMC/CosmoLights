"""
orchestrator.py - Multi-Strip Orchestrator & Capture Stream Pool.

Coordinates multiple StripInstances, manages shared GPU capture streams across
monitors, provides master power controls, and aggregates telemetry.
"""

from typing import Dict, Any, List, Optional, Callable
import threading

from ..capture.base import BaseCapture
from .strip_instance import StripInstance


class CapturePool:
    """
    Manages shared screen capture instances by monitor index.
    Ensures multiple strips targeting the same display share a single GPU capture
    thread instead of creating duplicate capture duplicators.
    """

    def __init__(self, capture_factory: Optional[Callable[[int], BaseCapture]] = None):
        self._pool: Dict[int, BaseCapture] = {}
        self._ref_counts: Dict[int, int] = {}
        self._lock = threading.Lock()
        self._factory = capture_factory

    def _create_capture(self, output_idx: int) -> BaseCapture:
        if self._factory:
            return self._factory(output_idx)
        from ..capture.windows_dxgi import WindowsDXGICapture
        return WindowsDXGICapture(output_idx=output_idx)

    def acquire(self, output_idx: int) -> BaseCapture:
        """Acquires a capture engine for the specified monitor index."""
        with self._lock:
            if output_idx not in self._pool:
                self._pool[output_idx] = self._create_capture(output_idx)
                self._ref_counts[output_idx] = 0

            self._ref_counts[output_idx] += 1
            return self._pool[output_idx]

    def release(self, output_idx: int) -> None:
        """Decrements reference count and cleans up when no strips use this monitor."""
        with self._lock:
            if output_idx in self._ref_counts:
                self._ref_counts[output_idx] -= 1
                if self._ref_counts[output_idx] <= 0:
                    cap = self._pool.pop(output_idx, None)
                    self._ref_counts.pop(output_idx, None)
                    if cap:
                        if hasattr(cap, "release"):
                            cap.release()
                        elif cap.is_active:
                            cap.stop()

    def get_active_count(self) -> int:
        with self._lock:
            return len(self._pool)


class StripOrchestrator:
    """Central orchestrator managing all active and configured LED strips."""

    def __init__(self, capture_factory: Optional[Callable[[int], BaseCapture]] = None):
        self._strips: Dict[str, StripInstance] = {}
        self._active_strip_id: Optional[str] = None
        self._lock = threading.Lock()
        self.capture_pool = CapturePool(capture_factory=capture_factory)

    @property
    def active_strip_id(self) -> Optional[str]:
        return self._active_strip_id

    def add_strip(self, strip: StripInstance) -> str:
        """Registers a new LED strip instance."""
        with self._lock:
            self._strips[strip.strip_id] = strip
            if self._active_strip_id is None:
                self._active_strip_id = strip.strip_id

            # Bind shared capture if strip needs ambilight on a monitor
            mon_idx = int(strip.config.get("selected_monitor", 0))
            if strip.capture is None:
                strip.capture = self.capture_pool.acquire(mon_idx)

            return strip.strip_id

    def remove_strip(self, strip_id: str) -> bool:
        """Stops, turns off, and unregisters an LED strip."""
        with self._lock:
            strip = self._strips.pop(strip_id, None)
            if strip is None:
                return False

            strip.turn_off()
            mon_idx = int(strip.config.get("selected_monitor", 0))
            self.capture_pool.release(mon_idx)

            if self._active_strip_id == strip_id:
                self._active_strip_id = next(iter(self._strips.keys())) if self._strips else None

            return True

    def get_strip(self, strip_id: str) -> Optional[StripInstance]:
        """Retrieves a strip by its unique ID."""
        with self._lock:
            return self._strips.get(strip_id)

    def get_active_strip(self) -> Optional[StripInstance]:
        """Returns the currently focused strip in the UI."""
        with self._lock:
            if self._active_strip_id and self._active_strip_id in self._strips:
                return self._strips[self._active_strip_id]
            if self._strips:
                first_id = next(iter(self._strips.keys()))
                self._active_strip_id = first_id
                return self._strips[first_id]
            return None

    def set_active_strip(self, strip_id: str) -> bool:
        """Switches the UI focused strip."""
        with self._lock:
            if strip_id in self._strips:
                self._active_strip_id = strip_id
                return True
            return False

    def list_strips(self) -> List[Dict[str, Any]]:
        """Returns list of all configured strips with basic status."""
        with self._lock:
            result = []
            for s in self._strips.values():
                result.append({
                    "id": s.strip_id,
                    "name": s.name,
                    "driver_type": s.driver.driver_type,
                    "connected": s.driver.is_connected,
                    "mode": s.mode,
                    "brightness": s.brightness,
                    "is_active": (s.strip_id == self._active_strip_id),
                })
            return result

    def turn_off_all(self) -> None:
        """Master Power Off: Shuts off all configured LED strips."""
        with self._lock:
            for s in self._strips.values():
                s.turn_off()

    def set_master_brightness(self, level: int) -> None:
        """Sets brightness uniformly across all strips."""
        with self._lock:
            for s in self._strips.values():
                s.set_brightness(level)

    def get_all_states(self) -> Dict[str, Any]:
        """Returns aggregated telemetry and configuration for all strips."""
        with self._lock:
            states = {}
            for sid, s in self._strips.items():
                states[sid] = s.get_state()
            return {
                "active_strip_id": self._active_strip_id,
                "strips": states,
                "total_strips": len(self._strips),
            }
