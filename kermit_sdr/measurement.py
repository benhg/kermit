"""Band-integrated IQ power and calibrated antenna field estimates.

Calibration is valid only for the receiver settings and frequency band used
when measuring the offset and antenna factor. No isotropic assumption is made.
"""
import math


def band_power_dbfs(samples):
    """Mean complex IQ power, relative to unit complex magnitude (0 dBFS)."""
    count = len(samples)
    if not count:
        raise ValueError('Cannot measure an empty IQ block')
    power = sum(abs(sample) ** 2 for sample in samples) / count
    if not math.isfinite(power):
        raise ValueError('IQ samples must be finite')
    # Floor silence for serializable output; does not imply a receiver noise floor.
    return 10 * math.log10(max(power, 1e-30))


def measure(samples, center_frequency_hz, bandwidth_hz,
            receiver_offset_db=None, antenna_factor_db_per_m=None,
            cable_loss_db=0, impedance_ohms=50):
    """Convert integrated dBFS -> dBm -> terminal Vrms -> estimated V/m.

    receiver_offset_db = known injected dBm - measured integrated dBFS.
    antenna_factor_db_per_m = 20 log10(E / antenna-terminal Vrms).
    Both must apply across the measured band. Cable loss is between antenna
    and calibrated receiver input; do not count it twice in the offset.
    """
    values = [center_frequency_hz, bandwidth_hz, cable_loss_db, impedance_ohms]
    values += [v for v in (receiver_offset_db, antenna_factor_db_per_m) if v is not None]
    if not all(math.isfinite(v) for v in values):
        raise ValueError('Measurement settings must be finite')
    if bandwidth_hz <= 0 or impedance_ohms <= 0 or center_frequency_hz <= 0:
        raise ValueError('Frequency, bandwidth and impedance must be positive')
    dbfs = band_power_dbfs(samples)
    calibrated = receiver_offset_db is not None and antenna_factor_db_per_m is not None
    power_dbm = None if receiver_offset_db is None else dbfs + receiver_offset_db
    field = None
    if calibrated:
        terminal_v = math.sqrt(impedance_ohms * 10 ** ((power_dbm - 30) / 10))
        field = terminal_v * 10 ** ((antenna_factor_db_per_m + cable_loss_db) / 20)
    return dict(band_power_dbfs=dbfs, input_power_dbm=power_dbm,
                field_strength_v_m=field,
                measurement_status='calibrated_estimate' if calibrated else 'uncalibrated',
                center_frequency_hz=center_frequency_hz, bandwidth_hz=bandwidth_hz)
