import serial
import logging
import time
from serial.tools import list_ports
from enum import IntEnum

GPS_POLL_SEC = 30


class GpsReadQuality(IntEnum):
    """
    GPS read quality (source)

    IntEnum because these have well-defined values
    So we can cast from an integer freely
    """
    INVALID = 0
    GPS_SPS = 1
    DGPS = 2
    PPS = 3
    REAL_TIME_KINEMATIC = 4
    FLOAT_RTK = 5
    ESTIMATED = 6
    MANUAL_INPUT = 7
    SIMULATED = 8


class GpsResponse:
    """
    A read from a GPS GGA signal. Contains the following attributes:

    Details from here: http://www.gpsinformation.org/dale/nmea.htm#GGA

    @var timestamp - the timestamp associated with the read
    @var lat - latitude
    @var lng - longitude
    @var quality - enum representing read quality
    @var sat_count - number of satellites currently being read.
    @var altitude - the GPS altitude
    @var error - the dilution of precision - above 20 == bad.
    @var timestamp - timestamp of read
    """
    def __init__(self,
                 lat=0,
                 lng=0,
                 quality=GpsReadQuality.INVALID,
                 sat_count=0,
                 altitude=0,
                 error=0,
                 timestamp=0):
        """
        Constructor for GPS response class
        """
        self.lat = lat
        self.lng = lng
        self.quality = quality
        self.sat_count = sat_count
        self.altitude = altitude
        self.error = error
        self.timestamp = timestamp

    def is_valid_read(self):
        """
        Return whether this read is trustworthy
        """
        return self.quality != GpsReadQuality.INVALID and self.error < 20 and self.sat_count >= 3

    def __repr__(self):
        return f"GpsResponse<lat={self.lat}, lng={self.lng}, quality={GpsReadQuality(self.quality).name}, sat_count={self.sat_count}, altitude={self.altitude}, error={self.error}, timestamp={self.timestamp}>"


def get_gga_signal_from_serial(serial_obj):
    """
    Given a GPS serial object, decode the GGA signal, and return relevant information

    @param serial_obj - a serial object that is a GPS unit
    @return - timestamp, lat, lng, quality, number of satellites, altitude
    """
    line = serial_obj.readline().decode('utf-8')
    # Only use GPGGA signal type
    line_found = False
    while not line_found:
        if "GPGGA" in line:
            logging.debug("Found GPGGA signal from GPS unit")
            line_found = True
            break
        line = serial_obj.readline().decode('utf-8')

    # Process the GPGGA signal, return the serial object
    # The GPGGA signal is well-defined (for decades),
    # so we can be a bit hacky here and get away with it.
    line_split = line.split(",")
    res = GpsResponse(timestamp=line_split[1],
                      quality=GpsReadQuality(int(line_split[6])),
                      sat_count=int(line_split[7]),
                      altitude=float(line_split[9]),
                      error=float(line_split[8]))

    # Converting the degrees from NMEA to decimal is kind of annoying
    lat = line_split[2]
    lat_dir = line_split[3]
    lng = line_split[4]
    lng_dir = line_split[5]

    print(lng_dir)

    lat_deg = lat[0:2]
    lat_min = lat[2:]
    lng_deg = lng[0:3]
    lng_min = lng[3:]

    latitude = float(lat_deg) + (float(lat_min) / 60)
    longitude = float(lng_deg) + (float(lng_min) / 60)

    if lat_dir == "S":
        latitude *= -1
    if lng_dir == "W":
        longitude *= -1
    res.lat = latitude
    res.lng = longitude

    print(f"Read GGA signal {res} successfully")
    logging.debug(f"Read GGA signal {res} successfully")
    return res


def setup_gps_source():
    """
    Find a GPS source over serial and return something that we can read from

    @return a Serial object that can be read for GPS data
    """
    port_list = list(list_ports.comports())
    logging.debug(
        f"Candidate GPS devices: [{', '.join([p.device for p in port_list])}]")

    # If it tells us it is a GPS, we're pretty sure it is a GPS
    found_gps_for_sure = False
    for p in port_list:
        if "gps" in str(p.product) or "GPS" in str(p.product):
            port = p.device
            found_gps_for_sure = True
            break

    # Otherwise, if there's more than one option, ask the user
    if len(port_list) > 1 and not found_gps_for_sure:
        port_str = "\n\t"
        port_str += "\n\t".join([p.device for p in port_list])
        inp = input(
            f"Which port corresponds to your GPS? Options: {port_str}\n $")
        for port_obj in port_list:
            if port_obj.device == inp:
                port = port_obj.device
                break

    elif len(port_list) == 1:
        # If there's only one option, we will try it because it's all there is.
        port = port_list[0].device
    elif not found_gps_for_sure:
        # Otherwise, we fail
        logging.warning("Could not find GPS. Not logging location source")
        return None
    logging.debug(f"Found GPS source device {port}")
    serial_obj = serial.Serial(port)
    # Wait for it to start returning location data
    for _ in range(GPS_POLL_SEC):
        gps_response = get_gga_signal_from_serial(serial_obj)
        if gps_response.is_valid_read():
            logging.info(f"Found properly functioning GPS device at {port}")
            return serial_obj
        time.sleep(1)

    # If we get here, we've tried for the max timeout. Give up
    logging.error(
        f"Polled for {GPS_POLL_SEC} seconds but could not get valid signal from GPS. No location services available"
    )
    return None


setup_gps_source()
