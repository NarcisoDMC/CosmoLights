"""
Capture package for CosmoLights.
Provides platform-independent screen capture through factory functions.
"""

import sys
from .base import BaseCapture

def get_screen_capture(monitor_idx: int = 0) -> BaseCapture:
    """
    Factory function returning the optimal capture provider for the host OS.
    - Windows: Uses DirectX 11 (dxcam / DXGI Desktop Duplication).
    - Linux: Can be extended with PipeWire / X11 SHM.
    """
    if sys.platform == "win32":
        from .windows_dxgi import WindowsDXGICapture
        return WindowsDXGICapture(output_idx=monitor_idx)
    elif sys.platform.startswith("linux"):
        raise NotImplementedError("Linux capture provider (PipeWire/X11) will be integrated in Phase 2.")
    else:
        raise OSError(f"Unsupported operating system: {sys.platform}")

__all__ = ["BaseCapture", "get_screen_capture"]
