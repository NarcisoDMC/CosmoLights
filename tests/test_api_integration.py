import unittest
import os
import sys

# Ensure src is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ui.api import CosmoLightsAPI
from src.driver.mock_driver import MockLedDriver
from src.engine.strip_instance import StripInstance


class TestApiMultiStrip(unittest.TestCase):
    def setUp(self):
        self.api = CosmoLightsAPI()

    def test_initialize_has_real_strips_no_fabricated_data(self):
        init_data = self.api.initialize()
        self.assertIn("strips", init_data)
        self.assertIn("active_strip_id", init_data)
        strips = init_data["strips"]
        # Only existing strips (e.g. 1 real strip), no invented strips
        self.assertGreaterEqual(len(strips), 1)
        active_id = init_data["active_strip_id"]
        self.assertTrue(any(s["id"] == active_id for s in strips))

    def test_enumerate_hardware_structure(self):
        hw = self.api.enumerate_hardware()
        self.assertIn("qinheng", hw)
        self.assertIn("serial", hw)
        self.assertIsInstance(hw["qinheng"], list)
        self.assertIsInstance(hw["serial"], list)

    def test_add_and_remove_strip_with_mock_driver(self):
        # Programmatically simulate a detected secondary hardware strip
        mock_driver = MockLedDriver(total_leds=30)
        new_strip = StripInstance(
            strip_id="strip_test_2",
            name="Tira Prueba Secundaria",
            driver=mock_driver,
            config={"selected_monitor": 0, "brightness": 80}
        )
        self.api.orchestrator.add_strip(new_strip)
        strips = self.api.list_strips()
        self.assertTrue(any(s["id"] == "strip_test_2" for s in strips))

        # Switch active strip
        switch_res = self.api.set_active_strip("strip_test_2")
        self.assertTrue(switch_res["success"])
        self.assertEqual(switch_res["active_strip_id"], "strip_test_2")
        self.assertEqual(self.api.active_strip.name, "Tira Prueba Secundaria")

        # Rename strip
        rename_res = self.api.rename_strip("strip_test_2", "Tira Secundaria Renombrada")
        self.assertTrue(rename_res["success"])
        self.assertEqual(rename_res["name"], "Tira Secundaria Renombrada")

        # Remove secondary strip
        remove_res = self.api.remove_strip("strip_test_2")
        self.assertTrue(remove_res["success"])
        strips_after = self.api.list_strips()
        self.assertFalse(any(s["id"] == "strip_test_2" for s in strips_after))


if __name__ == "__main__":
    unittest.main()
