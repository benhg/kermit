import math
import unittest
from kermit_sdr.measurement import band_power_dbfs, measure


class MeasurementTests(unittest.TestCase):
    def test_complex_power_retains_quadrature(self):
        self.assertAlmostEqual(band_power_dbfs([0.5j] * 16), -6.020599913)

    def test_known_terminal_voltage(self):
        # -30 dBm into 50 ohms => 7.071 mVrms, AF 20 dB/m => 70.71 mV/m.
        result = measure([1j] * 32, 145e6, 2e6, -30, 20)
        self.assertAlmostEqual(result['field_strength_v_m'], math.sqrt(50e-6) * 10)
        self.assertEqual(result['measurement_status'], 'calibrated_estimate')

    def test_cable_loss(self):
        first = measure([1], 145e6, 2e6, -30, 20)
        second = measure([1], 145e6, 2e6, -30, 20, 6.020599913)
        self.assertAlmostEqual(second['field_strength_v_m'], first['field_strength_v_m'] * 2)

    def test_no_fabricated_field_without_calibration(self):
        for offset, factor in [(None, None), (-30, None), (None, 20)]:
            result = measure([1], 145e6, 2e6, offset, factor)
            self.assertIsNone(result['field_strength_v_m'])
            self.assertEqual(result['measurement_status'], 'uncalibrated')

    def test_broad_power_includes_all_samples(self):
        self.assertAlmostEqual(band_power_dbfs([1, 0]), 10 * math.log10(0.5))

    def test_invalid_inputs(self):
        for samples in [[], [complex(float('nan'), 0)], [float('inf')]]:
            with self.assertRaises(ValueError): band_power_dbfs(samples)
        with self.assertRaises(ValueError): measure([1], 145e6, 0)
        with self.assertRaises(ValueError): measure([1], 145e6, 2e6, float('nan'), 20)

    def test_silence_serializable(self):
        self.assertEqual(band_power_dbfs([0]), -300)


if __name__ == '__main__':
    unittest.main()
