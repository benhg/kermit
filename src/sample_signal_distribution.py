"""
@file sample_signal_distribution.py

@brief collect data from RTLSDR source for mapping dB (RF) to dB (audio) 


The relationship between dB (of RF signal) and dB (of audio out of the line-in) may not be linear (in fact, it probably isn't linear)

There might be a better theorecitcal way to handle that mapping, and I promise to explore that in the future, but for now, what this file helps with is using the RTLSDR's ability to sample both, and produce a sample of the __shape__ of the function across frequencies and volume levels. We will then shift it by the signal strength added by the radio and microphone's relative volume/gain, and get a close-ish representation of the dB of the signal given the line-in.
"""
