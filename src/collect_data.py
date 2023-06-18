"""
@file collect_data.py

@brief this file is responsible for collecting RF background levels

At a high-level:

With some frequency defined in a config file:
- Sample the current signal coming in from the line-in or an RTLSDR
 (we assume this is a radio)
- Translate to S-units (extended s-unit scale)
- Collect lat, lng, elevation
- Create a row in an output CSV
- Announce out loud the S-level so the user can slow down

This assumes you have set up an actual radio as an input to the computer, and it works correctly. In future, an example setup will be added to the README
"""

# https://stackoverflow.com/questions/40138031/how-to-read-realtime-microphone-audio-volume-in-python-and-ffmpeg-or-similar (mic audio level)
# https://python.plainenglish.io/receiving-and-processing-gps-data-using-external-receiver-with-python-24d3592ad2e0 (gps recv)

import platform
import time
import atexit
import numpy as np
import subprocess
import logging
import csv
import os
import datetime
import sys

from rtlsdr import RtlSdr
import serial
from serial.tools import list_ports

from config import SAMPLE_INTERVAL, SignalSource, SIGNAL_SOURCE, RtlSdrSettings, ANTENNA_FUDGE_FACTOR,\
                   LISTENING_FREQUENCY, ANNOUNCE_SIGNAL, ANNOUNCE_SIGNAL_EVERY, S_UNIT_SCALE, GPS_POLL_SEC,\
                   OUTPUT_FILE_CSV, DEDUPLICATE
from utils import get_platform_speak_func, GpsReadQuality, GpsResponse
"""
If we don't find a GPS, still announce signal but don't store location data
"""
store_location = True
"""
The shape of the output CSV file
"""
CSV_COLUMNS = [
    "timestamp", "signal_strength_db", "signal_strength_s_unit", "latitude",
    "longitude", "elevation"
]


def get_s_unit_from_db(signal_strength_db):
    """
    Get the S-unit of a signal given it's strength in dB

    @param signal_strength_db: The signal strength in dB
    """
    for key, interval in S_UNIT_SCALE.items():
        if interval.in_interval(signal_strength_db):
            logging.debug(
                f"Signal strength {signal_strength_db} corresponds to {key}")
            return key
    return "Unknown S-unit"


def dbfft(x, fs, win=None, ref=1):
    """
    Calculate spectrum in dB scale
    Args:
        x: input signal
        fs: sampling frequency
        win: vector containing window samples (same length as x).
             If not provided, then rectangular window is used by default.
        ref: reference value used for dBFS scale. 32768 for int16 and 1 for float

    Returns:
        freq: frequency vector
        s_db: spectrum in dB scale
    """

    N = len(x)  # Length of input sequence

    if win is None:
        win = np.ones([N, 1])
    if len(x) != len(win):
        raise ValueError('Signal and window must be of the same length')
    x = x * win

    # Calculate real FFT and frequency vector
    sp = np.fft.rfft(x)
    freq = np.arange((N / 2) + 1) / (float(N) / fs)

    # Scale the magnitude of FFT by window and factor of 2,
    # because we are using half of FFT spectrum.
    s_mag = np.abs(sp) * 2 / np.sum(win)

    # Convert to dBFS
    s_dbfs = 20 * np.log10(s_mag / ref)

    return freq, s_dbfs


def read_signal_str(sdr):
    """
    Read the signal strength out from our signal source

    @param sdr - the RTLSDR object, if we're using the RTLSDR
                 None if we're not
    """
    if sdr:
        # this is TOO EASY
        logging.debug(
            f"Reading signal samples from RTLSDR at sample rate {RtlSdrSettings.sample_rate}"
        )
        samples = sdr.read_samples(1024)
    else:
        #collect_samples_from_line_in()
        pass

    # Once we have some samples of the signal, we can extract the power
    freq, dbfs = dbfft(samples, RtlSdrSettings.sample_rate)
    logging.debug(
        f"Signal sample summary: min - {np.min(dbfs)}, max: - {np.max(dbfs)}, average - {np.average(dbfs)}"
    )
    # TODO - instead of doing the max, we really should specifically take the listening frequency
    # Or something like the range of the antenna's useful frequencies (requires user config input)
    # But for almost all practical intents and purposes, the max _is_ the listening frequency
    max_db = np.max(dbfs)
    logging.debug(
        f"Shifting measured signal {max_db} by antenna gain {ANTENNA_FUDGE_FACTOR}"
    )
    db_result = max_db - ANTENNA_FUDGE_FACTOR
    return db_result


