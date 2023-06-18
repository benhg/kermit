"""
@file generate_map.py

@brief This file is responsible for generating maps based on CSVs created by the `collect_data.py` file.

Taking a CSV of locations and signal strengths, overlay that onto a map using OpenStreetMap

Heavy inspiration taken from https://python-charts.com/spatial/spatial-heatmap-plotly/
"""

import os
import logging

import pandas as pd
import numpy as np
import plotly.express as px
import plotly

from config import OUTPUT_FILE_CSV, OUTPUT_FILE_MAP, AUTO_OPEN_MAP, DEDUPLICATE, DEDUPLICATION_STEP


def main():
    """
    Main program entry point
    """

    # Data with latitude/longitude and values
    csv_file = os.path.expandvars(os.path.expanduser(OUTPUT_FILE_CSV))
    map_file = os.path.expandvars(os.path.expanduser(OUTPUT_FILE_MAP))
    df = pd.read_csv(csv_file)
    logging.info(f"Found {len(df['latitude'])} data points")
    if DEDUPLICATE:
        # Bin all the points into groups of 11-meter segments (4 decimal digits)
        # Take the max signal strength of each bin
        # Those are our deduplicated data points
        summary_points = []
        step = DEDUPLICATION_STEP
        to_bin = lambda x: np.floor(x / DEDUPLICATION_STEP
                                    ) * DEDUPLICATION_STEP
        df["lat_bin"] = to_bin(df.latitude)
        df["lon_bin"] = to_bin(df.longitude)
        groups = df.groupby(["lat_bin", "lon_bin"])
        for group in groups:
            lat = group[0][0]
            lon = group[0][1]
            signal_str_db = np.max(group[1].signal_strength_db)
            summary_points.append({
                "latitude": lat,
                "longitude": lon,
                "signal_strength_db": signal_str_db
            })

        df = pd.DataFrame(summary_points)
        logging.info(
            f"Found {len(df['latitude'])} data points after deduplication")

    fig = px.density_mapbox(
        df,
        lat='latitude',
        lon='longitude',
        z='signal_strength_db',
        radius=8,
        # Center at the first entry
        center=dict(lat=df["latitude"][1], lon=df["longitude"][1]),
        zoom=10,
        mapbox_style='open-street-map')

    logging.info(f"Saving map to {map_file}")
    plotly.offline.plot(fig, filename=map_file, auto_open=AUTO_OPEN_MAP)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
