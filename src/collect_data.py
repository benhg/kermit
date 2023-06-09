"""
@file collect_data.py

@brief this file is responsible for collecting RF background levels

At a high-level:

With some frequency defined in a config file:
- Sample the current signal coming in from the line-in
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
import os

from rtlsdr import RtlSdr

from config import SAMPLE_INTERVAL, SignalSource, SIGNAL_SOURCE, RtlSdrSettings, ANTENNA_FUDGE_FACTOR, LISTENING_FREQUENCY, ANNOUNCE_SIGNAL, ANNOUNCE_SIGNAL_EVERY


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
    s_dbfs = 20 * np.log10(s_mag/ref)

    return freq, s_dbfs


def read_signal_str(sdr):
    """
    Read the signal strength out from our signal source

    @param sdr - the RTLSDR object, if we're using the RTLSDR
                 None if we're not
    """
    if sdr:
        # this is TOO EASY
        samples = sdr.read_samples(512)
    else:
        #collect_samples_from_line_in()
        pass

    # Once we have some samples of the signal, we can extract the power
    freq, dbfs = dbfft(samples, RtlSdrSettings.sample_rate)
    avg_db = np.average(dbfs)

    db_result = avg_db - ANTENNA_FUDGE_FACTOR
    print(db_result)
    return db_result

def speak_darwin(text):
    """
    The function for using the `say` command on MacOS
    """
    os.system(f"say '{text}'")

def speak_linux(text):
    """
    The function for using the `espeak` command on Linux
    """
    os.system(f'echo "{text}" | espeak')


def get_platform_speak_func(platform):
    """
    Get a callable that uses the system's text-to-speech program to say a word.

    Returns a function that has one parameter, the text to say
    """
    if platform == "Darwin":
        return speak_darwin
    elif platform == "Linux":
        return speak_linux
        
            

def announce_signal(signal_strength_db, freq, speak_func):
    """
    Announce the signal strength using system text to speech
    
    @param signal_strength_db: Signal strength in dB
    @param freq: Frequency listening on, to decide whether to use VHF or HF s-scale
    @param speak_func: speak function to use for announcin strength
    """
    speak_func(f"S {int(signal_strength_db)}")


def main():
    """
	Main program loop.
	"""
    # Detect the platform
    system = platform.system()
    speak_func = get_platform_speak_func(system)

    # Leave this obj as None if we are not using the RTLSDR
    sdr = None

    if SIGNAL_SOURCE == SignalSource.RTLSDR:
        # Configure the RTLSDR if we want it
        sdr = RtlSdr()
        sdr.sample_rate = RtlSdrSettings.sample_rate
        sdr.center_freq = RtlSdrSettings.center_freq
        sdr.freq_correction = RtlSdrSettings.freq_correction
        sdr.gain = RtlSdrSettings.gain
        atexit.register(sdr.close)

    # Iteration counter. Used for announcing the signal strength every however often
    i = 0
    while True:
        signal_strength_db = read_signal_str(sdr)
        time.sleep(SAMPLE_INTERVAL)

        if ANNOUNCE_SIGNAL and (i % ANNOUNCE_SIGNAL_EVERY == 0):
            announce_signal(signal_strength_db, LISTENING_FREQUENCY, speak_func)

        i+= 1


if __name__ == '__main__':
    main()
