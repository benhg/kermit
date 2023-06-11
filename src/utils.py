"""
@file utils.py

@brief this file is responsible for maintaining functions and data structures that are used across multiple files
"""
"""
Map dB ranges to S-units, for clear annunciation
"""
import subprocess


class Interval():
    """
    This class represents a range between two numbers
    We use it for our S-unit scales
    """
    def __init__(self, start=0, end=0):
        """
        Constructor for interval class
        """
        self.start = start
        self.end = end

    def in_interval(self, val):
        """
        Check if a number is in this interval
        """
        return (val > self.start and val <= self.end)


"""
The S-unit scales

To make the announcments shorter, we use an extended scale, so above S-9,
    instead of saying S-9 plus x, we instead define S_x as S_(x-1) + 6 dB

We also add S-0 for below -48
"""

S_UNIT_SCALE_HF = {
    "S0": Interval(start=-999, end=-48),
    "S1": Interval(start=-48, end=-42),
    "S2": Interval(start=-42, end=-36),
    "S3": Interval(start=-36, end=-30),
    "S4": Interval(start=-30, end=-24),
    "S5": Interval(start=-24, end=-18),
    "S6": Interval(start=-18, end=-12),
    "S7": Interval(start=-12, end=-6),
    "S8": Interval(start=-6, end=0),
    "S9": Interval(start=0, end=6),
    "S10": Interval(start=6, end=12),
    "S11": Interval(start=12, end=18),
    "S12": Interval(start=18, end=24),
    "S too much": Interval(start=24, end=999)
}

S_UNIT_SCALE_VHF = {
"S0": Interval(start=-999, end=-48),
    "S1": Interval(start=-48, end=-42),
    "S2": Interval(start=-42, end=-36),
    "S3": Interval(start=-36, end=-30),
    "S4": Interval(start=-30, end=-24),
    "S5": Interval(start=-24, end=-18),
    "S6": Interval(start=-18, end=-12),
    "S7": Interval(start=-12, end=-6),
    "S8": Interval(start=-6, end=0),
    "S9": Interval(start=0, end=6),
    "S10": Interval(start=6, end=12),
    "S11": Interval(start=12, end=18),
    "S12": Interval(start=18, end=24),
    "S too much": Interval(start=24, end=999)
}


def speak_darwin(text):
    """
    The function for using the `say` command on MacOS
    """
    subprocess.Popen(["say", f"'{text}'"])


def speak_linux(text):
    """
    The function for using the `espeak` command on Linux
    """
    subprocess.Popen(["echo", f"'{text}'", "|", "espeak"])


def get_platform_speak_func(platform):
    """
    Get a callable that uses the system's text-to-speech program to say a word.

    Returns a function that has one parameter, the text to say
    """
    if platform == "Darwin":
        return speak_darwin
    elif platform == "Linux":
        return speak_linux
