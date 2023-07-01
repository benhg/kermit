#!/usr/bin/env python3
"""
This is the entry point to KERMIT. It can be used to collect data and generate maps.

For more details about KERMIT, please see https://github.com/benhg/kermit#readme
"""

import argparse
import logging
import sys

from kermit_sdr.generate_map import main as map_main
from kermit_sdr.collect_data import main as collect_main
from kermit_sdr.version import VERSION


def main():
    """
    The main entry point

    @param args: The arguments namespace from the parser
    """
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        metavar='action',
        type=str,
        help=
        "The action for KERMIT to take. Current options: ['generate-map', 'collect-data', 'version'']",
        choices=["generate-map", "collect-data", "version"])
    parser.add_argument(
        "-o",
        "--output-file",
        type=str,
        required=False,
        help=
        "Provide an output file (for data collection) or both an input and an output file (for map generation). Provide a filename with no extension as KERMIT will add appropriate extensions. This output file overrides the one in the config file."
    )
    args = parser.parse_args()

    if args.action == 'version':
        print(f"KERMIT version {VERSION}")
    elif args.action == "generate-map":
        map_main(args=args)
    elif args.action == "collect-data":
        collect_main(args=args)


if __name__ == '__main__':
    main()
