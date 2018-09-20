#
# pymoku example: Basic Lock-in Amplifier
#
# This example demonstrates how you can configure the lock-in amplifier
# instrument
#
# (c) 2017 Liquid Instruments Pty. Ltd.
#
from pymoku import Moku
from pymoku.instruments import LaserLockBox

from scipy import signal

def gen_butterworth(corner_frequency):
    """
    Generate coefficients for a second order butterworth low-pass filter.

    Corner frequencies for laser lock box second harmonic filtering should be in the range: 1 kHz < corner frequency < 31.25 MHz.
    """
    sample_rate = 62.5e6
    normalised_corner = corner_frequency / (sample_rate / 2)
    b, a = signal.butter(2, normalised_corner, 'low', analog = False)

    coefficient_array = [[1.0],
                        [1.0, b[0], b[1], b[2], -a[1], -a[2]],
                        [1.0, 1.0,  0.0,  0.0,  0.0, 0.0]]
    return coefficient_array

# Use Moku.get_by_serial() or get_by_name() if you don't know the IP
m = Moku.get_by_name('PeregrinTook', force = True)
i = m.deploy_instrument(LaserLockBox)

try:
    # set local oscillator, auxiliary and scan generators
    i.set_local_oscillator(source='internal', frequency=10e3, phase=0, pll_auto_acq = False)
    i.set_aux_sine(amplitude = 1.0, frequency = 10e6, phase=0, sync_to_lo = False, output = 'out2')
    i.set_scan(frequency=1e3, phase=0, output = 'out1', amplitude=1.0, waveform='triangle')

    # configure PIDs:
    i.set_pid_by_gain(1, g=1, kp=1)
    i.set_pid_enable(1, True)
    i.set_pid_bypass(1, False)
    i.set_pid_by_gain(2, g=1, kp=1)
    i.set_pid_enable(2, True)
    i.set_pid_bypass(2, False)

    # set offsets
    i.set_offsets(position = 'pid_input', offset = 0.1)
    i.set_offsets(position = 'out1', offset = -0.1)
    i.set_offsets(position = 'out2', offset = 0.2)

    # set allowable output range
    i.set_output_range(1, 0.5, -0.5)
    i.set_output_range(2, 0.5, -0.5)

    # configure second harmonic rejection low pass filter
    coef_array = gen_butterworth(1e4)
    i.set_custom_filter(coef_array)
finally:
	m.close()
