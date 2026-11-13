# Calibrating KERMIT for V/m readings

Out of the box, KERMIT reports relative band power in dBFS. That is enough to find the loudest spot on a map, but the numbers only mean something for your receiver at your settings. To get an estimated field strength in V/m, KERMIT needs two numbers in `kermit_sdr/config.py`:

- `RECEIVER_DBFS_TO_DBM_OFFSET`: turns the measured dBFS into dBm at the SDR input
- `ANTENNA_FACTOR_DB_PER_M`: turns the voltage at the antenna connector into the field around the antenna

plus `CABLE_LOSS_DB` for the coax between antenna and SDR. This guide explains how to get them with ordinary ham shack equipment. See "Band power and V/m reporting" in the README for what the V/m value does and does not mean.

## How KERMIT gets from samples to V/m

```
band_power_dbfs     mean power of all IQ samples across the sampled band (2.048 MHz by default)
+ offset            -> P_dBm, power at the SDR input
-> 50 ohm           -> V_rms = sqrt(50 * 10^((P_dBm - 30) / 10))
x antenna factor    -> E = V_rms * 10^((ANTENNA_FACTOR_DB_PER_M + CABLE_LOSS_DB) / 20)
```

KERMIT only reports V/m when both the offset and the antenna factor are set. Until then the CSV says `uncalibrated` and the V/m column stays empty. The S-unit column also needs the offset.

## Before you start

The calibration is only valid for the exact settings you calibrate with. Decide on these first and don't change them afterwards:

- `LISTENING_FREQUENCY` and `RtlSdrSettings.sample_rate`
- `RtlSdrSettings.gain`
- direct sampling, which KERMIT switches on by itself below 30 MHz
- the SDR itself (two dongles of the same model can differ by several dB)

If you change any of them, calibrate again.

## Part 1: The receiver offset

You need a signal of known level at the SDR input. Any of these work:

- a signal generator, for example the one in a tinySA (see below)
- a transmitter of known power followed by enough attenuation (see the warning below)

### Using a tinySA

The original tinySA's low output mode covers 100 kHz to 350 MHz at -76 to -6 dBm. The tinySA Ultra goes lower. After the built-in level calibration the tinySA is good to about 1 dB, which is fine for this purpose.

1. Run LEVEL CAL on the tinySA (it uses its 30 MHz reference).
2. Connect the tinySA output to the SDR with a short cable. If you want the cable loss of your antenna coax included, use that coax instead, and set `CABLE_LOSS_DB = 0` later (see Part 2).
3. Set the generator a few hundred kHz away from `LISTENING_FREQUENCY` but still well inside the sampled band, for example 145.43 MHz for the default 145.23 MHz. Right on the center frequency, the RTL-SDR's own DC spike adds to the reading.

### Taking the readings

KERMIT adds up the power across the whole sampled band, so the receiver's own noise is part of every reading. You have to measure it and take it out:

1. With the generator output **off**, record about 30 seconds:

   ```sh
   kermit collect-data -o ~/kermit-cal/off
   ```

   Stop it with ctrl-C. KERMIT does not need a GPS fix for this.

2. Turn the generator **on** at a known level, for example -60 dBm, and record again:

   ```sh
   kermit collect-data -o ~/kermit-cal/on-60
   ```

3. Average each recording. The first reading after startup is usually much too high, so skip it. This prints the power average of the `band_power_dbfs` column:

   ```sh
   python3 -c "import csv,sys,math; r=[float(x['band_power_dbfs']) for x in csv.DictReader(open(sys.argv[1]))][1:]; print(round(10*math.log10(sum(10**(v/10) for v in r)/len(r)), 2))" ~/kermit-cal/off.csv
   ```

4. Take the noise out of the "on" reading:

   ```
   carrier_dBFS = 10 * log10(10^(on/10) - 10^(off/10))
   offset       = generator_dBm - carrier_dBFS
   ```

   Example: off = -30.5 dBFS, on = -24.0 dBFS, generator at -60 dBm.
   carrier = 10 * log10(10^-2.40 - 10^-3.05) = -25.1 dBFS, offset = -60 - (-25.1) = **-34.9 dB**.

   The "on" reading should be at least 10 dB above "off". Closer than that, small changes in the noise make a big difference in the result.

