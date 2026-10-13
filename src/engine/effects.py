"""
effects.py - Dynamic Custom Software Effects & Audio Visualizer Engine.

Streams generated light patterns directly to the 3-strip modular LED setup (34 zones / 63 LEDs).
Features:
  - Rotating multi-color chromatic gradients & cyber waves.
  - Color-morphing meteor / traveling light bars with trails.
  - Bioluminescent Aurora, Fireplace, Plasma & Starlight sparks.
  - Cyberpunk breathing, Police strobe, Matrix digital rain.
  - Multi-band reactive audio visualizers (bilateral convergence, bass pulse, EQ & ripple).
"""

from typing import List, Tuple, Dict, Any, Optional
import threading
import time
import math
import random
import numpy as np

from ..driver.led_driver import LedDriver
from .audio_capture import AudioCaptureListener


def hsv_to_rgb(h: float, s: float = 1.0, v: float = 1.0) -> Tuple[int, int, int]:
    """Converts HSV (h in 0-360, s in 0-1, v in 0-1) to RGB (0-255)."""
    h = h % 360.0
    c = v * s
    x = c * (1.0 - abs((h / 60.0) % 2.0 - 1.0))
    m = v - c

    if 0.0 <= h < 60.0:
        r, g, b = c, x, 0.0
    elif 60.0 <= h < 120.0:
        r, g, b = x, c, 0.0
    elif 120.0 <= h < 180.0:
        r, g, b = 0.0, c, x
    elif 180.0 <= h < 240.0:
        r, g, b = 0.0, x, c
    elif 240.0 <= h < 300.0:
        r, g, b = x, 0.0, c
    else:
        r, g, b = c, 0.0, x

    return (
        int(np.clip((r + m) * 255.0, 0, 255)),
        int(np.clip((g + m) * 255.0, 0, 255)),
        int(np.clip((b + m) * 255.0, 0, 255)),
    )


