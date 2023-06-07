"""
@file config.py

@brief This file maintains configuration details for the program
"""

from enum import Enum, auto


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
LISTENING_FREQUENCY = 14523e4

class RtlSdrSettings:
    """
    Class that stores RTL SDR settings for initialization
    """
    sample_rate = 2.048e6 # Sample rate in Hz
    center_freq = LISTENING_FREQUENCY # Center frequency, in Hz
    freq_correction = 60  # Parts per million


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
SAMPLE_INTERVAL = 0.5