def announce_signal(signal_strength_s_unit, speak_func):
    """
    Announce the signal strength using system text to speech
    
    @param signal_strength_db: Signal strength in dB
    @param speak_func: speak function to use for announcin strength
    """
    speak_func(signal_strength_s_unit)


def get_gga_signal_from_serial(serial_obj):
    """
    Given a GPS serial object, decode the GGA signal, and return relevant information

    @param serial_obj - a serial object that is a GPS unit
    @return - timestamp, lat, lng, quality, number of satellites, altitude
    """
    line = serial_obj.readline().decode('utf-8')
    # Only use GPGGA signal type
    line_found = False
    while not line_found:
        if "GPGGA" in line:
            logging.debug("Found GPGGA signal from GPS unit")
            line_found = True
            line_split = line.split(",")
            if int(line_split[6]) == 0:
                return None
            break
        line = serial_obj.readline().decode('utf-8')

    # Process the GPGGA signal, return the serial object
    # The GPGGA signal is well-defined (for decades),
    # so we can be a bit hacky here and get away with it.
    line_split = line.split(",")
    res = GpsResponse(timestamp=line_split[1],
                      quality=GpsReadQuality(int(line_split[6])),
                      sat_count=int(line_split[7]),
                      altitude=float(line_split[9]),
                      error=float(line_split[8]))

    # Converting the degrees from NMEA to decimal is kind of annoying
    # The format is "ddmm.mmm" for latitude, and
    # "dddmm.mmmmm" for longitude
    # Direction is encoded in the next entry
    lat = line_split[2]
    lat_dir = line_split[3]
    lng = line_split[4]
    lng_dir = line_split[5]
    lat_deg = lat[0:2]
    lat_min = lat[2:]
    lng_deg = lng[0:3]
    lng_min = lng[3:]

    latitude = float(lat_deg) + (float(lat_min) / 60)
    longitude = float(lng_deg) + (float(lng_min) / 60)
    if lat_dir == "S":
        latitude *= -1
    if lng_dir == "W":
        longitude *= -1

    # Relevant XKCD - https://xkcd.com/2170/
    res.lat = format(latitude, ".5f")
    res.lng = format(longitude, ".5f")
    logging.info(f"Read GGA signal {res} successfully")

    return res


def setup_gps_source():
    """
    Find a GPS source over serial and return something that we can read from

    @return a Serial object that can be read for GPS data
    """
    port_list = list(list_ports.comports())
    logging.debug(
        f"Candidate GPS devices: [{', '.join([p.device for p in port_list])}]")

    # If it tells us it is a GPS, we're pretty sure it is a GPS
    found_gps_for_sure = False
    for p in port_list:
        if "gps" in str(p.product) or "GPS" in str(p.product):
            port = p.device
            found_gps_for_sure = True
            break

    # Otherwise, if there's more than one option, ask the user
    if len(port_list) > 1 and not found_gps_for_sure:
        port_str = "\n\t"
        port_str += "\n\t".join([p.device for p in port_list])
        inp = input(
            f"Which port corresponds to your GPS? Options: {port_str}\n $")
        for port_obj in port_list:
            if port_obj.device == inp:
                port = port_obj.device
                break

    elif len(port_list) == 1:
        # If there's only one option, we will try it because it's all there is.
        port = port_list[0].device
    elif not found_gps_for_sure:
        # Otherwise, we fail
        logging.warning("Could not find GPS. Not logging location source")
        return None
    logging.debug(f"Found GPS source device {port}")
    serial_obj = serial.Serial(port)
    # Wait for it to start returning location data
    for _ in range(GPS_POLL_SEC):
        gps_response = get_gga_signal_from_serial(serial_obj)
        if gps_response is None:
            continue
        if gps_response.is_valid_read():
            logging.info(f"Found properly functioning GPS device at {port}")
            return serial_obj
        time.sleep(1)

    # If we get here, we've tried for the max timeout. Give up
    logging.error(
        f"Polled for {GPS_POLL_SEC} seconds but could not get valid signal from GPS. No location services available"
    )
    return None


