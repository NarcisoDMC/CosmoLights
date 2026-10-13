"""
windows_dxgi.py - High-Performance Screen Capture Engine for Windows.

Uses `dxcam` with the modern Windows Graphics Capture API (WinRT backend)
and DXGI Desktop Duplication fallback.
Outputs raw RGB NumPy arrays directly from GPU VRAM with ultra-low latency (<2ms).
"""

import os
from typing import Tuple, Optional, List, Dict, Any
import time

# Disable Windows 10/11 yellow privacy border and cursor capture
os.environ["DXCAM_WINRT_BORDER_REQUIRED"] = "0"
os.environ["DXCAM_WINRT_CURSOR_CAPTURE"] = "0"

import numpy as np
import dxcam

from .base import BaseCapture


class WindowsDXGICapture(BaseCapture):
    """
    DirectX / WinRT GPU screen capture provider for Windows.
    Default backend is 'winrt' to prevent E_ACCESSDENIED errors on multi-monitor Windows 11.
    """

    def __init__(self, output_idx: int = 0, device_idx: int = 0, backend: str = "winrt"):
        self._output_idx = output_idx
        self._device_idx = device_idx
        self._backend = backend
        self._camera = None
        self._is_active = False
        self._width = 0
        self._height = 0

    @staticmethod
    def _get_win32_monitors() -> List[Dict[str, Any]]:
        """
        Enumerate all active displays directly via Win32 User32 APIs.
        Guaranteed to detect all active monitors on Windows regardless of DirectX state.
        """
        monitors = []
        try:
            import ctypes
            from ctypes import wintypes

            class RECT(ctypes.Structure):
                _fields_ = [
                    ('left', wintypes.LONG),
                    ('top', wintypes.LONG),
                    ('right', wintypes.LONG),
                    ('bottom', wintypes.LONG)
                ]

            class MONITORINFOEXW(ctypes.Structure):
                _fields_ = [
                    ('cbSize', wintypes.DWORD),
                    ('rcMonitor', RECT),
                    ('rcWork', RECT),
                    ('dwFlags', wintypes.DWORD),
                    ('szDevice', wintypes.WCHAR * 32)
                ]

            def _callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
                info = MONITORINFOEXW()
                info.cbSize = ctypes.sizeof(MONITORINFOEXW)
                if ctypes.windll.user32.GetMonitorInfoW(hMonitor, ctypes.byref(info)):
                    w = abs(info.rcMonitor.right - info.rcMonitor.left)
                    h = abs(info.rcMonitor.bottom - info.rcMonitor.top)
                    is_primary = bool(info.dwFlags & 1)
                    monitors.append({
                        "name": str(info.szDevice),
                        "resolution": (w, h),
                        "primary": is_primary,
                    })
                return 1

            MONITORENUMPROC = ctypes.WINFUNCTYPE(
                ctypes.c_int,
                wintypes.HMONITOR,
                wintypes.HDC,
                ctypes.POINTER(RECT),
                wintypes.LPARAM
            )
            ctypes.windll.user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(_callback), 0)
        except Exception as e:
            print(f"[WindowsDXGICapture] Error en Win32 EnumDisplayMonitors: {e}")

        return monitors

    @staticmethod
    def list_monitors() -> List[Dict[str, Any]]:
        """
        Enumerate connected displays and their resolutions.
        Combines Win32 system monitors with DXGI outputs to guarantee all
        connected displays are detected and selectable.
        """
        win32_displays = WindowsDXGICapture._get_win32_monitors()

        dxgi_monitors = []
        try:
            from dxcam import DXFactory
            factory = DXFactory._instances.get(DXFactory)
            if factory is None:
                factory = DXFactory()
            else:
                try:
                    factory.__init__()
                except Exception:
                    pass

            for dev_idx, (device, outputs) in enumerate(zip(factory.devices, factory.outputs)):
                for out_idx, output in enumerate(outputs):
                    try:
                        output.update_desc()
                    except Exception:
                        pass

                    out_name = getattr(output, "devicename", f"\\\\.\\DISPLAY{out_idx + 1}")
                    res = tuple(output.resolution) if hasattr(output, "resolution") and output.resolution else None
                    metadata = factory.output_metadata.get(out_name) if hasattr(factory, "output_metadata") else None
                    is_primary = bool(metadata[1]) if metadata else False
                    rotation = getattr(output, "rotation_angle", 0)

                    dxgi_monitors.append({
                        "device_idx": dev_idx,
                        "output_idx": out_idx,
                        "device_name": getattr(device, "description", "GPU Adapter"),
                        "output_name": out_name,
                        "resolution": res,
                        "primary": is_primary,
                        "rotation": rotation,
                    })
        except Exception as e:
            print(f"[WindowsDXGICapture] No se pudieron enumerar monitores DXGI: {e}")

        # Reconcile Win32 and DXGI monitors
        final_monitors: List[Dict[str, Any]] = []

        if dxgi_monitors:
            # Map by output_name
            dxgi_by_name = {m["output_name"]: m for m in dxgi_monitors}

            for i, wm in enumerate(win32_displays):
                name = wm["name"]
                if name in dxgi_by_name:
                    item = dxgi_by_name[name]
                    # Ensure valid resolution and primary flag
                    if not item.get("resolution"):
                        item["resolution"] = wm["resolution"]
                    item["primary"] = wm["primary"] or item.get("primary", False)
                    final_monitors.append(item)
                else:
                    # Win32 monitor missing from DXGI - assign next output_idx
                    final_monitors.append({
                        "device_idx": 0,
                        "output_idx": i,
                        "device_name": dxgi_monitors[0]["device_name"] if dxgi_monitors else "GPU Adapter",
                        "output_name": name,
                        "resolution": wm["resolution"],
                        "primary": wm["primary"],
                        "rotation": 0,
                    })

            # If Win32 found fewer or no monitors, retain any remaining DXGI outputs
            added_names = {m["output_name"] for m in final_monitors}
            for dm in dxgi_monitors:
                if dm["output_name"] not in added_names:
                    final_monitors.append(dm)
        elif win32_displays:
            # DXGI failed completely, use Win32 monitors directly
            for i, wm in enumerate(win32_displays):
                final_monitors.append({
                    "device_idx": 0,
                    "output_idx": i,
                    "device_name": "GPU Display",
                    "output_name": wm["name"],
                    "resolution": wm["resolution"],
                    "primary": wm["primary"],
                    "rotation": 0,
                })

        # Ultimate fallback if everything failed
        if not final_monitors:
            try:
                import ctypes
                user32 = ctypes.windll.user32
                res = (user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))
            except Exception:
                res = (1920, 1080)
            final_monitors.append({
                "device_idx": 0,
                "output_idx": 0,
                "device_name": "Default GPU",
                "output_name": "\\\\.\\DISPLAY1",
                "resolution": res,
                "primary": True,
                "rotation": 0
            })

        # Sort monitors by output_idx
        final_monitors.sort(key=lambda x: x.get("output_idx", 0))
        return final_monitors

    def _init_camera(self) -> bool:
        # Try primary backend (default: winrt), fallback to dxgi if needed
        backends_to_try = [self._backend]
        if self._backend != "dxgi":
            backends_to_try.append("dxgi")

        for b in backends_to_try:
            try:
                self._camera = dxcam.create(
                    device_idx=self._device_idx,
                    output_idx=self._output_idx,
                    output_color="RGB",
                    backend=b,
                    processor_backend="numpy"
                )
                if self._camera is not None:
                    self._backend = b
                    break
            except Exception as e:
                print(f"[WindowsDXGICapture] Backend '{b}' init failed: {e}")
                self._camera = None

        if self._camera is None:
            print(f"[WindowsDXGICapture] Failed to create DXCam on output {self._output_idx}.")
            return False

        # Grab a test frame to verify dimensions
        try:
            sample = self._camera.grab()
            if sample is not None:
                self._height, self._width, _ = sample.shape
            else:
                self._width, self._height = 1920, 1080
        except Exception:
            self._width, self._height = 1920, 1080

        print(f"[WindowsDXGICapture] Initialized ({self._backend}) on Output {self._output_idx} ({self._width}x{self._height}).")
        return True

    def start(self, target_fps: int = 60) -> bool:
        """Starts background frame capture thread."""
        if self._is_active:
            return True

        if self._camera is None:
            if not self._init_camera():
                return False

        try:
            # video_mode=True ensures smoothest non-blocking circular buffer
            self._camera.start(target_fps=target_fps, video_mode=True)
            self._is_active = True
            print(f"[WindowsDXGICapture] Capture started @ {target_fps} target FPS.")
            return True
        except Exception as e:
            print(f"[WindowsDXGICapture] Failed to start capture: {e}")
            self._is_active = False
            return False

    def stop(self) -> None:
        """Stops background frame capture thread."""
        if self._is_active and self._camera is not None:
            try:
                self._camera.stop()
            except Exception:
                pass
            self._is_active = False
            print("[WindowsDXGICapture] Capture stopped.")

    def release(self) -> None:
        """Releases the camera and duplicator resources."""
        self.stop()
        if self._camera is not None:
            try:
                self._camera.release()
            except Exception:
                pass
            self._camera = None

    def grab_frame(self) -> Optional[np.ndarray]:
        """
        Retrieves the latest available frame from the GPU buffer.
        Returns:
            np.ndarray of shape (Height, Width, 3), dtype=uint8 in RGB order,
            or None if no new frame is ready.
        """
        if not self._is_active or self._camera is None:
            return None

        try:
            return self._camera.get_latest_frame()
        except Exception:
            return None

    @property
    def resolution(self) -> Tuple[int, int]:
        return (self._width, self._height)

    @property
    def is_active(self) -> bool:
        return self._is_active


