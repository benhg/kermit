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

from rtlsdr import RtlSdr

from config import SAMPLE_INTERVAL, SignalSource, SIGNAL_SOURCE, RtlSdrSettings, ANTENNA_FUDGE_FACTOR,\
                   LISTENING_FREQUENCY, ANNOUNCE_SIGNAL, ANNOUNCE_SIGNAL_EVERY, S_UNIT_SCALE
from utils import get_platform_speak_func


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


def get_current_location():
    logging.warning(f"Location detection is not yet implemented")
    return 0, 0


def main():
    """
	Main program loop.
	"""
    # Detect the platform
    system = platform.system()
    logging.debug(f"Found platform {system}")
    speak_func = get_platform_speak_func(system)

    # Leave this obj as None if we are not using the RTLSDR
    sdr = None

    if SIGNAL_SOURCE == SignalSource.RTLSDR:
        # Configure the RTLSDR if we want it
        logging.debug("Using signal source RTLSDR")
        sdr = RtlSdr()
        sdr.sample_rate = RtlSdrSettings.sample_rate
        sdr.center_freq = RtlSdrSettings.center_freq
        sdr.freq_correction = RtlSdrSettings.freq_correction
        sdr.gain = RtlSdrSettings.gain
        atexit.register(sdr.close)
    else:
        logging.debug("Using signal source LINE IN")

    # Iteration counter. Used for announcing the signal strength every however often
    i = 0
    while True:
        signal_strength_db = read_signal_str(sdr)
        signal_strength_s_unit = get_s_unit_from_db(signal_strength_db)
        lat, lng = get_current_location()

        logging.info(
            f"Signal strength {signal_strength_db} dB ({signal_strength_db}). Location: ({lat}, {lng})"
        )
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
