import json
import socket
import threading
import time
import unittest

from kermit_sdr.gps import GpsdSource, gps_response_from_gpsd
from kermit_sdr.utils import GpsReadQuality

TPV_3D = {"class": "TPV", "device": "/dev/ttyACM0", "mode": 3, "status": 1,
          "time": "2026-11-13T13:42:14.000Z", "lat": 43.1077, "lon": -77.7378,
          "altHAE": 98.45, "altMSL": 132.6}
SKY = {"class": "SKY", "device": "/dev/ttyACM0", "hdop": 1.2, "pdop": 2.1, "uSat": 7,
       "satellites": []}
DEVICES = {"class": "DEVICES", "devices": [{"class": "DEVICE", "path": "/dev/ttyACM0"}]}


class ConversionTests(unittest.TestCase):
    def test_3d_fix(self):
        res = gps_response_from_gpsd(TPV_3D, SKY)
        self.assertEqual(res.lat, "43.10770")
        self.assertEqual(res.lng, "-77.73780")
        self.assertEqual(res.altitude, 132.6)
        self.assertEqual(res.sat_count, 7)
        self.assertEqual(res.error, 1.2)
        self.assertEqual(res.quality, GpsReadQuality.GPS_SPS)
        self.assertTrue(res.is_valid_read())

    def test_no_fix(self):
        self.assertIsNone(gps_response_from_gpsd({"class": "TPV", "mode": 1}, SKY))
        self.assertIsNone(gps_response_from_gpsd(None))

    def test_dgps_and_satellite_count_without_usat(self):
        sky = {"class": "SKY", "pdop": 3.0,
               "satellites": [{"used": True}, {"used": True}, {"used": True}, {"used": False}]}
        res = gps_response_from_gpsd(dict(TPV_3D, status=2), sky)
        self.assertEqual(res.quality, GpsReadQuality.DGPS)
        self.assertEqual(res.sat_count, 3)
        self.assertEqual(res.error, 3.0)

    def test_without_sky_is_not_valid(self):
        res = gps_response_from_gpsd(TPV_3D, None)
        self.assertIsNotNone(res)
        self.assertFalse(res.is_valid_read())


class FakeGpsd:
    """A one-client gpsd stand-in that answers WATCH with the given reports"""

    def __init__(self, reports, delay=0.0):
        self.reports = reports
        self.delay = delay
        self.server = socket.socket()
        self.server.bind(("127.0.0.1", 0))
        self.server.listen(1)
        self.port = self.server.getsockname()[1]
        self.watch = None
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self):
        conn, _ = self.server.accept()
        with conn:
            self.watch = conn.recv(1024)
            # A real gpsd that was idle reopens the receiver before answering
            time.sleep(self.delay)
            for report in self.reports:
                conn.sendall(json.dumps(report).encode() + b"\n")
            time.sleep(2)

    def close(self):
        self.server.close()


class GpsdSourceTests(unittest.TestCase):
    def wait_for(self, predicate):
        for _ in range(50):
            if predicate():
                return True
            time.sleep(0.02)
        return False

    def test_reads_latest_fix(self):
        fake = FakeGpsd([{"class": "VERSION"}, DEVICES, SKY, TPV_3D])
        gpsd = GpsdSource("127.0.0.1", fake.port)
        try:
            self.assertTrue(self.wait_for(lambda: gpsd.read() is not None))
            self.assertEqual(gpsd.devices, ["/dev/ttyACM0"])
            self.assertIn(b"?WATCH=", fake.watch)
            res = gpsd.read()
            self.assertEqual(res.lat, "43.10770")
            self.assertTrue(res.is_valid_read())
        finally:
            gpsd.close()
            fake.close()

    def test_partial_sky_reports_are_merged(self):
        dop_only = {"class": "SKY", "device": "/dev/ttyACM0", "pdop": 2.1}
        fake = FakeGpsd([DEVICES, SKY, dop_only, TPV_3D])
        gpsd = GpsdSource("127.0.0.1", fake.port)
        try:
            self.assertTrue(self.wait_for(lambda: gpsd.read() is not None))
            res = gpsd.read()
            self.assertEqual(res.sat_count, 7)
            self.assertEqual(res.error, 1.2)
            self.assertTrue(res.is_valid_read())
        finally:
            gpsd.close()
            fake.close()

    def test_no_devices(self):
        fake = FakeGpsd([{"class": "VERSION"}, {"class": "DEVICES", "devices": []}])
        gpsd = GpsdSource("127.0.0.1", fake.port)
        try:
            self.assertTrue(self.wait_for(lambda: gpsd.devices is not None))
            self.assertEqual(gpsd.devices, [])
            self.assertIsNone(gpsd.read())
        finally:
            gpsd.close()
            fake.close()

    def test_connection_refused(self):
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        with self.assertRaises(OSError):
            GpsdSource("127.0.0.1", port)


class SetupGpsdTests(unittest.TestCase):
    def setup_with(self, fake):
        from unittest import mock
        from kermit_sdr import collect_data
        with mock.patch.object(collect_data, "GPSD_HOST", "127.0.0.1"), \
             mock.patch.object(collect_data, "GPSD_PORT", fake.port), \
             mock.patch.object(collect_data, "GPS_POLL_SEC", 2):
            return collect_data.setup_gpsd_source()

    def test_waits_for_slow_device_list(self):
        # gpsd took 2.1 s on a real system after it had closed the receiver
        fake = FakeGpsd([{"class": "VERSION"}, DEVICES, SKY, TPV_3D], delay=2.5)
        try:
            gpsd = self.setup_with(fake)
            self.assertIsNotNone(gpsd)
            self.assertEqual(gpsd.devices, ["/dev/ttyACM0"])
            gpsd.close()
        finally:
            fake.close()

    def test_no_receiver_falls_back(self):
        fake = FakeGpsd([{"class": "VERSION"}, {"class": "DEVICES", "devices": []}])
        try:
            self.assertIsNone(self.setup_with(fake))
        finally:
            fake.close()


if __name__ == "__main__":
    unittest.main()
