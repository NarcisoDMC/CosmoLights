"""
test_drivers.py - Unit tests for Phase 1 Driver Abstraction & Multi-Strip Support.

Uses simulated in-memory data to verify protocol packets, checksums,
zone mappings, and multi-device isolation without requiring physical hardware.
"""

import unittest
from typing import List, Tuple

from src.driver.base_driver import BaseLedDriver
from src.driver.mock_driver import MockLedDriver
from src.driver.serial_driver import SerialLedDriver
from src.driver.led_driver import LedDriver, QinHengDriver


class TestMockLedDriver(unittest.TestCase):
    """Verifies that MockLedDriver adheres to BaseLedDriver contract and records data."""

    def setUp(self):
        self.driver = MockLedDriver(device_id="strip_desk", total_leds=63)

    def test_implements_base_interface(self):
        self.assertIsInstance(self.driver, BaseLedDriver)
        self.assertEqual(self.driver.driver_type, "mock")

    def test_connection_lifecycle(self):
        self.assertFalse(self.driver.is_connected)
        self.assertTrue(self.driver.connect())
        self.assertTrue(self.driver.is_connected)
        self.driver.disconnect()
        self.assertFalse(self.driver.is_connected)

    def test_sync_screen_frame(self):
        self.driver.connect()
        test_frame = [(255, 0, 0)] * 34
        success = self.driver.sync_screen_frame(test_frame)
        self.assertTrue(success)
        self.assertEqual(self.driver.frame_count, 1)
        self.assertEqual(self.driver.last_frame, test_frame)

    def test_set_solid_color(self):
        self.driver.connect()
        success = self.driver.set_solid_color(0, 128, 255)
        self.assertTrue(success)
        self.assertEqual(self.driver.last_solid_color, (0, 128, 255))
        self.assertEqual(len(self.driver.last_frame), 63)
        self.assertEqual(self.driver.last_frame[0], (0, 128, 255))

    def test_turn_off(self):
        self.driver.connect()
        self.driver.set_solid_color(255, 255, 255)
        self.assertFalse(self.driver.is_turned_off)
        self.driver.turn_off()
        self.assertTrue(self.driver.is_turned_off)
        self.assertEqual(self.driver.last_frame[0], (0, 0, 0))


class TestSerialAdalightProtocol(unittest.TestCase):
    """Verifies the standard Adalight binary streaming protocol used by Arduino/ESP32."""

    def test_adalight_packet_structure_63_leds(self):
        num_leds = 63
        test_colors = [(i % 255, (i * 2) % 255, (i * 3) % 255) for i in range(num_leds)]
        packet = SerialLedDriver.build_adalight_packet(test_colors, num_leds)

        # Header check: 'Ada' (0x41, 0x64, 0x61)
        self.assertEqual(packet[:3], b"Ada")

        # Count check
        count = num_leds - 1
        hi = (count >> 8) & 0xFF
        lo = count & 0xFF
        chk = hi ^ lo ^ 0x55
        self.assertEqual(packet[3], hi)
        self.assertEqual(packet[4], lo)
        self.assertEqual(packet[5], chk)

        # Total byte length: 6 header bytes + 63 * 3 RGB bytes = 195 bytes
        self.assertEqual(len(packet), 6 + (num_leds * 3))

        # Payload check for first LED
        self.assertEqual(packet[6], test_colors[0][0])
        self.assertEqual(packet[7], test_colors[0][1])
        self.assertEqual(packet[8], test_colors[0][2])

    def test_adalight_auto_padding_when_input_shorter(self):
        num_leds = 30
        short_colors = [(255, 255, 255)] * 10
        packet = SerialLedDriver.build_adalight_packet(short_colors, num_leds)

        self.assertEqual(len(packet), 6 + (30 * 3))
        # The 20th LED should be padded with (0,0,0)
        idx_20 = 6 + (20 * 3)
        self.assertEqual(packet[idx_20 : idx_20 + 3], b"\x00\x00\x00")


