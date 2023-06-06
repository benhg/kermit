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

def main():
	"""
	Main program loop.
	"""


if __name__ == '__main__':
	main()