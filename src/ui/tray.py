"""
tray.py - System Tray (Notification Area / Iconos Ocultos) Manager for CosmoLights.

Runs as a background daemon managing the taskbar tray icon, context menu,
and background Ambilight service state.
"""

from typing import Optional, Callable
from pathlib import Path
import threading
from PIL import Image
import pystray


class CosmoLightsTray:
    """Manages the Windows Notification Area tray icon and background controls."""

    def __init__(
        self,
        icon_path: Path,
        window,
        api,
        on_exit_callback: Optional[Callable[[], None]] = None,
    ):
        self.icon_path = icon_path
        self.window = window
        self.api = api
        self.on_exit_callback = on_exit_callback

        self._icon: Optional[pystray.Icon] = None
        self._is_visible = True

    def _get_icon_image(self) -> Image.Image:
        """Loads and prepares the icon image for the system tray."""
        try:
            if self.icon_path.exists():
                return Image.open(self.icon_path)
        except Exception as e:
            print(f"[Tray] Error cargando icono: {e}")

        # Fallback 32x32 glowing cyan square if file is missing
        return Image.new("RGBA", (32, 32), color=(0, 240, 255, 255))

    def _on_toggle_window(self, icon=None, item=None):
        """Shows and restores the main application window."""
        try:
            if self.window:
                self.window.show()
                self.window.restore()
        except Exception as e:
            print(f"[Tray] Error mostrando ventana: {e}")

    def _on_toggle_ambilight(self, icon=None, item=None):
        """Toggles Ambilight live synchronization from the tray."""
        try:
            is_active = self.api.engine.is_running
            self.api.toggle_ambilight(not is_active)
        except Exception as e:
            print(f"[Tray] Error alternando Ambilight: {e}")

    def _ambilight_menu_text(self, item) -> str:
        """Dynamic label reflecting current Ambilight state."""
        try:
            if self.api.engine.is_running:
                return "● Ambilight: Activo (Pausar)"
            elif self.api._current_mode == "effect":
                return "● Efecto en reproducción (Activar Ambilight)"
            return "○ Ambilight: Detenido (Iniciar)"
        except Exception:
            return "Ambilight"

    def _on_turn_off_lights(self, icon=None, item=None):
        """Turns off the LEDs."""
        try:
            self.api.turn_off()
        except Exception as e:
            print(f"[Tray] Error apagando luces: {e}")

    def _on_quit_app(self, icon=None, item=None):
        """Cleanly quits the application from the tray context menu."""
        print("[Tray] Cerrando CosmoLights desde el menú de la bandeja...")
        self.stop()
        if self.on_exit_callback:
            self.on_exit_callback()

    def start(self):
        """Starts the system tray icon in a dedicated background thread."""
        img = self._get_icon_image()

        menu = pystray.Menu(
            pystray.MenuItem("Abrir CosmoLights", self._on_toggle_window, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(self._ambilight_menu_text, self._on_toggle_ambilight),
            pystray.MenuItem("Apagar Luces", self._on_turn_off_lights),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Salir de CosmoLights", self._on_quit_app),
        )

        self._icon = pystray.Icon(
            "CosmoLights",
            img,
            "CosmoLights - Control Ambilight",
            menu,
        )

        # Run non-blocking
        self._icon.run_detached()
        print("[Tray] Icono de la bandeja del sistema iniciado.")

    def stop(self):
        """Removes the tray icon."""
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None
        print("[Tray] Icono de la bandeja detenido.")
