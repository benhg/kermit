"""Local-network measurement bridge. SDR stays attached to the host.

Run: python -m kermit_sdr.bridge --host 0.0.0.0
Use a trusted private network; no remote control or location upload is exposed.
"""
import argparse
import json
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from kermit_sdr import config


def make_handler(read):
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != '/measurement':
                self.send_error(404)
                return
            try:
                with lock:
                    result = read()
                result['timestamp'] = datetime.now(timezone.utc).isoformat()
                body = json.dumps(result, allow_nan=False).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                self.wfile.write(body)
            except Exception:
                self.send_error(503, 'SDR measurement unavailable')
    return Handler


def main():
    from rtlsdr import RtlSdr
    from kermit_sdr.collect_data import read_measurement
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    sdr = RtlSdr()
    try:
        if config.LISTENING_FREQUENCY <= 3e7:
            sdr.set_direct_sampling(True)
        sdr.sample_rate = config.RtlSdrSettings.sample_rate
        sdr.center_freq = config.RtlSdrSettings.center_freq
        sdr.freq_correction = config.RtlSdrSettings.freq_correction
        sdr.gain = config.RtlSdrSettings.gain
        server = ThreadingHTTPServer((args.host, args.port), make_handler(lambda: read_measurement(sdr)))
        try:
            server.serve_forever()
        finally:
            server.server_close()
    finally:
        sdr.close()


if __name__ == '__main__':
    main()
