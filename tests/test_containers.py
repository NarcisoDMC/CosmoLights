"""
test_containers.py - Unit tests for Phase 2 StripInstance and Multi-Strip Orchestrator.

Uses synthetic in-memory frames and mock drivers to test multi-strip orchestration,
autonomous mode transitions, shared capture pool optimization, and master controls
without requiring physical hardware or DirectX GPUs.
"""

import unittest
import time
from typing import Tuple, Optional
import numpy as np

from src.capture.base import BaseCapture
from src.driver.mock_driver import MockLedDriver
from src.engine.strip_instance import StripInstance
from src.engine.orchestrator import StripOrchestrator, CapturePool


class MockCapture(BaseCapture):
    """Synthetic in-memory screen capture provider for unit testing."""

    def __init__(self, output_idx: int = 0):
        self.output_idx = output_idx
        self._active = False
        self.frame_count = 0

    def start(self, target_fps: int = 60) -> bool:
        self._active = True
        return True

    def stop(self) -> None:
        self._active = False

    def grab_frame(self) -> Optional[np.ndarray]:
        if not self._active:
            return None
        self.frame_count += 1
        # Generates a synthetic 120x240 RGB frame with distinct borders
        frame = np.zeros((120, 240, 3), dtype=np.uint8)
        # Top border: Green
        frame[0:20, :, 1] = 200
        # Left border: Red
        frame[:, 0:30, 0] = 220
        # Right border: Blue
        frame[:, 210:240, 2] = 240
        return frame

    @property
    def resolution(self) -> Tuple[int, int]:
        return (240, 120)

    @property
    def is_active(self) -> bool:
        return self._active


class TestStripInstance(unittest.TestCase):
    """Tests autonomous control, mode transitions, and calibration of StripInstance."""

    def setUp(self):
        self.driver = MockLedDriver("test_strip_1", total_leds=63)
        self.capture = MockCapture(output_idx=0)
        self.strip = StripInstance(
            strip_id="strip_1",
            name="Monitor Principal",
            driver=self.driver,
            capture=self.capture,
            config={"brightness": 100, "black_cutoff": 15, "gamma": 2.0}
        )

    def tearDown(self):
        self.strip.turn_off()

    def test_initial_state(self):
        self.assertEqual(self.strip.strip_id, "strip_1")
        self.assertEqual(self.strip.name, "Monitor Principal")
        self.assertEqual(self.strip.mode, "off")
        self.assertEqual(self.strip.brightness, 100)

    def test_set_solid_color_mode(self):
        success = self.strip.set_solid_color(255, 128, 0)
        self.assertTrue(success)
        self.assertEqual(self.strip.mode, "solid")
        self.assertEqual(self.driver.last_solid_color, (255, 128, 0))
        self.assertEqual(self.driver.last_frame[0], (255, 128, 0))

    def test_brightness_scaling_on_solid(self):
        self.strip.set_solid_color(200, 100, 50)
        self.strip.set_brightness(50)  # 50%
        self.assertEqual(self.strip.brightness, 50)
        # Scaled values: 200*0.5=100, 100*0.5=50, 50*0.5=25
        self.assertEqual(self.driver.last_frame[0], (100, 50, 25))

    def test_effect_mode(self):
        success = self.strip.set_effect("breath_pulse", speed=1.5)
        self.assertTrue(success)
        self.assertEqual(self.strip.mode, "effect")
        self.assertTrue(self.strip.effects.is_running)

        # Allow effect thread to produce at least 1 frame
        time.sleep(0.08)
        self.assertGreater(self.driver.frame_count, 0)

        self.strip.turn_off()
        self.assertEqual(self.strip.mode, "off")
        self.assertFalse(self.strip.effects.is_running)

    def test_ambilight_streaming_mode(self):
        success = self.strip.start_ambilight()
        self.assertTrue(success)
        self.assertEqual(self.strip.mode, "ambilight")
        self.assertTrue(self.strip.engine.is_running)

        # Allow Ambilight streaming loop to process synthetic frames
        time.sleep(0.12)
        self.assertGreater(self.driver.frame_count, 0)
        self.assertGreater(self.capture.frame_count, 0)

        self.strip.stop_ambilight()
        self.assertEqual(self.strip.mode, "off")
        self.assertFalse(self.strip.engine.is_running)

    def test_telemetry_snapshot(self):
        self.strip.set_solid_color(0, 255, 128)
        state = self.strip.get_state()

        self.assertEqual(state["id"], "strip_1")
        self.assertEqual(state["mode"], "solid")
        self.assertEqual(state["brightness"], 100)
        self.assertEqual(state["driver"]["type"], "mock")
        self.assertEqual(len(state["led_preview"]), 34)
        self.assertEqual(state["led_preview"][0], [0, 255, 128])


