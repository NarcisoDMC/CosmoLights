"""
audio_capture.py - Real-Time Desktop WASAPI Loopback Audio Listener.

Captures system audio playback directly from Windows default output device using `soundcard`.
Analyzes volume envelope (RMS), frequency spectrum (FFT: Bass, Mids, Treble),
and detects beat/bass transient peaks for dynamic rhythm visualizer effects.
"""

from typing import Dict, Any, Optional
import threading
import time
import numpy as np


class AudioCaptureListener:
    """Non-blocking background thread that captures and analyzes desktop audio."""

    def __init__(self, sample_rate: int = 44100, block_size: int = 1024):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Audio features state
        self._volume = 0.0          # Normalized 0.0 to 1.0
        self._bass = 0.0            # Normalized 0.0 to 1.0
        self._mids = 0.0            # Normalized 0.0 to 1.0
        self._treble = 0.0          # Normalized 0.0 to 1.0
        self._is_beat = False       # Transient peak flag
        self._beat_intensity = 0.0  # Spike strength (0.0 to 1.0)
        self._beat_count = 0

        # Dynamic Auto-Gain Control (AGC) state
        self._peak_history = 0.05
        self._last_beat_time = 0.0

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> bool:
        """Starts audio loopback listener in background."""
        if self._running:
            return True

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True, name="CosmoLights-Audio")
        self._thread.start()
        print("[AudioCaptureListener] Started desktop audio listener.")
        return True

    def stop(self) -> None:
        """Stops the audio listener."""
        if not self._running:
            return
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None
        print("[AudioCaptureListener] Stopped audio listener.")

    def get_features(self) -> Dict[str, Any]:
        """Returns current instant audio metrics."""
        with self._lock:
            beat = self._is_beat
            self._is_beat = False  # Reset pulse flag once consumed
            return {
                "volume": float(self._volume),
                "bass": float(self._bass),
                "mids": float(self._mids),
                "treble": float(self._treble),
                "is_beat": beat,
                "beat_intensity": float(self._beat_intensity),
                "beat_count": self._beat_count
            }

    def _capture_loop(self) -> None:
        """Background loop reading from WASAPI loopback recorder."""
        try:
            import soundcard as sc
        except ImportError:
            print("[AudioCaptureListener] 'soundcard' package not found.")
            self._running = False
            return

        mic = None
        try:
            default_sp = sc.default_speaker()
            mic = sc.get_microphone(default_sp.name, include_loopback=True)
        except Exception as e:
            print(f"[AudioCaptureListener] Failed to find loopback microphone: {e}")
            # Try first available microphone with loopback
            try:
                mics = sc.all_microphones(include_loopback=True)
                if mics:
                    mic = mics[0]
            except Exception:
                pass

        if mic is None:
            print("[AudioCaptureListener] No audio output device found.")
            self._running = False
            return

        while self._running:
            try:
                with mic.recorder(samplerate=self.sample_rate, blocksize=self.block_size) as recorder:
                    while self._running:
                        data = recorder.record(numframes=self.block_size)
                        if data is None or len(data) == 0:
                            time.sleep(0.01)
                            continue

                        # Convert stereo to mono
                        if data.ndim > 1:
                            mono = np.mean(data, axis=1)
                        else:
                            mono = data

                        # 1. Instant RMS Volume
                        rms = float(np.sqrt(np.mean(mono ** 2)))

                        # Auto-Gain Control (AGC): smoothly track peak level
                        if rms > self._peak_history:
                            self._peak_history = self._peak_history * 0.7 + rms * 0.3
                        else:
                            self._peak_history = max(0.02, self._peak_history * 0.99)

                        # Normalized volume (0.0 to 1.0)
                        norm_vol = np.clip(rms / max(0.01, self._peak_history), 0.0, 1.0)

                        # 2. FFT Spectral Analysis
                        fft_vals = np.abs(np.fft.rfft(mono))
                        freq_bins = len(fft_vals)

                        # Frequency bands:
                        # Bass: 20 - 250 Hz
                        b_end = max(2, int(freq_bins * (250.0 / (self.sample_rate / 2))))
                        # Mids: 250 - 2500 Hz
                        m_end = max(b_end + 1, int(freq_bins * (2500.0 / (self.sample_rate / 2))))

                        raw_bass = float(np.mean(fft_vals[1:b_end])) if b_end > 1 else 0.0
                        raw_mids = float(np.mean(fft_vals[b_end:m_end])) if m_end > b_end else 0.0
                        raw_treble = float(np.mean(fft_vals[m_end:])) if freq_bins > m_end else 0.0

                        norm_bass = np.clip(raw_bass * 4.0, 0.0, 1.0)
                        norm_mids = np.clip(raw_mids * 5.0, 0.0, 1.0)
                        norm_treble = np.clip(raw_treble * 8.0, 0.0, 1.0)

                        # 3. Beat / Transient Peak Detection
                        now = time.perf_counter()
                        is_beat = False
                        beat_intensity = 0.0

                        # Beat trigger: sudden energy spike in bass or volume
                        if norm_vol > 0.45 and (norm_vol > self._volume * 1.35 or norm_bass > 0.6):
                            if now - self._last_beat_time > 0.14:  # Max ~7 beats/sec limit
                                is_beat = True
                                beat_intensity = min(1.0, norm_vol * 1.2)
                                self._last_beat_time = now
                                self._beat_count += 1

                        with self._lock:
                            # Asymmetric attack/decay filter: fast response on rise, organic smooth decay on fall
                            vol_att = 0.75 if norm_vol > self._volume else 0.18
                            bass_att = 0.80 if norm_bass > self._bass else 0.16
                            mids_att = 0.70 if norm_mids > self._mids else 0.18
                            treble_att = 0.75 if norm_treble > self._treble else 0.20

                            self._volume = self._volume * (1.0 - vol_att) + norm_vol * vol_att
                            self._bass = self._bass * (1.0 - bass_att) + norm_bass * bass_att
                            self._mids = self._mids * (1.0 - mids_att) + norm_mids * mids_att
                            self._treble = self._treble * (1.0 - treble_att) + norm_treble * treble_att

                            if is_beat:
                                self._is_beat = True
                                self._beat_intensity = beat_intensity

            except Exception as e:
                # If audio stream is interrupted (e.g. sample rate change, sleep/wake), retry
                time.sleep(0.5)
