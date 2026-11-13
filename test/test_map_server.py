import os
import socket
import tempfile
import threading
import unittest
from urllib.request import urlopen

from kermit_sdr.map_server import make_map_server


class MapServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.map_file = os.path.join(self.tmp.name, "my survey.html")
        with open(self.map_file, "w") as fh:
            fh.write("<html>map</html>")

    def tearDown(self):
        self.tmp.cleanup()

    def fetch(self, server, url):
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with urlopen(url) as response:
                return response.read().decode()
        finally:
            server.shutdown()
            server.server_close()
            worker.join()

    def test_serves_map_on_localhost(self):
        server, url = make_map_server(self.map_file, port=0)
        self.assertTrue(url.startswith("http://127.0.0.1:"))
        self.assertTrue(url.endswith("/my%20survey.html"))
        self.assertEqual(self.fetch(server, url), "<html>map</html>")

    def test_falls_back_when_port_is_taken(self):
        busy = socket.socket()
        busy.bind(("127.0.0.1", 0))
        busy.listen(1)
        taken = busy.getsockname()[1]
        try:
            server, url = make_map_server(self.map_file, port=taken)
            self.assertNotEqual(server.server_port, taken)
            self.assertEqual(self.fetch(server, url), "<html>map</html>")
        finally:
            busy.close()

    def test_missing_map(self):
        with self.assertRaises(FileNotFoundError):
            make_map_server(os.path.join(self.tmp.name, "nope.html"))


if __name__ == "__main__":
    unittest.main()