def save_read_to_file(expanded_out_file, signal_strength_db,
                      signal_strength_s_unit, gps_read):
    """
    Save a single sample to the CSV file. Assumes we've set it up already
    and there is a correctly populated header.
    """
    row_dict = {}
    # set up dictionary for dictwriter
    for col in CSV_COLUMNS:
        row_dict[col] = ""

    row_dict["timestamp"] = str(datetime.datetime.now())

    [
        "timestamp", "signal_strength_db", "signal_strength_s_unit",
        "latitude", "longitude", "elevation"
    ]
    # Populate GPS reads if the GPS read is a valid object
    if gps_read is not None:
        row_dict["latitude"] = gps_read.lat
        row_dict["longitude"] = gps_read.lng
        row_dict["elevation"] = gps_read.altitude

    row_dict["signal_strength_db"] = signal_strength_db
    row_dict["signal_strength_s_unit"] = signal_strength_s_unit

    # Open in append mode
    with open(expanded_out_file, "a") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writerow(row_dict)


def init_output_file(expanded_out_file):
    """
    Write the CSV header to the output file
    """
    new_file = True

    if os.path.exists(expanded_out_file):
        new_file = False
        logging.warning(f"Output file {expanded_out_file} exists already")
        response = input(
            "Do you want to overwrite the existing output file? y/N\n")
        if response == "y" or response == "Y":
            new_file = True

    # We overwrite the file if it doesn't exist, or if the user told us to.
    if not new_file:
        return False

    # open in "w" mode to write a new file
    with open(expanded_out_file, "w") as fh:
        writer = csv.writer(fh)
        writer.writerow(CSV_COLUMNS)


def main():
    """
	Main program loop.
	"""
    # Detect the platform
    system = platform.system()
    logging.debug(f"Found platform {system}")
    speak_func = get_platform_speak_func(system)

    expanded_out_file = os.path.expandvars(os.path.expanduser(OUTPUT_FILE_CSV))

    gps_stream = setup_gps_source()

    if gps_stream == None:
        logging.warning("GPS source not found. Not storing location data")
        store_location = False

    # Leave this obj as None if we are not using the RTLSDR
    sdr = None

    response = init_output_file(expanded_out_file)
    if response == False:
        logging.error(
            "Failed to create output file. Please verify your supplied output file path is free, or you are okay overwriting it"
        )
        sys.exit(1)

    if SIGNAL_SOURCE == SignalSource.RTLSDR:
        # Configure the RTLSDR if we want it
        logging.debug("Using signal source RTLSDR")
        sdr = RtlSdr()
        if LISTENING_FREQUENCY <= 3e7:
            # For HF frequencies, we will get better results out of direct sampling
            sdr.set_direct_sampling(True)
        sdr.sample_rate = RtlSdrSettings.sample_rate
        sdr.center_freq = RtlSdrSettings.center_freq
        sdr.freq_correction = RtlSdrSettings.freq_correction
        sdr.gain = RtlSdrSettings.gain
        atexit.register(sdr.close)
    else:
        logging.debug("Using signal source LINE IN")
        logging.warning("LINE IN signal source is not yet supported")
        sys.exit(0)

    # Iteration counter. Used for announcing the signal strength every however often
    i = 0
    while True:

        # Get and process the signal strength
        signal_strength_db = read_signal_str(sdr)
        signal_strength_s_unit = get_s_unit_from_db(signal_strength_db)
        logging.info(
            f"Signal strength {format(signal_strength_db, '.3f')} dB ({signal_strength_s_unit})."
        )

        gps_read = None

        # Get and process the location
        if gps_stream is not None:
            gps_read = get_gga_signal_from_serial(gps_stream)

        save_read_to_file(expanded_out_file, signal_strength_db,
                          signal_strength_s_unit, gps_read)

        time.sleep(SAMPLE_INTERVAL)
        if ANNOUNCE_SIGNAL and (i % ANNOUNCE_SIGNAL_EVERY == 0):
            logging.debug(
                f"Announcing signal strength {signal_strength_db} dB ({signal_strength_db})"
            )
            announce_signal(signal_strength_s_unit, speak_func)

        i += 1


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
