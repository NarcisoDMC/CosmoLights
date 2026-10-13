# -*- mode: python ; coding: utf-8 -*-
r"""
CosmoLights.spec - Configuración de PyInstaller (modo onedir, ideal para instalador).

Construir con:
    .venv\Scripts\python.exe -m PyInstaller CosmoLights.spec --noconfirm --clean

NOTA IMPORTANTE:
  No usar collect_all() / collect_submodules() sobre paquetes grandes (comtypes,
  webview, PIL, pythonnet, winrt...). Esas funciones IMPORTAN cada submódulo en
  subprocesos durante el build (incluidos tests de comtypes, backends Qt/GTK/
  Cocoa de pywebview, el runtime .NET, etc.), lo que deja el build colgado y
  satura el sistema. Aquí se declara solo lo que la app usa de verdad.
"""
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

# El hook de pyusb (hook-usb.py) llama a usb.core.find() durante el build,
# enumerando TODOS los dispositivos USB del equipo. No lo necesitamos porque
# libusb-1.0.dll viene de libusb_package.
os.environ["PYINSTALLER_USB_HOOK_SKIP_PYUSB_DISCOVERY"] = "1"

ROOT = Path(SPECPATH).resolve()
ICON = str(ROOT / "src" / "ui" / "assets" / "CosmoLightLogoIcon.ico")
DIST_HTML = ROOT / "src" / "ui" / "dist" / "index.html"

if not DIST_HTML.exists():
    raise SystemExit(
        "[CosmoLights.spec] Falta src/ui/dist/index.html. Ejecuta 'npm run build' antes de empaquetar."
    )

# ---------------------------------------------------------------------------
# Datos y binarios
# ---------------------------------------------------------------------------
datas = [
    (str(ROOT / "src" / "ui" / "dist"), "src/ui/dist"),
    (str(ROOT / "src" / "ui" / "assets"), "src/ui/assets"),
]
# pywebview: DLLs de WebView2 / WinForms (webview/lib/*)
datas += collect_data_files("webview", subdir="lib")
# soundcard: cabeceras cffi (*.py.h) que lee en tiempo de ejecución
datas += collect_data_files("soundcard")

binaries = []
# libusb-1.0.dll: dentro de su paquete (para importlib_resources) y en la raíz
binaries += collect_dynamic_libs("libusb_package")
binaries += collect_dynamic_libs("libusb_package", destdir=".")

# ---------------------------------------------------------------------------
# Imports dinámicos que PyInstaller no puede detectar por análisis estático
# ---------------------------------------------------------------------------
hiddenimports = [
    # pywebview: solo el backend de Windows (EdgeChromium / WinForms)
    "webview.platforms.edgechromium",
    "webview.platforms.winforms",
    "clr",
    "clr_loader",
    # pystray: solo backend Win32
    "pystray._win32",
    # soundcard: backend WASAPI
    "soundcard.mediafoundation",
    # dxcam importa winrt con importlib.import_module()
    "dxcam.core.winrt_duplicator",
    "dxcam.core.dxgi_duplicator",
    "dxcam.processor.numpy_processor",
    "dxcam.processor._numpy_kernels",
    "winrt.system",
    "winrt.windows.foundation",
    "winrt.windows.foundation.collections",
    "winrt.windows.graphics",
    "winrt.windows.graphics.capture",
    "winrt.windows.graphics.capture.interop",
    "winrt.windows.graphics.directx",
    "winrt.windows.graphics.directx.direct3d11",
    "winrt.windows.graphics.directx.direct3d11.interop",
    # pyusb / libusb
    "usb.backend.libusb1",
    "libusb_package",
    "importlib_resources",
]

# ---------------------------------------------------------------------------
# Exclusiones: backends y librerías que NO se usan en Windows
# ---------------------------------------------------------------------------
excludes = [
    "tkinter", "_tkinter", "unittest", "test", "pydoc_data",
    # pywebview en otras plataformas
    "webview.platforms.qt", "webview.platforms.gtk", "webview.platforms.cocoa",
    "webview.platforms.android", "webview.platforms.cef",
    "PyQt5", "PyQt6", "PySide2", "PySide6", "qtpy", "gi", "cefpython3", "jnius",
    # pystray en otras plataformas
    "pystray._xorg", "pystray._gtk", "pystray._appindicator", "pystray._darwin",
    "Xlib", "AppKit", "Foundation", "objc",
    # soundcard en otras plataformas
    "soundcard.pulseaudio", "soundcard.coreaudio",
    # comtypes: tests y herramientas que no hacen falta
    "comtypes.test", "comtypes.tools.codegenerator",
    # extras pesados opcionales
    "cv2", "matplotlib", "IPython", "pytest",
    "PIL.ImageTk", "PIL.ImageQt",
]

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CosmoLights",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # Sin ventana de consola
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,
    version=str(ROOT / "packaging" / "version_info.txt"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="CosmoLights",
)
