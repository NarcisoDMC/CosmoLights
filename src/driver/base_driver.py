"""
base_driver.py - Abstract Base Class for LED Strip Hardware Drivers.

Defines the contract for all physical and simulated LED strip controllers
(QinHeng USB, Serial/COM Arduino/ESP32, Wi-Fi UDP WLED, Mock Drivers).
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any, Optional


class BaseLedDriver(ABC):
    """Abstract interface that all LED hardware drivers must implement."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Returns True if the physical hardware is currently connected and claimed."""
        pass

    @property
    @abstractmethod
    def driver_type(self) -> str:
        """Returns the driver identifier (e.g., 'qinheng', 'serial', 'udp', 'mock')."""
        pass

    @property
    @abstractmethod
    def device_info(self) -> Dict[str, Any]:
        """Returns metadata about the connected hardware device."""
        pass

    @abstractmethod
    def connect(self) -> bool:
        """Establishes connection to the hardware device."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Releases hardware resources and closes communication."""
        pass

    @abstractmethod
    def sync_screen_frame(self, colors: List[Tuple[int, int, int]]) -> bool:
        """
        Streams a real-time Ambilight frame to the LED strip.
        colors can be 34 zone tuples or N individual LED tuples.
        """
        pass

    @abstractmethod
    def set_solid_color(self, r: int, g: int, b: int) -> bool:
        """Sets a uniform static color on the entire LED strip."""
        pass

    @abstractmethod
    def turn_off(self) -> bool:
        """Turns off all LEDs on the strip."""
        pass
