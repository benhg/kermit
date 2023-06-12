"""
@file config.py

@brief This file maintains configuration details for the program
"""

from enum import Enum, auto
from utils import S_UNIT_SCALE_HF, S_UNIT_SCALE_VHF


class SignalSource(Enum):
    """
	This class represents a signal source that the program should read the signal level from
	"""
    # A USB RTL-SDR
    # https://www.rtl-sdr.com
    RTLSDR = auto()
    # A microphone plugged into line-in
    # For mac, we assume the headphone port is being used for line-in
    # For others, line in is assumed
    LINE_IN = auto()
    # TODO more like USB line in etc


"""
The frequency to listen on, in Hz

A sensible default is 137.00 (MHz), as that is an often-empty frequency in the aircraft band
Set it to something that plays nice with your antenna
"""
LISTENING_FREQUENCY = 146520000
"""
Because s-unit scales are different for VHF vs HF, we need a config parameter to specify to the program whether the user is listening in VHF or HF

We expect most users to use VHF, so we will default to that
"""
S_UNIT_SCALE = S_UNIT_SCALE_VHF if LISTENING_FREQUENCY >= 3e7 else S_UNIT_SCALE_HF


class RtlSdrSettings:
    """
    Class that stores RTL SDR settings for initialization
    """
    sample_rate = 2.048e6  # Sample rate in Hz
    center_freq = LISTENING_FREQUENCY  # Center frequency, in Hz
    freq_correction = 1  # Parts per million
    gain = 0  # Be careful when overriding this.


"""
Because the antenna is not an isotropic radiator, and the input is all in relative db, not absolute db, we need to be able to convert to actual dbi.

We assume you are using a ham-stick or similar simple antenna, by default, which basically behaves like a 0 dBi antenna.
"""
ANTENNA_FUDGE_FACTOR = 0
"""
Set the program's signal source.
Today, RTLSDR and LINE IN are supported
Defaults to RTLSDR
"""
SIGNAL_SOURCE = SignalSource.RTLSDR
"""
The /dev path that the USB serial device shows up at
"""
GPS_DEV_PATH = ""
"""
Set the sampling interval, in seconds
"""
SAMPLE_INTERVAL = 1.0
"""
A flag used to enable/disable the annunciation of signal strength
"""
ANNOUNCE_SIGNAL = True
"""
Every _n_ samples, announce the signal
"""
ANNOUNCE_SIGNAL_EVERY = 5

"""
The output file path. We recommend ending it with `.csv`, as it will be a CSV
It will be appended to by the program. Move the old file yourself if you want a fresh start
"""
OUTPUT_FILE = "~/Desktop/rf_mapper.csv"