class TestQinHengProtocol(unittest.TestCase):
    """Verifies QinHeng (1A86:FE07) binary packet generation, zone mapping, and checksums."""

    def setUp(self):
        self.driver = LedDriver(total_leds=63, device_index=0)

    def test_checksum_algorithm(self):
        sample_data = bytes([0x52, 0x42, 0x01, 0x80, 0xFF, 0x00, 0xAA])
        expected = sum(sample_data) % 256
        self.assertEqual(LedDriver._calc_checksum(sample_data), expected)

    def test_multi_device_targeting_metadata(self):
        driver_0 = LedDriver(device_index=0)
        driver_1 = LedDriver(device_index=1, bus=2, address=5)

        self.assertEqual(driver_0.device_index, 0)
        self.assertEqual(driver_1.device_index, 1)
        self.assertEqual(driver_1.device_info["bus"], 2)
        self.assertEqual(driver_1.device_info["address"], 5)
        self.assertEqual(driver_0.driver_type, "qinheng")
        self.assertIs(QinHengDriver, LedDriver)

    def test_rb_command_packet_structure(self):
        # Action 0x86 (SET_SECTION_LED) with sample params
        action = LedDriver.CMD_SET_SECTION_LED
        params = [1, 255, 128, 0, 63]

        seq = self.driver._next_seq()
        packet = bytearray(b"RB")
        packet.append(seq)
        packet.append(action)
        packet.extend(params)
        chk = LedDriver._calc_checksum(packet)
        packet.append(chk)

        # Must be padded to exactly 64 bytes
        if len(packet) < LedDriver.PACKET_SIZE:
            packet.extend(b"\x00" * (LedDriver.PACKET_SIZE - len(packet)))

        self.assertEqual(len(packet), 64)
        self.assertEqual(packet[:2], b"RB")
        self.assertEqual(packet[2], seq)
        self.assertEqual(packet[3], action)
        self.assertEqual(packet[4:9], bytes(params))

    def test_sync_screen_frame_packet_size(self):
        # 34 zones covering 63 LEDs
        zones_34 = [(i * 7, (255 - i * 7), 128) for i in range(34)]

        seq = self.driver._next_seq()
        stream = bytearray(b"SC\x00\xb1")
        stream.append(seq)
        stream.append(LedDriver.CMD_SYNC_SCREEN)

        for i, (s, e) in enumerate(LedDriver.DEFAULT_ZONES):
            r, g, b = zones_34[i]
            stream.extend([s, int(r), int(g), int(b), e])

        chk = LedDriver._calc_checksum(stream)
        stream.append(chk)

        # Must pad to 192 bytes (3 packets of 64 bytes)
        pad_needed = (LedDriver.PACKET_SIZE - (len(stream) % LedDriver.PACKET_SIZE)) % LedDriver.PACKET_SIZE
        stream.extend(b"\x00" * pad_needed)

        self.assertEqual(len(stream), 192)
        self.assertEqual(stream[:2], b"SC")
        self.assertEqual(stream[5], LedDriver.CMD_SYNC_SCREEN)


class TestMultiStripIsolation(unittest.TestCase):
    """Verifies that multiple drivers operate concurrently without state collision."""

    def test_two_independent_strips(self):
        strip_monitor_1 = MockLedDriver(device_id="strip_1", total_leds=63)
        strip_monitor_2 = MockLedDriver(device_id="strip_2", total_leds=63)

        self.assertTrue(strip_monitor_1.connect())
        self.assertTrue(strip_monitor_2.connect())

        # Send distinct colors
        frame_1 = [(255, 0, 0)] * 34  # Red for Monitor 1
        frame_2 = [(0, 0, 255)] * 34  # Blue for Monitor 2

        strip_monitor_1.sync_screen_frame(frame_1)
        strip_monitor_2.sync_screen_frame(frame_2)

        # Check isolation
        self.assertEqual(strip_monitor_1.last_frame[0], (255, 0, 0))
        self.assertEqual(strip_monitor_2.last_frame[0], (0, 0, 255))
        self.assertEqual(strip_monitor_1.device_id, "strip_1")
        self.assertEqual(strip_monitor_2.device_id, "strip_2")

        # Turn off strip 1 only
        strip_monitor_1.turn_off()
        self.assertTrue(strip_monitor_1.is_turned_off)
        self.assertFalse(strip_monitor_2.is_turned_off)


if __name__ == "__main__":
    unittest.main()
