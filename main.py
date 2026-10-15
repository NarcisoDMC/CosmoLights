"""
main.py - Entry point for CosmoLights Desktop Application.

Initializes the Python backend, hardware interfaces, starts the system tray service,
and launches the Microsoft Edge WebView2 GUI via pywebview.
"""

import os
import sys
from pathlib import Path

# Safe stdout / stderr for --noconsole mode
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

# Disable Windows 10/11 yellow capture privacy border and cursor capture
os.environ["DXCAM_WINRT_BORDER_REQUIRED"] = "0"
os.environ["DXCAM_WINRT_CURSOR_CAPTURE"] = "0"

# Determine project root (handling frozen PyInstaller bundle vs standard execution)
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    PROJECT_ROOT = Path(sys._MEIPASS)
else:
    PROJECT_ROOT = Path(__file__).resolve().parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Set explicit Windows AppUserModelID so taskbar groups properly with the app icon
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("cosmolights.ambilight.controller.1.0")
    except Exception:
        pass

import webview
from src.ui.api import CosmoLightsAPI
from src.ui.tray import CosmoLightsTray


def main():
    api = CosmoLightsAPI()
    html_path = PROJECT_ROOT / "src" / "ui" / "dist" / "index.html"

    # Search for icon in multiple potential locations
    icon_candidates = [
        PROJECT_ROOT / "src" / "ui" / "assets" / "CosmoLightLogoIcon.ico",
        PROJECT_ROOT / "src" / "ui" / "react_src" / "src" / "assets" / "CosmoLightLogoIcon.ico",
        PROJECT_ROOT / "assets" / "CosmoLightLogoIcon.ico",
        PROJECT_ROOT / "CosmoLightLogoIcon.ico",
    ]
    icon_path = next((p.resolve() for p in icon_candidates if p.exists()), None)
    if icon_path:
        print(f"[CosmoLights] Icono cargado: {icon_path}")
    else:
        print("[CosmoLights] Advertencia: No se encontró archivo .ico")

    if not html_path.exists():
        raise FileNotFoundError(
            f"No se encontró el bundle de la interfaz en '{html_path}'. "
            "Ejecuta 'npm run build' en la raíz del proyecto para compilar el frontend React."
        )

    # Flag indicating whether we are truly terminating or just minimizing/hiding
    is_quitting = False
    start_minimized = "--minimized" in sys.argv or "--tray" in sys.argv

    # Create the modern pywebview window
    window = webview.create_window(
        title="CosmoLights - Control Ambilight",
        url=str(html_path.resolve()),
        js_api=api,
        width=1000,
        height=740,
        min_size=(860, 620),
        resizable=True,
        background_color="#0b0d14",
        hidden=start_minimized,
    )

    # Define clean total exit routine (called only when selecting 'Salir' from tray)
    def quit_completely():
        nonlocal is_quitting
        print("[CosmoLights] Finalizando aplicación por completo...")
        is_quitting = True
        try:
            api.turn_off()
            api.shutdown()
        except Exception:
            pass
        try:
            window.destroy()
        except Exception:
            pass

    # Intercept 'X' close button: hide to tray so Ambilight keeps running as background service!
    def on_closing():
        nonlocal is_quitting
        if not is_quitting:
            print("[CosmoLights] Ocultando ventana a la bandeja del sistema (Ambilight sigue activo)...")
            window.hide()
            return False  # Cancels window destruction!
        return True

    window.events.closing += on_closing

    # Initialize System Tray
    tray = CosmoLightsTray(
        icon_path=icon_path if icon_path else (PROJECT_ROOT / "CosmoLightLogoIcon.ico"),
        window=window,
        api=api,
        on_exit_callback=quit_completely,
    )

    # Startup worker: starts tray and automatically launches Ambilight background service
    def on_started(win):
        tray.start()
        # Automatically start Ambilight background synchronization
        try:
            print("[CosmoLights] Iniciando sincronización Ambilight en segundo plano...")
            api.toggle_ambilight(True)
        except Exception as e:
            print(f"[CosmoLights] Error iniciando Ambilight automático: {e}")

    # Set icon argument for webview if available
    start_kwargs = {
        "debug": True,
    }
    if icon_path:
        start_kwargs["icon"] = str(icon_path)

    # Launch GUI loop
    try:
        webview.start(on_started, window, gui="edgechromium", **start_kwargs)
    except Exception as e:
        print(f"[CosmoLights] Fallback launching standard webview: {e}")
        webview.start(on_started, window, **start_kwargs)


if __name__ == "__main__":
    main()
