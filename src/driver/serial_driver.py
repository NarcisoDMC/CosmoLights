"""
serial_driver.py - Serial COM / Adalight Protocol Driver for Arduino and ESP32.

Implements the standard Adalight streaming protocol over USB-UART:
Header: 'Ada' (0x41, 0x64, 0x61)
High count: (num_leds - 1) >> 8
Low count: (num_leds - 1) & 0xFF
Checksum: High count ^ Low count ^ 0x55
Payload: [R1, G1, B1, R2, G2, B2, ...]
"""

from typing import List, Tuple, Dict, Any, Optional
import threading
import time

from .base_driver import BaseLedDriver

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


class SerialLedDriver(BaseLedDriver):
    """Driver for Arduino / ESP32 running FastLED / NeoPixel with Adalight protocol."""

    DEFAULT_BAUDRATE = 115200

    def __init__(
        self,
        port: str = "COM3",
        baudrate: int = DEFAULT_BAUDRATE,
        total_leds: int = 63,
        timeout: float = 1.0
    ):
        self.port = port
        self.baudrate = baudrate
        self.total_leds = total_leds
        self.timeout = timeout
        self._ser: Optional[Any] = None
        self._lock = threading.Lock()
        self._is_connected = False

    @classmethod
    def list_ports(cls) -> List[Dict[str, str]]:
        """Returns detected serial COM ports on the system."""
        if not SERIAL_AVAILABLE:
            return []
        ports = []
        for p in serial.tools.list_ports.comports():
            ports.append({
                "port": p.device,
                "description": p.description,
                "hwid": p.hwid,
            })
        return ports

    @property
    def is_connected(self) -> bool:
        return self._is_connected and self._ser is not None and self._ser.is_open

    @property
    def driver_type(self) -> str:
        return "serial"

    @property
    def device_info(self) -> Dict[str, Any]:
        return {
            "type": "serial",
            "port": self.port,
            "baudrate": self.baudrate,
            "total_leds": self.total_leds,
            "connected": self.is_connected,
        }

    def connect(self) -> bool:
        if not SERIAL_AVAILABLE:
            print("[SerialLedDriver] pyserial no está instalado. Ejecuta: pip install pyserial")
            return False

        with self._lock:
            try:
                self._ser = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=self.timeout,
                    write_timeout=self.timeout
                )
                time.sleep(1.5)  # Allow Arduino / ESP32 reset after DTR toggle
                self._is_connected = True
                print(f"[SerialLedDriver] Conectado exitosamente a {self.port} @ {self.baudrate} baud.")
                return True
            except Exception as e:
                print(f"[SerialLedDriver] Error al conectar con {self.port}: {e}")
                self._is_connected = False
                self._ser = None
                return False

    def disconnect(self) -> None:
        with self._lock:
            if self._ser and self._ser.is_open:
                try:
                    self._ser.close()
                except Exception:
                    pass
            self._ser = None
            self._is_connected = False

    @staticmethod
    def build_adalight_packet(colors: List[Tuple[int, int, int]], total_leds: int) -> bytes:
        """
        Builds the raw Adalight binary frame payload.
        Ensures exact total_leds count.
        """
        padded = list(colors[:total_leds])
        while len(padded) < total_leds:
            padded.append((0, 0, 0))

        count = len(padded) - 1
        hi = (count >> 8) & 0xFF
        lo = count & 0xFF
        chk = hi ^ lo ^ 0x55

        header = bytes([0x41, 0x64, 0x61, hi, lo, chk])  # 'Ada' + hi + lo + chk
        payload = bytearray(header)
        for r, g, b in padded:
            payload.append(max(0, min(255, int(r))))
            payload.append(max(0, min(255, int(g))))
            payload.append(max(0, min(255, int(b))))

        return bytes(payload)

    def sync_screen_frame(self, colors: List[Tuple[int, int, int]]) -> bool:
        if not self.is_connected:
            return False

        data = self.build_adalight_packet(colors, self.total_leds)
        try:
            with self._lock:
                if self._ser and self._ser.is_open:
                    self._ser.write(data)
                    return True
        except Exception as e:
            print(f"[SerialLedDriver] Error en transmisión serial: {e}")
            self.disconnect()
        return False

    def set_solid_color(self, r: int, g: int, b: int) -> bool:
        return self.sync_screen_frame([(r, g, b)] * self.total_leds)

    def turn_off(self) -> bool:
        return self.sync_screen_frame([(0, 0, 0)] * self.total_leds)
