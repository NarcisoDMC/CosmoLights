# CosmoLights ✨

Software ligero e independiente de control y sincronización **Ambilight** en tiempo real para tiras LED basadas en el controlador QinHeng Electronics (**VID: `0x1A86`**, **PID: `0xFE07`**).

Desarrollado como reemplazo nativo, seguro y de alto rendimiento del software chino bloqueado `DX Light.exe`.

---

## 🚀 Características Principales

- **Captura GPU Zero-Copy de Ultra Baja Latencia (<16 ms):**
  - Utiliza la API nativa **Windows Graphics Capture (WinRT)** a 60 FPS sin bordes amarillos en pantalla ni artefactos de cursor.
- **Protocolo Hardware Inverso Preciso (Sistema Modular de 3 Tiras):**
  - Envío directo por interrupciones USB (`Endpoint 0x01`, paquetes de 64 bytes).
  - Diseñado para la disposición física modular de 3 tiras (**17 LEDs Izquierda** + **29 LEDs Superior** + **17 LEDs Derecha** = **63 LEDs totales**).
  - Mapeo exacto de las **34 zonas perimetrales** del chip QinHeng (9 zonas a la izquierda, 16 zonas arriba, 9 zonas a la derecha).
- **Motor Ambilight Inteligente:**
  - Muestreo perimetral en forma de "U" invertida con saltos vectorizados en NumPy (**<0.5 ms de CPU por cuadro**).
  - Suavizado temporal exponencial (**EMA / LERP**) para transiciones suaves tipo cine o instantáneas para gaming.
  - Realce de saturación y corte de negros (las luces se apagan si los bordes de la pantalla están en negro).
- **Calibración y Orientación Completa:**
  - Ajuste de lado de inicio (Inferior Izquierda vs Inferior Derecha).
  - Inversión de secuencia (modo espejo izquierda a derecha).
  - Desplazamiento fino zona por zona (offset).
- **Efectos Algorítmicos y Visualizador de Audio en Tiempo Real:**
  - **Gradiente en Giro:** Rotación continua de espectro cromático fluido a 40 FPS.
  - **Barra Móvil Cromática:** Cometa/barra de luz que viaja por las 3 tiras, muta de color y deja estela.
  - **Aurora Cósmica:** Ondas bioluminiscentes orgánicas de cian, esmeralda y violeta.
  - **Espectro Convergente:** Ondas de audio bilaterales que suben por los laterales, colisionan en el centro superior y cambian de color en los picos/beats de sonido.
  - **Pulso de Graves & Ecualizador 3 Bandas:** Reacción directa a la música/juegos capturada por WASAPI loopback sin latencia.
- **Interfaz Moderna con React 19 + Tailwind CSS + WebView2:**
  - Desarrollada con **React 19**, **Tailwind CSS v4**, **Vite** y **Lucide Icons**, compilada en un bundle ultraligero y autónomo cargado por Microsoft Edge WebView2 (`pywebview`).
  - Monitor virtual en tiempo real con 34 nodos LED que reflejan la luz física emitida.
  - Modos adicionales de **Color Fijo** (paleta rápida y color picker libre) y **Efectos**.

---

## 🛠️ Estructura del Proyecto

```
CosmoLights/
├── main.py                     # Punto de entrada de la aplicación
├── run_cosmolights.bat         # Lanzador directo de Windows con 1 clic
├── vite.config.js              # Configuración de compilación Vite
├── package.json                # Dependencias React 19 y Lucide Icons
├── src/
│   ├── driver/
│   │   └── led_driver.py       # Controlador USB (PyUSB / libusb)
│   ├── capture/
│   │   ├── base.py             # Interfaz agnóstica de captura
│   │   └── windows_dxgi.py     # Captura GPU WinRT / DirectX
│   ├── engine/
│   │   └── ambilight.py        # Motor de procesamiento, zonas y EMA
│   └── ui/
│       ├── api.py              # API Bridge entre Python y JavaScript
│       ├── react_src/          # Código fuente React (App.jsx, componentes)
│       └── dist/               # Bundle optimizado autogenerado (index.html)
└── .venv/                      # Entorno virtual de Python
```

---

## 💻 Cómo Ejecutar

### Opción 1: Con 1 clic
Haz doble clic sobre el archivo:
```text
run_cosmolights.bat
```

### Opción 2: Desde la terminal
```powershell
.\.venv\Scripts\python.exe main.py
```
