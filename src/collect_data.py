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

import time
from rtlsdr import RtlSdr

from config import SAMPLE_INTERVAL, SignalSource, SIGNAL_SOURCE, RtlSdrSettings

def main():
    """
	Main program loop.
	"""
    while True:

        if (SIGNAL_SOURCE == SignalSource.RTLSDR):
            sdr = RtlSdr()
            # configure device
            sdr.sample_rate = RtlSdrSettings.sample_rate
            sdr.center_freq = RtlSdrSettings.center_freq
            sdr.freq_correction = RtlSdrSettings.freq_correction
            sdr.gain = 'auto'
            print(sdr.read_samples(512))

        time.sleep(SAMPLE_INTERVAL)



if __name__ == '__main__':
    main()