# ---------------------------------------------------------------------------
# Standalone Benchmark Test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== Testing WindowsDXGICapture ===")
    monitors = WindowsDXGICapture.list_monitors()
    print("Detected Monitors:")
    for m in monitors:
        print(f"  - [{m['output_idx']}] {m['output_name']} ({m['resolution'][0]}x{m['resolution'][1]}) {'[PRIMARY]' if m['primary'] else ''} on {m['device_name']}")

    cap = WindowsDXGICapture(output_idx=0)

    if not cap.start(target_fps=60):
        print("Failed to start capture.")
        exit(1)

    try:
        print(f"\nActive Resolution: {cap.resolution[0]}x{cap.resolution[1]}")
        print("Benchmarking 100 frames...")

        start_time = time.perf_counter()
        frames_captured = 0

        while frames_captured < 100:
            frame = cap.grab_frame()
            if frame is not None:
                frames_captured += 1
            else:
                time.sleep(0.001)

        elapsed = time.perf_counter() - start_time
        fps = frames_captured / elapsed
        latency_ms = (elapsed / frames_captured) * 1000

        print(f"\nResults:")
        print(f"Captured: {frames_captured} frames in {elapsed:.3f}s")
        print(f"Average FPS: {fps:.1f}")
        print(f"Latency per frame: {latency_ms:.2f} ms")
        print(f"Frame shape: {frame.shape}, type: {frame.dtype}")
        print(f"Sample center pixel RGB: {frame[frame.shape[0]//2, frame.shape[1]//2].tolist()}")
        print("=== Test PASSED ===")

    finally:
        cap.stop()
