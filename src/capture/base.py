"""
base.py - Abstract base class for screen capture engines.
Allows switching between Windows (DXGI / DirectX 11) and Linux (X11 / PipeWire) seamlessly.
"""

from abc import ABC, abstractmethod
from typing import Tuple, Optional
import numpy as np


class BaseCapture(ABC):
    """Abstract interface for high-performance screen capture."""

    @abstractmethod
    def start(self, target_fps: int = 60) -> bool:
        """Starts the capture engine."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stops the capture engine and releases resources."""
        pass

    @abstractmethod
    def grab_frame(self) -> Optional[np.ndarray]:
        """
        Retrieves the latest captured frame as a NumPy array (Height, Width, 3) in RGB format.
        Returns None if no new frame is available or on error.
        """
        pass

    @property
    @abstractmethod
    def resolution(self) -> Tuple[int, int]:
        """Returns the monitor resolution as (width, height)."""
        pass

    @property
    @abstractmethod
    def is_active(self) -> bool:
        """Returns True if the capture engine is currently running."""
        pass

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
