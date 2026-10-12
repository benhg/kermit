import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import urlopen
from urllib.error import HTTPError
from kermit_sdr.bridge import make_handler


class BridgeTests(unittest.TestCase):
    def test_measurement_and_errors(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(lambda: {'field_strength_v_m': None}))
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            base = 'http://127.0.0.1:%s' % server.server_port
            with urlopen(base + '/measurement') as response:
                data = json.load(response)
                self.assertIsNone(data['field_strength_v_m'])
                self.assertIn('timestamp', data)
            with self.assertRaises(HTTPError) as error:
                urlopen(base + '/unknown')
            self.assertEqual(error.exception.code, 404)
            error.exception.close()
        finally:
            server.shutdown()
            server.server_close()
            worker.join()
