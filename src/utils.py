"""
@file utils.py

@brief this file is responsible for maintaining functions and data structures that are used across multiple files
"""
"""
Map dB ranges to S-units, for clear annunciation
"""
import subprocess

S_UNIT_SCALE_HF = {}

S_UNIT_SCALE_VHF = {}


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