class TestCapturePoolOptimization(unittest.TestCase):
    """Verifies that multiple strips targeting the same display share a single capture instance."""

    def setUp(self):
        self.created_instances = []

        def mock_factory(out_idx: int) -> BaseCapture:
            cap = MockCapture(out_idx)
            self.created_instances.append(cap)
            return cap

        self.pool = CapturePool(capture_factory=mock_factory)

    def test_shared_capture_same_monitor(self):
        cap_1 = self.pool.acquire(0)
        cap_2 = self.pool.acquire(0)

        # Both must point to the identical capture instance
        self.assertIs(cap_1, cap_2)
        self.assertEqual(self.pool.get_active_count(), 1)
        self.assertEqual(len(self.created_instances), 1)

    def test_distinct_capture_different_monitors(self):
        cap_mon_0 = self.pool.acquire(0)
        cap_mon_1 = self.pool.acquire(1)

        self.assertIsNot(cap_mon_0, cap_mon_1)
        self.assertEqual(self.pool.get_active_count(), 2)
        self.assertEqual(len(self.created_instances), 2)

    def test_reference_counting_cleanup(self):
        self.pool.acquire(0)
        self.pool.acquire(0)
        self.assertEqual(self.pool.get_active_count(), 1)

        self.pool.release(0)
        self.assertEqual(self.pool.get_active_count(), 1)  # 1 strip still uses it

        self.pool.release(0)
        self.assertEqual(self.pool.get_active_count(), 0)  # All released, cleaned up


class TestStripOrchestrator(unittest.TestCase):
    """Verifies master management, multi-strip isolation, and aggregated controls."""

    def setUp(self):
        self.orchestrator = StripOrchestrator(capture_factory=lambda idx: MockCapture(idx))

        self.driver_1 = MockLedDriver("strip_1")
        self.driver_2 = MockLedDriver("strip_2")
        self.driver_3 = MockLedDriver("strip_3")

        self.strip_1 = StripInstance("strip_1", "Monitor 1", self.driver_1, config={"selected_monitor": 0})
        self.strip_2 = StripInstance("strip_2", "Monitor 2", self.driver_2, config={"selected_monitor": 1})
        self.strip_3 = StripInstance("strip_3", "Desk Ambient", self.driver_3, config={"selected_monitor": 0})

        self.orchestrator.add_strip(self.strip_1)
        self.orchestrator.add_strip(self.strip_2)
        self.orchestrator.add_strip(self.strip_3)

    def tearDown(self):
        self.orchestrator.turn_off_all()

    def test_registration_and_active_strip(self):
        self.assertEqual(self.orchestrator.active_strip_id, "strip_1")
        strips = self.orchestrator.list_strips()
        self.assertEqual(len(strips), 3)

        self.assertTrue(self.orchestrator.set_active_strip("strip_2"))
        self.assertEqual(self.orchestrator.active_strip_id, "strip_2")

    def test_multi_strip_concurrent_modes(self):
        # Strip 1: Ambilight
        self.strip_1.start_ambilight()
        # Strip 2: Solid Cyan
        self.strip_2.set_solid_color(0, 240, 255)
        # Strip 3: Effect (dynamic wave)
        self.strip_3.set_effect("dynamic_wave")

        time.sleep(0.08)

        # Verify all 3 strips are running their own mode simultaneously
        self.assertEqual(self.strip_1.mode, "ambilight")
        self.assertEqual(self.strip_2.mode, "solid")
        self.assertEqual(self.strip_3.mode, "effect")

        self.assertTrue(self.strip_1.engine.is_running)
        self.assertEqual(self.driver_2.last_solid_color, (0, 240, 255))
        self.assertTrue(self.strip_3.effects.is_running)

    def test_master_turn_off(self):
        self.strip_1.set_solid_color(255, 0, 0)
        self.strip_2.set_solid_color(0, 255, 0)
        self.strip_3.set_solid_color(0, 0, 255)

        self.orchestrator.turn_off_all()

        self.assertEqual(self.strip_1.mode, "off")
        self.assertEqual(self.strip_2.mode, "off")
        self.assertEqual(self.strip_3.mode, "off")

        self.assertTrue(self.driver_1.is_turned_off)
        self.assertTrue(self.driver_2.is_turned_off)
        self.assertTrue(self.driver_3.is_turned_off)

    def test_master_brightness(self):
        self.orchestrator.set_master_brightness(45)
        self.assertEqual(self.strip_1.brightness, 45)
        self.assertEqual(self.strip_2.brightness, 45)
        self.assertEqual(self.strip_3.brightness, 45)

    def test_get_all_states(self):
        all_states = self.orchestrator.get_all_states()
        self.assertEqual(all_states["total_strips"], 3)
        self.assertIn("strip_1", all_states["strips"])
        self.assertIn("strip_2", all_states["strips"])
        self.assertIn("strip_3", all_states["strips"])


if __name__ == "__main__":
    unittest.main()
