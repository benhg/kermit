"""
@file map_server.py
@brief Serve a generated map over http://127.0.0.1 and open it in the browser

Plotly 6+ draws maps with MapLibre. Browsers do not let MapLibre start its
background worker for pages opened from disk (file://), so the measurement
points never show up. Served over HTTP the same file works, so KERMIT runs a
small web server for it.

The server only listens on 127.0.0.1, so other machines on the network cannot
reach it. It serves the directory the map is in (that includes the survey CSV).
"""

import functools
import logging
import os
import urllib.parse
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        logging.debug("map server: " + format % args)


def make_map_server(map_file, port=8000):
    """
    Create (but do not start) a server for map_file.

    @param map_file - path to the .html map
    @param port - preferred port; if it is taken, a free one is used instead
    @return (server, url)
    """
    map_file = os.path.abspath(os.path.expanduser(map_file))
    if not os.path.isfile(map_file):
        raise FileNotFoundError(f"Map file {map_file} does not exist")
    directory, name = os.path.split(map_file)
    handler = functools.partial(_QuietHandler, directory=directory)
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    except OSError:
        logging.info(f"Port {port} is in use, picking a free one")
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    url = f"http://127.0.0.1:{server.server_port}/{urllib.parse.quote(name)}"
    return server, url


def serve_map(map_file, port=8000, open_browser=True):
    """
    Serve map_file until ctrl-C, optionally opening it in the browser first.
    """
    server, url = make_map_server(map_file, port)
    logging.info(f"Map is available at {url}")
    logging.info("Press ctrl-C to stop the map server")
    if open_browser:
        try:
            if not webbrowser.open(url):
                logging.info("Could not open a browser, please open the address above yourself")
        except webbrowser.Error:
            logging.info("Could not open a browser, please open the address above yourself")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        logging.info("Map server stopped")
