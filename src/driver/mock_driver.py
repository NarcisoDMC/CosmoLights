"""
mock_driver.py - Simulated In-Memory Driver for Unit Testing and Virtual Preview.

Allows testing full streaming pipelines without physical hardware connected.
"""

from typing import List, Tuple, Dict, Any
from .base_driver import BaseLedDriver


class MockLedDriver(BaseLedDriver):
    """In-memory simulated driver that records sent frames and command packets."""

    def __init__(self, device_id: str = "mock_0", total_leds: int = 63):
        self.device_id = device_id
        self.total_leds = total_leds
        self._connected = False
        self.last_frame: List[Tuple[int, int, int]] = []
        self.last_solid_color: Tuple[int, int, int] = (0, 0, 0)
        self.frame_count = 0
        self.is_turned_off = True

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def driver_type(self) -> str:
        return "mock"

    @property
    def device_info(self) -> Dict[str, Any]:
        return {
            "type": "mock",
            "device_id": self.device_id,
            "total_leds": self.total_leds,
            "connected": self._connected,
        }

    def connect(self) -> bool:
        self._connected = True
        self.is_turned_off = False
        return True

    def disconnect(self) -> None:
        self._connected = False

    def sync_screen_frame(self, colors: List[Tuple[int, int, int]]) -> bool:
        if not self._connected:
            return False
        self.last_frame = list(colors)
        self.frame_count += 1
        self.is_turned_off = False
        return True

    def set_solid_color(self, r: int, g: int, b: int) -> bool:
        if not self._connected:
            return False
        self.last_solid_color = (r, g, b)
        self.last_frame = [(r, g, b)] * self.total_leds
        self.is_turned_off = False
        return True

    def turn_off(self) -> bool:
        if not self._connected:
            return False
        self.last_frame = [(0, 0, 0)] * self.total_leds
        self.is_turned_off = True
        return True
