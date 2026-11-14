"""
@file generate_map.py

@brief This file is responsible for generating maps based on CSVs created by the `collect_data.py` file.

Taking a CSV of locations and signal strengths, overlay that onto a map using OpenStreetMap

Heavy inspiration taken from https://python-charts.com/spatial/spatial-heatmap-plotly/
"""

import os
import sys
import logging

import pandas as pd
import numpy as np
import plotly.express as px
import plotly

from kermit_sdr.config import OUTPUT_FILE_CSV, OUTPUT_FILE_MAP, AUTO_OPEN_MAP, DEDUPLICATE, DEDUPLICATION_STEP, \
    MAP_SERVER_PORT
from kermit_sdr.map_server import serve_map


def main(args=None):
    """
    Main program entry point

    @param args: arguments from CLI entry point.
        Only supported argument is the output file
    """

    # Decide if the user has supplied their own output file over CLI
    output_file_csv = OUTPUT_FILE_CSV
    output_file_map = OUTPUT_FILE_MAP
    if args is not None:
        if args.output_file is not None and args.output_file != "":
            output_file_map = f"{args.output_file}.html"
            output_file_csv = f"{args.output_file}.csv"

    # Data with latitude/longitude and values
    csv_file = os.path.expandvars(os.path.expanduser(output_file_csv))
    map_file = os.path.expandvars(os.path.expanduser(output_file_map))
    df = pd.read_csv(csv_file)
    df = df.dropna(subset=["latitude", "longitude"])
    metric = getattr(args, "metric", "auto") if args is not None else "auto"
    has_field = "field_strength_v_m" in df and df.field_strength_v_m.notna().any()
    if metric == "v-m" and not has_field:
        raise ValueError("CSV has no calibrated V/m measurements")
    value = "field_strength_v_m" if metric == "v-m" or (metric == "auto" and has_field) else (
        "band_power_dbfs" if "band_power_dbfs" in df else "signal_strength_db")
    df = df.dropna(subset=[value])
    if df.empty:
        raise ValueError("CSV has no located measurements for this metric")
    if DEDUPLICATE:
        df["lat_bin"] = np.floor(df.latitude / DEDUPLICATION_STEP) * DEDUPLICATION_STEP
        df["lon_bin"] = np.floor(df.longitude / DEDUPLICATION_STEP) * DEDUPLICATION_STEP
        df = df.loc[df.groupby(["lat_bin", "lon_bin"])[value].idxmax()]
    label = {"field_strength_v_m": "Estimated RMS field (V/m)",
             "band_power_dbfs": "Band power (dBFS)",
             "signal_strength_db": "Legacy relative level (dB)"}[value]
    # Colored points preserve actual values; density maps sum overlapping levels.
    # Plotly 5.24 added the MapLibre-based scatter_map; scatter_mapbox was
    # deprecated in 6.x and is gone in 7.x. Keep the old call for old Plotly.
    map_args = dict(
        lat="latitude", lon="longitude", color=value,
        labels={value: label}, hover_data=[value],
        center=dict(lat=float(df.latitude.mean()), lon=float(df.longitude.mean())),
        zoom=10, title=label)
    if hasattr(px, "scatter_map"):
        fig = px.scatter_map(df, map_style="open-street-map", **map_args)
    else:
        fig = px.scatter_mapbox(df, mapbox_style="open-street-map", **map_args)

    logging.info(f"Saving map to {map_file}")
    plotly.offline.plot(fig, filename=map_file, auto_open=False)
    if AUTO_OPEN_MAP:
        serve_map(map_file, port=MAP_SERVER_PORT)
    else:
        logging.info("Run 'kermit view-map' (with the same -o, if you used one) to look at it")


def view_map(args=None):
    """
    Serve an existing map without generating it again
    """
    output_file_map = OUTPUT_FILE_MAP
    if args is not None and args.output_file:
        output_file_map = f"{args.output_file}.html"
    map_file = os.path.expandvars(os.path.expanduser(output_file_map))
    if not os.path.isfile(map_file):
        logging.error(f"Map file {map_file} does not exist. Run 'kermit generate-map' first")
        sys.exit(1)
    serve_map(map_file, port=MAP_SERVER_PORT)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
