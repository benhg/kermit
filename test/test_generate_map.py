import argparse
import os
import tempfile
import unittest
from unittest import mock

from kermit_sdr import generate_map

CSV = """timestamp,signal_strength_db,signal_strength_s_unit,latitude,longitude,elevation,band_power_dbfs,input_power_dbm,field_strength_v_m,measurement_status,center_frequency_hz,bandwidth_hz
2026-11-13 08:45:38,-30.1,Uncalibrated,43.10770,-77.73780,166.9,-30.1,,,uncalibrated,145230000.0,2048000.0
2026-11-13 08:45:39,-28.4,Uncalibrated,43.10850,-77.73600,166.9,-28.4,,,uncalibrated,145230000.0,2048000.0
2026-11-13 08:45:40,-31.0,Uncalibrated,,,,-31.0,,,uncalibrated,145230000.0,2048000.0
"""


class GenerateMapTests(unittest.TestCase):
    def test_writes_html_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = os.path.join(tmp, "survey")
            with open(base + ".csv", "w") as fh:
                fh.write(CSV)
            with mock.patch.object(generate_map, "AUTO_OPEN_MAP", False):
                generate_map.main(argparse.Namespace(output_file=base, metric="auto"))
            with open(base + ".html") as fh:
                html = fh.read()
            self.assertIn("open-street-map", html)


if __name__ == "__main__":
    unittest.main()