5. Repeat step 2 to 4 at three or four levels, for example -70, -60, -50 and -40 dBm. The offset should come out the same within about 1 dB:
   - If it drifts at the **low** levels, you are too close to the noise. Use only the higher levels.
   - If it drifts at the **high** levels, the receiver is overloading. Use only the lower levels, and don't survey near strong transmitters at this gain.

6. Use the average of the consistent results as `RECEIVER_DBFS_TO_DBM_OFFSET`.

### Using a transmitter instead

You can use an HT of known power with an attenuator chain, for example 0.5 W (+27 dBm) through 90 dB gives about -63 dBm.

**Never connect a transmitter to an SDR without enough attenuation. It will destroy the SDR.** Check the attenuators' power rating for the first stage. Also keep in mind that cheap attenuators leak, and an HT's real output power can be quite different from what it says. Your offset can't be better than these numbers. If you have a tinySA, use it to check the power and the attenuation.

### An S9 calibrator

A fixed S9 calibrator (S9 is -73 dBm on HF and -93 dBm on VHF and up) only gives you one level, so it can't show whether the receiver is linear. It is still useful to check your main signal source at one point. Two limits:

- An HF calibrator only calibrates HF settings. Below 30 MHz KERMIT uses direct sampling, which needs its own offset.
- -93 dBm is usually too weak here, because KERMIT measures the noise of the whole 2 MHz band along with it. Check that the "on" reading is at least 10 dB above "off".

## Part 2: Antenna factor and cable loss

The antenna factor says how much field it takes to produce one volt at the antenna connector:

```
E (V/m) = V (volts) * 10^(antenna_factor / 20)
```

### Where to get it

- **Data sheet:** Measurement antennas come with an antenna factor table. Most ham antennas don't.
- **Calculation**, for a matched antenna with known gain in free space:

  ```
  antenna_factor (dB/m) = 20 * log10(f_MHz) - 29.77 - gain_dBi
  ```

  For a half-wave dipole (2.15 dBi) at 145.23 MHz that gives **11.3 dB/m**.

- **Measurement** in a known field. This is the most accurate way, and the hardest.

A mag-mount antenna on a car is only roughly approximated by a calculated value. The car body, the mounting spot and the polarization of the signal all change it. Count on a few dB of uncertainty. The value also changes with frequency, so it should be valid across the sampled band (2 MHz at 145 MHz is not a problem, but a wide HF band can be).

### Cable loss

`CABLE_LOSS_DB` is the loss of the coax between antenna and SDR at your frequency. Take it from the cable's data sheet or measure it with the tinySA. Count it only once: If you calibrated the offset through the same coax in Part 1, it is already included and `CABLE_LOSS_DB` stays at 0.

## Part 3: Enter and check

Put the values into `kermit_sdr/config.py`, for example:

```python
RECEIVER_DBFS_TO_DBM_OFFSET = -34.9
ANTENNA_FACTOR_DB_PER_M = 11.3
CABLE_LOSS_DB = 1.0
```

Then run `kermit collect-data` again. The log should now show `field ... V/m (calibrated_estimate)` instead of `uncalibrated`, and `kermit generate-map` uses V/m by default (`--metric dbfs` still shows the relative values).

Two quick checks:

- Connect the tinySA again at a level you did not use for calibration. `input_power_dbm` in the CSV should match the generator level within about 1 dB.
- With nothing but the antenna connected, a quiet spot gives you the lowest V/m KERMIT can report with this setup. Readings near that value mostly show the receiver's own noise, not the field.

A rough field check is possible with a transmitter at a known distance outdoors. In the far field, `E (V/m) = sqrt(30 * P_W * G) / d_m` (G as a plain factor, 1 for an isotropic antenna). For example 0.5 W at 300 m with G = 1 gives about 13 mV/m. Ground reflections easily move the real value by 6 dB or more, so this only catches big mistakes, such as a sign error in the offset. Make sure you are allowed to transmit on that frequency, and keep the transmitter far enough away that the SDR is not overloaded.

## What the numbers mean

- The V/m value is an estimate for the sampled band and the antenna orientation, not an RF exposure measurement.
- Everything in the band counts: interference, strong nearby signals, the DC spike and the receiver's own noise.
- If anything in the setup changes (frequency, sample rate, gain, dongle, antenna, mounting, coax), the calibration is no longer valid.
