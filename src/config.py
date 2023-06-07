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
