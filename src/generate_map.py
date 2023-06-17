"""
@file generate_map.py

@brief This file is responsible for generating maps based on CSVs created by the `collect_data.py` file.

Taking a CSV of locations and signal strengths, overlay that onto a map using OpenStreetMap

Heavy inspiration taken from https://python-charts.com/spatial/spatial-heatmap-plotly/
"""

import os

import pandas as pd
import plotly.express as px
import plotly

from config import OUTPUT_FILE_CSV, OUTPUT_FILE_MAP, AUTO_OPEN_MAP


def main():
    """
    Main program entry point
    """
    # Data with latitude/longitude and values
    csv_file = os.path.expandvars(os.path.expanduser(OUTPUT_FILE_CSV))
    map_file = os.path.expandvars(os.path.expanduser(OUTPUT_FILE_MAP))
    df = pd.read_csv(csv_file)

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

    plotly.offline.plot(fig, filename=map_file, auto_open=AUTO_OPEN_MAP)


if __name__ == '__main__':
    main()