class CustomEffectsEngine:
    """Real-time procedural light patterns and audio visualizer renderer."""

    EFFECTS_LIST = [
        {"id": "rainbow_flow", "name": "Gradiente en Giro", "category": "visual", "desc": "Rotación cromática suave a lo largo de las 3 tiras"},
        {"id": "meteor_chaser", "name": "Barra Móvil Cromática", "category": "visual", "desc": "Barra de luz con estela que viaja y muta de color"},
        {"id": "cosmic_aurora", "name": "Aurora Cósmica", "category": "visual", "desc": "Ondas bioluminiscentes de cian, esmeralda y violeta"},
        {"id": "fire_ember", "name": "Fuego & Brasas", "category": "visual", "desc": "Llamas ardientes de rojo, naranja y chispas doradas"},
        {"id": "cyberpunk_breath", "name": "Respiración Neón", "category": "visual", "desc": "Inhalación y exhalación suave entre tonos magenta y violeta"},
        {"id": "plasma_waves", "name": "Plasma Cósmico", "category": "visual", "desc": "Campos de energía oscilantes de alta fluidez"},
        {"id": "starlight_twinkle", "name": "Cielo Estrellado", "category": "visual", "desc": "Destellos aleatorios de estrellas brillantes sobre fondo nocturno"},
        {"id": "police_strobe", "name": "Estroboscópico Patrulla", "category": "visual", "desc": "Destellos policiales alternantes de alta cadencia"},
        {"id": "audio_converge", "name": "Espectro Convergente", "category": "audio", "desc": "La luz sube por ambos lados y colisiona arriba con el ritmo"},
        {"id": "audio_pulse", "name": "Pulso de Graves", "category": "audio", "desc": "Respiración reactiva con destellos de color en los picos de audio"},
        {"id": "audio_eq", "name": "Ecualizador 3 Bandas", "category": "audio", "desc": "Graves en los laterales, medios y agudos en el borde superior"},
        {"id": "audio_ripple", "name": "Onda Expansiva", "category": "audio", "desc": "Onda expansiva desde el centro hacia los extremos al ritmo de la música"},
    ]

    def __init__(self, driver: LedDriver):
        self.driver = driver
        self.audio = AudioCaptureListener()

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Effect parameters
        self.active_effect = "rainbow_flow"
        self.speed = 1.0            # 0.2x to 3.0x
        self.brightness = 100       # 0 to 100
        self.audio_sensitivity = 1.2 # 0.5x to 2.5x

        # Internal state
        self._current_colors: np.ndarray = np.zeros((34, 3), dtype=np.uint8)
        self._hue_offset = 0.0
        self._position = 0.0
        self._beat_hue = 180.0
        self._peak_decay = 0.0
        self._fps_actual = 0.0

        # State buffers for special procedural effects
        self._fire_heat = np.zeros(34, dtype=np.float32)
        self._stars_intensity = np.zeros(34, dtype=np.float32)
        self._ripple_pos = -1.0
        self._ripple_hue = 200.0

        # State buffers for fluid audio visualizer movement
        self._smooth_vol = 0.0
        self._smooth_bass = 0.0
        self._smooth_mids = 0.0
        self._smooth_treble = 0.0
        self._converge_height = 0.0
        self._converge_peak = 0.0
        self._converge_peak_hold = 0.0
        self._pulse_energy = 0.0
        self._eq_bars = np.zeros(34, dtype=np.float32)

        # Precomputed dual convergence symmetric paths:
        # Left path (17 steps): Zone 0 (bottom-left) -> 8 (top-left) -> 9..16 (top-center)
        self._left_path = list(range(0, 9)) + list(range(9, 17))
        # Right path (17 steps): Zone 33 (bottom-right) -> 25 (top-right) -> 24..17 (top-center)
        self._right_path = list(range(33, 24, -1)) + list(range(24, 16, -1))

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self, effect_name: Optional[str] = None) -> bool:
        """Starts the effect streaming thread."""
        if self._running:
            if effect_name:
                self.set_effect(effect_name)
            return True

        if effect_name:
            self.active_effect = effect_name

        if not self.driver.is_connected:
            if not self.driver.connect():
                print("[CustomEffectsEngine] Failed to connect to LED driver.")
                return False

        # Start audio listener if audio effect is selected
        if "audio" in self.active_effect:
            self.audio.start()

        self._running = True
        self._thread = threading.Thread(target=self._render_loop, daemon=True, name="CosmoLights-Effects")
        self._thread.start()
        print(f"[CustomEffectsEngine] Started effect '{self.active_effect}'.")
        return True

    def stop(self) -> None:
        """Stops the effect stream."""
        if not self._running:
            return

        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

        if self.audio.is_running:
            self.audio.stop()

        if self.driver.is_connected:
            self.driver.turn_off()

        print("[CustomEffectsEngine] Effect stopped.")

    def set_effect(self, effect_name: str, speed: Optional[float] = None) -> None:
        """Switches active effect pattern dynamically."""
        with self._lock:
            self.active_effect = effect_name
            if speed is not None:
                self.speed = speed

        # Ensure audio listener is active if switching to an audio effect
        if "audio" in effect_name and not self.audio.is_running:
            self.audio.start()
        elif "audio" not in effect_name and self.audio.is_running:
            self.audio.stop()

    def set_brightness(self, level: int) -> None:
        """Sets effect brightness (0-100), applied via real-time software scaling."""
        with self._lock:
            self.brightness = max(0, min(100, int(level)))

    def set_speed(self, speed: float) -> None:
        self.speed = max(0.1, min(5.0, float(speed)))

    def set_audio_sensitivity(self, sens: float) -> None:
        self.audio_sensitivity = max(0.5, min(3.0, float(sens)))

    def get_stats(self) -> Dict[str, Any]:
        """Telemetry metrics for the UI."""
        with self._lock:
            return {
                "running": self._running,
                "active_effect": self.active_effect,
                "speed": self.speed,
                "brightness": self.brightness,
                "fps": round(self._fps_actual, 1),
                "led_preview": self._current_colors.tolist()
            }

    # -------------------------------------------------------------------------
    # Procedural Effect Generators (Returning 34 RGB tuples)
    # -------------------------------------------------------------------------

    def _gen_rainbow_flow(self, dt: float) -> List[Tuple[int, int, int]]:
        """1. Gradiente que gira: Rotación suave de espectro cromático."""
        self._hue_offset = (self._hue_offset + dt * 90.0 * self.speed) % 360.0
        colors = []
        for i in range(34):
            hue = (self._hue_offset + (i * 360.0 / 34.0)) % 360.0
            colors.append(hsv_to_rgb(hue, s=1.0, v=1.0))
        return colors

    def _gen_meteor_chaser(self, dt: float) -> List[Tuple[int, int, int]]:
        """2. Barra de luz pequeña que rota y cambia de color con estela suave."""
        self._position = (self._position + dt * 14.0 * self.speed) % 34.0
        self._hue_offset = (self._hue_offset + dt * 45.0 * self.speed) % 360.0

        bar_head = self._position
        tail_len = 7.0
        colors = []

        for i in range(34):
            dist = (bar_head - i) % 34.0
            if dist < tail_len:
                brightness_fade = max(0.0, 1.0 - (dist / tail_len))
                hue = (self._hue_offset + dist * 10.0) % 360.0
                colors.append(hsv_to_rgb(hue, s=1.0, v=brightness_fade))
            else:
                colors.append(hsv_to_rgb(self._hue_offset, s=0.9, v=0.04))

        return colors

    def _gen_cosmic_aurora(self, dt: float) -> List[Tuple[int, int, int]]:
        """3. Aurora Cósmica: Ondas bioluminiscentes de cian, verde esmeralda y violeta."""
        self._hue_offset = (self._hue_offset + dt * 30.0 * self.speed) % 360.0
        t = time.perf_counter() * self.speed
        colors = []

        for i in range(34):
            wave1 = math.sin(t * 1.5 + i * 0.25)
            wave2 = math.cos(t * 0.9 - i * 0.18)
            combined = (wave1 + wave2) / 2.0

            base_hue = 170.0 + (combined * 60.0)
            brightness = 0.85 + 0.15 * math.sin(t * 2.0 + i * 0.3)
            colors.append(hsv_to_rgb(base_hue, s=1.0, v=brightness))

        return colors

    def _gen_fire_ember(self, dt: float) -> List[Tuple[int, int, int]]:
        """4. Fuego & Brasas: Algoritmo de calor térmico procedural con chispas de fuego."""
        cooling = 2.4 * dt * self.speed
        self._fire_heat = np.maximum(0.0, self._fire_heat - cooling)

        # Chispas aleatorias en la base y perímetro
        num_sparks = random.randint(2, 5)
        for _ in range(num_sparks):
            idx = random.randint(0, 33)
            self._fire_heat[idx] = min(1.0, self._fire_heat[idx] + random.uniform(0.3, 0.8))

        # Difusión térmica suave entre vecinos
        smooth_heat = np.copy(self._fire_heat)
        for i in range(34):
            prev_idx = (i - 1) % 34
            next_idx = (i + 1) % 34
            smooth_heat[i] = (self._fire_heat[prev_idx] + self._fire_heat[i] * 2.0 + self._fire_heat[next_idx]) / 4.0
        self._fire_heat = smooth_heat

        colors = []
        for heat in self._fire_heat:
            # Rango térmico: Rojo profundo (0-15 hue) -> Ámbar (20-35) -> Amarillo incandescente (45-55)
            hue = heat * 48.0
            val = min(1.0, heat * 1.3)
            sat = max(0.65, 1.0 - (heat * 0.3))
            colors.append(hsv_to_rgb(hue, s=sat, v=val))
        return colors

    def _gen_cyberpunk_breath(self, dt: float) -> List[Tuple[int, int, int]]:
        """5. Respiración Neón Cyberpunk: Pulso suave con gradiente oscilante magenta/violeta."""
        t = time.perf_counter() * self.speed * 1.8
        # Pulso sinusoidal suave
        breathe = (math.sin(t) + 1.0) / 2.0  # 0.0 a 1.0
        brightness = 0.20 + (breathe * 0.80)

        colors = []
        for i in range(34):
            # Gradiente espacial magenta (300) a violeta (260)
            offset = math.sin((i / 34.0) * math.pi * 2.0 + t * 0.5)
            hue = 280.0 + (offset * 30.0)
            colors.append(hsv_to_rgb(hue, s=1.0, v=brightness))
        return colors

    def _gen_plasma_waves(self, dt: float) -> List[Tuple[int, int, int]]:
        """6. Plasma Cósmico: Interferencia de 3 frecuencias sinusoidales fluidas."""
        t = time.perf_counter() * self.speed * 2.2
        colors = []
        for i in range(34):
            v1 = math.sin(i * 0.4 + t)
            v2 = math.sin(i * 0.25 - t * 0.8)
            v3 = math.sin((i * 0.3 + t * 1.2) + math.sin(i * 0.15 + t))
            plasma = (v1 + v2 + v3) / 3.0  # -1.0 a 1.0

            hue = (220.0 + (plasma * 120.0)) % 360.0
            val = 0.75 + 0.25 * math.cos(i * 0.2 + t)
            colors.append(hsv_to_rgb(hue, s=0.95, v=val))
        return colors

    def _gen_starlight_twinkle(self, dt: float) -> List[Tuple[int, int, int]]:
        """7. Cielo Estrellado: Destellos aleatorios suaves y centelleo sobre fondo azul noche."""
        # Decaimiento continuo
        decay = 1.8 * dt * self.speed
        self._stars_intensity = np.maximum(0.0, self._stars_intensity - decay)

        # Aparición esporádica de nuevas estrellas
        if random.random() < (0.28 * self.speed):
            idx = random.randint(0, 33)
            self._stars_intensity[idx] = 1.0

        colors = []
        for intensity in self._stars_intensity:
            # Fondo azul profundo a blanco brillante en el pico
            val = max(0.08, float(intensity))
            sat = max(0.0, 1.0 - float(intensity) * 0.85)  # En pico se torna blanco puro
            hue = 225.0
            colors.append(hsv_to_rgb(hue, s=sat, v=val))
        return colors

    def _gen_police_strobe(self, dt: float) -> List[Tuple[int, int, int]]:
        """8. Estroboscópico Patrulla: Ráfagas rápidas alternadas rojo/azul en lados opuestos."""
        t = time.perf_counter() * self.speed * 5.0
        phase = int(t) % 4
        sub_flash = (t * 4.0) % 1.0 > 0.5  # Sub-parpadeo rápido estroboscópico

        frame = [(4, 4, 10)] * 34

        if sub_flash:
            if phase in (0, 1):
                # Izquierda rojo intenso
                for i in range(17):
                    frame[i] = (255, 0, 10)
            else:
                # Derecha azul intenso
                for i in range(17, 34):
                    frame[i] = (0, 70, 255)

        return frame

    def _gen_audio_converge(self, dt: float) -> List[Tuple[int, int, int]]:
        """
        9. Espectro convergente hiper-fluido:
        - Físicas de resorte/LERP para altura continua no cuantizada.
        - Peak meter con retención y caída por gravedad (estilo analizador de espectro).
        - Cabeza con antialiasing sub-zona para movimiento ultra-suave sin saltos bruscos.
        """
        feats = self.audio.get_features()
        vol = min(1.0, feats["volume"] * self.audio_sensitivity)

        # Suavizado asimétrico continuo de altura objetivo (0.0 a 17.0)
        target_height = vol * 17.0
        if target_height > self._converge_height:
            # Subida rápida y responsiva
            self._converge_height += (target_height - self._converge_height) * min(1.0, dt * 18.0)
        else:
            # Caída suave con inercia
            self._converge_height += (target_height - self._converge_height) * min(1.0, dt * 7.5)

        # Físicas del pico flotante (Peak Meter)
        if self._converge_height >= self._converge_peak:
            self._converge_peak = self._converge_height
            self._converge_peak_hold = 0.12  # Retención momentánea en el punto más alto
        else:
            if self._converge_peak_hold > 0.0:
                self._converge_peak_hold -= dt
            else:
                # Caída por aceleración/gravedad
                self._converge_peak = max(self._converge_height, self._converge_peak - dt * 9.0)

        # Cambio de tono suave continuo + impulso en beat
        if feats["is_beat"]:
            self._beat_hue = (self._beat_hue + 35.0 + (feats["beat_intensity"] * 25.0)) % 360.0

        self._beat_hue = (self._beat_hue + dt * 20.0 * self.speed) % 360.0

        frame = [(4, 4, 10)] * 34  # Fondo ambiental tenue

        cur_h = self._converge_height
        peak_idx = int(round(self._converge_peak))

        for step in range(17):
            l_zone = self._left_path[step]
            r_zone = self._right_path[step]

            # Interpolación sub-pixel/sub-zona
            diff = cur_h - step
            if diff >= 1.0:
                intensity = 1.0
            elif diff > 0.0:
                intensity = diff  # Antialiasing suave en la punta
            else:
                intensity = 0.0

            if intensity > 0.0:
                progress = step / 17.0
                hue = (self._beat_hue + (progress * 70.0)) % 360.0
                rgb = hsv_to_rgb(hue, s=1.0, v=intensity)
                frame[l_zone] = rgb
                frame[r_zone] = rgb

            # Dibujar pico flotante si está por encima
            if step == peak_idx and step > 1 and intensity < 0.85:
                peak_hue = (self._beat_hue + 140.0) % 360.0
                peak_rgb = hsv_to_rgb(peak_hue, s=0.8, v=0.95)
                frame[l_zone] = peak_rgb
                frame[r_zone] = peak_rgb

        return frame

    def _gen_audio_pulse(self, dt: float) -> List[Tuple[int, int, int]]:
        """
        10. Pulso de graves orgánico:
        - Respiración armónica continua con filtro LERP.
        - Onda de choque radial que viaja por el perímetro durante los picos de bombo/bajos.
        """
        feats = self.audio.get_features()
        bass = min(1.0, feats["bass"] * self.audio_sensitivity)

        # LERP continuo de energía de bajos
        target_energy = bass
        if target_energy > self._pulse_energy:
            self._pulse_energy += (target_energy - self._pulse_energy) * min(1.0, dt * 22.0)
        else:
            self._pulse_energy += (target_energy - self._pulse_energy) * min(1.0, dt * 6.0)

        # Decaimiento y disparo de explosión en golpe
        if feats["is_beat"]:
            self._beat_hue = (self._beat_hue + 45.0) % 360.0
            self._peak_decay = 1.0
        else:
            self._peak_decay = max(0.0, self._peak_decay - dt * 3.8)

        # Deriva lenta cromática
        self._beat_hue = (self._beat_hue + dt * 15.0 * self.speed) % 360.0

        # Base con respiración sinusoidal ambiental suave
        t = time.perf_counter() * 1.5
        ambient_breath = 0.08 + 0.04 * math.sin(t)
        center_boost = self._pulse_energy * 0.70 + self._peak_decay * 0.35

        frame = []
        for i in range(34):
            # Modular ligeramente la intensidad según la distancia al centro superior para dar profundidad 3D
            dist_from_top = abs(i - 16.5) / 16.5  # 0 en centro superior, 1 en bases
            local_val = np.clip(ambient_breath + center_boost * (1.15 - dist_from_top * 0.3), 0.0, 1.0)
            local_hue = (self._beat_hue + (dist_from_top * 35.0)) % 360.0
            frame.append(hsv_to_rgb(local_hue, s=1.0, v=local_val))

        return frame

    def _gen_audio_eq(self, dt: float) -> List[Tuple[int, int, int]]:
        """
        11. Ecualizador 3 Bandas analógico fluido:
        - Interpolación continua barra por barra con caída balística sin escalonamiento brusco.
        - Antialiasing perimetral: Bajos en laterales, Medios en esquinas superiores y Agudos al centro.
        """
        feats = self.audio.get_features()
        bass = min(1.0, feats["bass"] * self.audio_sensitivity)
        mids = min(1.0, feats["mids"] * self.audio_sensitivity)
        treble = min(1.0, feats["treble"] * self.audio_sensitivity)

        if feats["is_beat"]:
            self._beat_hue = (self._beat_hue + 25.0) % 360.0

        self._beat_hue = (self._beat_hue + dt * 12.0 * self.speed) % 360.0

        # Vector de alturas objetivo para cada una de las 34 zonas
        target_levels = np.zeros(34, dtype=np.float32)

        # Bajos: Izquierda (0..8) y Derecha (25..33), escalando desde la base
        bass_height = bass * 9.0
        for i in range(9):
            diff = bass_height - i
            val = np.clip(diff, 0.0, 1.0)
            target_levels[i] = val
            target_levels[33 - i] = val

        # Medios: Esquinas superiores (9..12 y 21..24)
        mids_height = mids * 4.0
        for i, z in enumerate([9, 10, 11, 12]):
            val = np.clip(mids_height - i, 0.0, 1.0)
            target_levels[z] = val
            target_levels[24 - i] = val

        # Agudos: Centro superior (13..20)
        treble_height = treble * 4.0
        for i in range(4):
            val = np.clip(treble_height - i, 0.0, 1.0)
            target_levels[16 - i] = val
            target_levels[17 + i] = val

        # LERP individualizado de cada zona: subida instantánea (~22/s), caída suave (~8/s)
        for i in range(34):
            tgt = target_levels[i]
            cur = self._eq_bars[i]
            if tgt > cur:
                self._eq_bars[i] = cur + (tgt - cur) * min(1.0, dt * 24.0)
            else:
                self._eq_bars[i] = cur + (tgt - cur) * min(1.0, dt * 7.0)

        frame = []
        for i in range(34):
            level = float(self._eq_bars[i])
            # Color por banda con gradiente armónico:
            if i <= 8 or i >= 25:
                # Banda Bajos (cálido / base hue)
                hue = self._beat_hue
            elif (9 <= i <= 12) or (21 <= i <= 24):
                # Banda Medios (+110°)
                hue = (self._beat_hue + 110.0) % 360.0
            else:
                # Banda Agudos (+220°)
                hue = (self._beat_hue + 220.0) % 360.0

            val = max(0.04, level)
            sat = 1.0 if level > 0.05 else 0.7
            frame.append(hsv_to_rgb(hue, s=sat, v=val))

        return frame

    def _gen_audio_ripple(self, dt: float) -> List[Tuple[int, int, int]]:
        """12. Onda Expansiva: Al detectar beats/bajos, lanza una onda desde el centro superior."""
        feats = self.audio.get_features()

        if feats["is_beat"] and self._ripple_pos < 0.0:
            self._ripple_pos = 0.0
            self._ripple_hue = (self._ripple_hue + 55.0) % 360.0

        if self._ripple_pos >= 0.0:
            self._ripple_pos += dt * 18.0 * self.speed
            if self._ripple_pos > 17.0:
                self._ripple_pos = -1.0

        # Fondo tenue reactivo al volumen
        vol = min(1.0, feats["volume"] * self.audio_sensitivity)
        base_val = 0.05 + (vol * 0.15)
        frame = [hsv_to_rgb(self._ripple_hue, s=0.9, v=base_val)] * 34

        # Si hay onda activa, se propaga por left_path y right_path
        if self._ripple_pos >= 0.0:
            wave_width = 3.5
            for step in range(17):
                dist = abs(step - self._ripple_pos)
                if dist < wave_width:
                    fade = max(0.0, 1.0 - (dist / wave_width))
                    # El centro top es el inicio (step 16 hacia abajo)
                    # O bien invertido: del centro hacia los lados
                    inv_step = 16 - step
                    l_zone = self._left_path[inv_step]
                    r_zone = self._right_path[inv_step]
                    wave_rgb = hsv_to_rgb((self._ripple_hue + 60.0) % 360.0, s=1.0, v=fade)
                    frame[l_zone] = wave_rgb
                    frame[r_zone] = wave_rgb

        return frame

    # -------------------------------------------------------------------------
    # Render Loop
    # -------------------------------------------------------------------------

    def _render_loop(self) -> None:
        """Main procedural rendering loop (40 FPS)."""
        target_fps = 40
        interval = 1.0 / target_fps
        last_time = time.perf_counter()
        fps_timer = last_time
        frames_cnt = 0

        while self._running:
            now = time.perf_counter()
            dt = now - last_time
            last_time = now

            with self._lock:
                eff = self.active_effect
                b_factor = max(0.0, min(1.0, self.brightness / 100.0))

            # Dispatch effect generator
            if eff == "rainbow_flow":
                frame_colors = self._gen_rainbow_flow(dt)
            elif eff == "meteor_chaser":
                frame_colors = self._gen_meteor_chaser(dt)
            elif eff == "cosmic_aurora":
                frame_colors = self._gen_cosmic_aurora(dt)
            elif eff == "fire_ember":
                frame_colors = self._gen_fire_ember(dt)
            elif eff == "cyberpunk_breath":
                frame_colors = self._gen_cyberpunk_breath(dt)
            elif eff == "plasma_waves":
                frame_colors = self._gen_plasma_waves(dt)
            elif eff == "starlight_twinkle":
                frame_colors = self._gen_starlight_twinkle(dt)
            elif eff == "police_strobe":
                frame_colors = self._gen_police_strobe(dt)
            elif eff == "audio_converge":
                frame_colors = self._gen_audio_converge(dt)
            elif eff == "audio_pulse":
                frame_colors = self._gen_audio_pulse(dt)
            elif eff == "audio_eq":
                frame_colors = self._gen_audio_eq(dt)
            elif eff == "audio_ripple":
                frame_colors = self._gen_audio_ripple(dt)
            else:
                frame_colors = self._gen_rainbow_flow(dt)

            # Master brightness scaling
            scaled_colors = [
                (
                    int(np.clip(r * b_factor, 0, 255)),
                    int(np.clip(g * b_factor, 0, 255)),
                    int(np.clip(b * b_factor, 0, 255))
                )
                for (r, g, b) in frame_colors
            ]

            # Update preview buffer
            with self._lock:
                self._current_colors = np.array(scaled_colors, dtype=np.uint8)

            # Transmit directly over USB
            self.driver.sync_screen_frame(scaled_colors)

            # Performance telemetry
            frames_cnt += 1
            if now - fps_timer >= 1.0:
                self._fps_actual = frames_cnt / (now - fps_timer)
                frames_cnt = 0
                fps_timer = now

            # Frame rate throttle
            elapsed = time.perf_counter() - now
            sleep_t = interval - elapsed
            if sleep_t > 0.001:
                time.sleep(sleep_t)
