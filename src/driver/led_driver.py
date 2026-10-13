"""
led_driver.py - Hardware Driver for QinHeng (VID 0x1A86, PID 0xFE07) LED Controller.

Decoded via Wireshark USB reverse engineering.
Communicates directly with USB Interface 0, Endpoint 0x01 using 64-byte raw packets.
"""

from typing import List, Tuple, Optional
import threading
import time
import usb.core
import usb.util
import libusb_package


class LedDriver:
    # Hardware IDs (QinHeng Electronics USB Composite Device)
    VID = 0x1A86
    PID = 0xFE07
    INTERFACE_NUM = 0
    ENDPOINT_OUT = 0x01
    ENDPOINT_IN = 0x82
    PACKET_SIZE = 64

    # Default LED strip parameters
    TOTAL_LEDS = 63
    MAX_ADDRESSABLE_LEDS = 254

    # Protocol Commands (Decoded from DX Light & Wireshark capture)
    CMD_SYNC_SCREEN = 0x80       # 128: Ambilight streaming (Header 'SC')
    CMD_SET_SECTION_LED = 0x86   # 134: Color by section / solid color
    CMD_SET_BRIGHTNESS = 0x87    # 135: Brightness level (0-100)
    CMD_SET_LED_EFFECT = 0x85    # 133: Dynamic built-in effects
    CMD_TURN_OFF = 0x97          # 151: Turn off lights
    CMD_AUDIO_RHYTHM = 0x98      # 152: Sound / rhythm reaction

    # 34 Predefined hardware zones decoded from USB captures covering 63 LEDs
    DEFAULT_ZONES = [
        (1, 1), (2, 3), (4, 5), (6, 7), (8, 10),
        (11, 12), (13, 14), (15, 16), (17, 17), (18, 19),
        (20, 20), (21, 22), (23, 24), (25, 26), (27, 28),
        (29, 30), (31, 32), (33, 34), (35, 36), (37, 38),
        (39, 40), (41, 42), (43, 44), (45, 45), (46, 46),
        (47, 47), (48, 49), (50, 51), (52, 53), (54, 56),
        (57, 58), (59, 60), (61, 62), (63, 63)
    ]

    def __init__(self, total_leds: int = TOTAL_LEDS):
        self.total_leds = total_leds
        self._dev: Optional[usb.core.Device] = None
        self._ep_out = None
        self._seq = 1
        self._is_connected = False
        self._write_lock = threading.Lock()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    @property
    def is_connected(self) -> bool:
        return self._is_connected and self._dev is not None

    def connect(self) -> bool:
        """Finds and claims the USB LED strip controller."""
        try:
            # Find device using libusb-package backend
            self._dev = libusb_package.find(idVendor=self.VID, idProduct=self.PID)
            if self._dev is None:
                print(f"[LedDriver] Device {hex(self.VID)}:{hex(self.PID)} not found.")
                return False

            # On Linux/macOS, detach kernel driver if bound
            try:
                if self._dev.is_kernel_driver_active(self.INTERFACE_NUM):
                    self._dev.detach_kernel_driver(self.INTERFACE_NUM)
            except (NotImplementedError, usb.core.USBError):
                pass

            # Claim interface 0
            usb.util.claim_interface(self._dev, self.INTERFACE_NUM)

            # Get configuration and OUT endpoint
            cfg = self._dev.get_active_configuration()
            intf = cfg[(self.INTERFACE_NUM, 0)]

            self._ep_out = usb.util.find_descriptor(
                intf,
                custom_match=lambda e: (
                    usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
                    and e.bEndpointAddress == self.ENDPOINT_OUT
                )
            )

            if not self._ep_out:
                print("[LedDriver] Endpoint 0x01 OUT not found.")
                return False

            self._is_connected = True
            print("[LedDriver] Connected successfully to LED Strip controller.")
            return True

        except Exception as e:
            print(f"[LedDriver] Connection error: {e}")
            self.disconnect()
            return False

    def disconnect(self):
        """Releases the USB interface and closes the connection."""
        with self._write_lock:
            if self._dev:
                try:
                    usb.util.release_interface(self._dev, self.INTERFACE_NUM)
                    usb.util.dispose_resources(self._dev)
                except Exception:
                    pass
            self._dev = None
            self._ep_out = None
            self._is_connected = False
            print("[LedDriver] Disconnected from device.")

    def _next_seq(self) -> int:
        """Generates an incremental sequence ID (1-254)."""
        seq = self._seq
        self._seq = 1 if self._seq >= 254 else self._seq + 1
        return seq

    @staticmethod
    def _calc_checksum(data: bytes) -> int:
        """Calculates checksum: (sum of bytes) % 256."""
        return sum(data) % 256

    def _send_rb_command(self, action: int, params: List[int] = None) -> bool:
        """
        Builds and transfers a 64-byte command packet with 'RB' header.
        
        Packet layout:
          Bytes 0-1: 'RB' (0x52, 0x42)
          Byte 2:    Total length of meaningful payload
          Byte 3:    Sequence ID (incremental)
          Byte 4:    Action / Command byte
          Bytes 5..: Parameters
          Last byte: Checksum ((sum of all preceding bytes) % 256)
          Remaining: Padded with 0x00 to exactly 64 bytes
        """
        if not self.is_connected:
            raise ConnectionError("LED Controller is not connected. Call connect() first.")

        if params is None:
            params = []

        payload_len = 5 + len(params) + 1
        seq = self._next_seq()

        # Build payload buffer
        payload = bytearray()
        payload.extend(b'RB')
        payload.append(payload_len)
        payload.append(seq)
        payload.append(action)
        payload.extend(params)

        # Calculate and append checksum
        checksum = self._calc_checksum(payload)
        payload.append(checksum)

        # Pad to exactly 64 bytes (the hardware requires 64-byte transfers)
        if len(payload) < self.PACKET_SIZE:
            payload.extend(b'\x00' * (self.PACKET_SIZE - len(payload)))
        elif len(payload) > self.PACKET_SIZE:
            payload = payload[:self.PACKET_SIZE]

        try:
            with self._write_lock:
                if not self._ep_out:
                    return False
                self._ep_out.write(bytes(payload))
            return True
        except usb.core.USBError as e:
            print(f"[LedDriver] Write error on action 0x{action:02X}: {e}")
            return False

    def set_brightness(self, level: int) -> bool:
        """Sets global brightness (0 to 100)."""
        level = max(0, min(100, int(level)))
        return self._send_rb_command(self.CMD_SET_BRIGHTNESS, [level])

    def set_solid_color(self, r: int, g: int, b: int) -> bool:
        """Sets a uniform static color on all LEDs (1 to total_leds)."""
        r = max(0, min(255, int(r)))
        g = max(0, min(255, int(g)))
        b = max(0, min(255, int(b)))

        # Format decoded in frame 5063:
        # [start_led_1, R, G, B, end_led_1, start_led_2, 0, 0, 0, end_led_2]
        params = [
            1, r, g, b, self.total_leds,
            self.total_leds + 1, 0, 0, 0, self.MAX_ADDRESSABLE_LEDS
        ]
        return self._send_rb_command(self.CMD_SET_SECTION_LED, params)

    def set_sections(self, sections: List[Tuple[int, int, int, int, int]]) -> bool:
        """
        Sets colors for arbitrary LED ranges.
        Each section is a tuple: (start_led, r, g, b, end_led).
        """
        params = []
        for start, r, g, b, end in sections:
            params.extend([
                max(1, start),
                max(0, min(255, r)),
                max(0, min(255, g)),
                max(0, min(255, b)),
                max(1, min(self.MAX_ADDRESSABLE_LEDS, end))
            ])
        return self._send_rb_command(self.CMD_SET_SECTION_LED, params)

    def set_effect(self, effect_type: int = 1, param: int = 1) -> bool:
        """Sets a built-in hardware dynamic effect (e.g. rainbow, breathing)."""
        return self._send_rb_command(self.CMD_SET_LED_EFFECT, [effect_type, param])

    def turn_off(self) -> bool:
        """Turns off all LEDs."""
        return self._send_rb_command(self.CMD_TURN_OFF, [])

    def sync_screen_frame(self, colors: List[Tuple[int, int, int]]) -> bool:
        """
        Transmits a single Ambilight frame (live screen capture stream).
        
        Protocol layout (Decoded from frame 7, 9, 11 of Wireshark capture):
          - Header: 'SC' (0x53, 0x43)
          - Total length: 177 bytes (0x00, 0xB1)
          - Sequence ID (1-254)
          - Action: 0x80 (128)
          - 34 zones x 5 bytes: [start_led, R, G, B, end_led]
          - Checksum byte ((sum of all preceding bytes) % 256)
          - Padded with 0x00 to exactly 192 bytes (3 x 64-byte USB packets)
        
        `colors` can be:
          - A list of 34 RGB tuples (one per zone), OR
          - A list of 63 RGB tuples (one per LED, automatically averaged per zone).
        """
        if not self.is_connected:
            return False

        # If 63 individual LED colors are provided, map them into the 34 zones
        if len(colors) == self.total_leds:
            zone_colors = []
            for s, e in self.DEFAULT_ZONES:
                slice_leds = colors[s - 1 : e]
                if slice_leds:
                    avg_r = sum(c[0] for c in slice_leds) // len(slice_leds)
                    avg_g = sum(c[1] for c in slice_leds) // len(slice_leds)
                    avg_b = sum(c[2] for c in slice_leds) // len(slice_leds)
                    zone_colors.append((avg_r, avg_g, avg_b))
                else:
                    zone_colors.append((0, 0, 0))
        elif len(colors) == len(self.DEFAULT_ZONES):
            zone_colors = colors
        else:
            zone_colors = list(colors[:len(self.DEFAULT_ZONES)])
            while len(zone_colors) < len(self.DEFAULT_ZONES):
                zone_colors.append((0, 0, 0))

        seq = self._next_seq()

        # Build raw Ambilight payload (177 bytes data)
        stream = bytearray(b'SC\x00\xb1')
        stream.append(seq)
        stream.append(self.CMD_SYNC_SCREEN)

        for i, (s, e) in enumerate(self.DEFAULT_ZONES):
            r, g, b = zone_colors[i]
            stream.extend([
                s,
                max(0, min(255, int(r))),
                max(0, min(255, int(g))),
                max(0, min(255, int(b))),
                e
            ])

        # Append checksum
        chk = self._calc_checksum(stream)
        stream.append(chk)

        # Pad to 192 bytes (3 packets of 64 bytes)
        pad_needed = (self.PACKET_SIZE - (len(stream) % self.PACKET_SIZE)) % self.PACKET_SIZE
        if pad_needed > 0:
            stream.extend(b'\x00' * pad_needed)

        # Transmit in 64-byte chunks
        try:
            with self._write_lock:
                if not self._ep_out:
                    return False
                for offset in range(0, len(stream), self.PACKET_SIZE):
                    chunk = stream[offset : offset + self.PACKET_SIZE]
                    self._ep_out.write(bytes(chunk))
            return True
        except usb.core.USBError as e:
            print(f"[LedDriver] Sync frame transfer error: {e}")
            return False


# ---------------------------------------------------------------------------
# Quick Interactive Test when executed directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== Testing LedDriver Standalone ===")
    driver = LedDriver()

    if not driver.connect():
        print("Failed to connect to LED strip controller.")
        exit(1)

    try:
        print("1. Setting brightness to 100%...")
        driver.set_brightness(100)
        time.sleep(0.5)

        colors = [
            ("ROJO", 255, 0, 0),
            ("VERDE", 0, 255, 0),
            ("AZUL", 0, 0, 255),
            ("BLANCO CÁLIDO", 255, 180, 100),
            ("CYAN", 0, 255, 255),
            ("MAGENTA", 255, 0, 255)
        ]

        for name, r, g, b in colors:
            print(f"Setting color: {name} ({r}, {g}, {b})")
            driver.set_solid_color(r, g, b)
            time.sleep(1.0)

        print("Turning off...")
        driver.turn_off()
        time.sleep(0.5)

        print("Test completed successfully!")

    finally:
        driver.disconnect()
