#
# pymoku example: Basic Lock-in Amplifier
#
# This example demonstrates how you can configure the lock-in amplifier
# instrument
#
# (c) 2019 Liquid Instruments Pty. Ltd.
#
from pymoku import Moku
from pymoku.instruments import LockInAmp

# Use Moku.get_by_serial() or get_by_name() if you don't know the IP
m = Moku.get_by_name('Moku')

try:
    i = m.deploy_or_connect(LockInAmp)

    # Configure the two DAC outputs to provide the R (magnitude) and
    # demodulation (local-oscillator in this case, see below) outputs.
    # Give the main ('R') channel 100x gain.
    i.set_outputs('R', 'demod')
    i.set_gain('main', 100)

    # Demodulate at 1MHz (internally-generated) with a 100Hz, 2nd-order
    # (6dB / octave) LPF.
    i.set_demodulation('internal', 1e6)
    i.set_filter(100, 2)
finally:
    m.close()
