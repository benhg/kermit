"""
@file gps.py
@brief GPS location from gpsd

gpsd owns the receiver and can share it with other programs. We connect to its
JSON socket (default localhost:2947), keep the newest TPV (position) and SKY
(satellites, DOP) reports in a background thread, and hand out the latest fix
as a GpsResponse so the rest of KERMIT does not care where location came from.

Only the Python standard library is used, so no extra dependency is required.
"""

import json
import logging
import socket
import threading
import time

from kermit_sdr.utils import GpsReadQuality, GpsResponse

# A fix older than this is treated as lost (receiver unplugged, gpsd stalled...)
MAX_FIX_AGE_SEC = 3.0

WATCH_COMMAND = b'?WATCH={"enable":true,"json":true}\n'


def gps_response_from_gpsd(tpv, sky=None):
    """
    Convert gpsd TPV (and optionally SKY) reports to a GpsResponse.

    @param tpv - dict from a gpsd TPV report
    @param sky - dict from the most recent gpsd SKY report, or None
    @return GpsResponse, or None if the TPV report has no 2D/3D fix
    """
    if tpv is None or tpv.get("mode", 0) < 2:
        return None
    if tpv.get("lat") is None or tpv.get("lon") is None:
        return None

    # gpsd "status" 2 means DGPS; everything else with a fix is a normal GPS fix
    quality = GpsReadQuality.DGPS if tpv.get("status") == 2 else GpsReadQuality.GPS_SPS

    sat_count = 0
    error = 0
    if sky is not None:
        if sky.get("uSat") is not None:
            sat_count = int(sky["uSat"])
        else:
            sat_count = sum(1 for sat in sky.get("satellites", []) if sat.get("used"))
        # HDOP matches the GGA field the serial reader uses; fall back to PDOP
        dop = sky.get("hdop", sky.get("pdop"))
        if dop is not None:
            error = float(dop)

    altitude = tpv.get("altMSL", tpv.get("alt", 0)) or 0

    return GpsResponse(lat=format(float(tpv["lat"]), ".5f"),
                       lng=format(float(tpv["lon"]), ".5f"),
                       quality=quality,
                       sat_count=sat_count,
                       altitude=altitude,
                       error=error,
                       timestamp=tpv.get("time", ""))


class GpsdSource:
    """
    Reads position reports from gpsd in a background thread.

    Call read() whenever a location is needed; it returns the newest fix
    without blocking.
    """

    def __init__(self, host="127.0.0.1", port=2947, connect_timeout=2.0):
        self.host = host
        self.port = port
        self._lock = threading.Lock()
        self._tpv = None
        self._tpv_received = 0.0
        self._sky = None
        self._running = True
        # Device paths gpsd reports, None until its DEVICES report arrives
        self.devices = None

        self._sock = socket.create_connection((host, port), timeout=connect_timeout)
        self._sock.settimeout(1.0)
        self._sock.sendall(WATCH_COMMAND)
        self._thread = threading.Thread(target=self._reader, name="gpsd-reader", daemon=True)
        self._thread.start()

    def _reader(self):
        buf = b""
        while self._running:
            try:
                chunk = self._sock.recv(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            if not chunk:
                logging.warning("gpsd closed the connection")
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                self._handle_line(line)
        self._running = False

    def _handle_line(self, line):
        try:
            report = json.loads(line)
        except ValueError:
            return
        cls = report.get("class")
        with self._lock:
            if cls == "TPV":
                self._tpv = report
                self._tpv_received = time.monotonic()
            elif cls == "SKY":
                # Newer gpsd sends some SKY reports with only DOP values and
                # others with the satellite list, so merge instead of replacing
                self._sky = {**(self._sky or {}), **report}
            elif cls == "DEVICES":
                self.devices = [d["path"] for d in report.get("devices", []) if d.get("path")]
            elif cls == "DEVICE" and report.get("path"):
                # A receiver was plugged in (activated) or removed (deactivated)
                devices = [d for d in (self.devices or []) if d != report["path"]]
                if report.get("activated"):
                    devices.append(report["path"])
                self.devices = devices

    def is_connected(self):
        return self._running

    def read(self):
        """
        @return the newest GpsResponse, or None if there is no current fix
        """
        with self._lock:
            tpv, sky, received = self._tpv, self._sky, self._tpv_received
        if tpv is None or time.monotonic() - received > MAX_FIX_AGE_SEC:
            return None
        res = gps_response_from_gpsd(tpv, sky)
        if res is not None:
            logging.info(f"Read gpsd fix {res} successfully")
        return res

    def close(self):
        self._running = False
        try:
            self._sock.close()
        except OSError:
            pass
