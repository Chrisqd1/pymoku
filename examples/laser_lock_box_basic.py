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

# Use Moku.get_by_serial() or get_by_name() if you don't know the IP
m = Moku.get_by_name('Bilbo', force = True)
i = m.deploy_instrument(LaserLockBox)

try:
    i.set_frontend(1, fiftyr = True, atten = False, ac = False)
    i.set_local_oscillator(source='internal', frequency=50e3, phase=0, pll_auto_acq = True)
    i.set_aux_sine(amplitude = 1.0, frequency = 2e3, phase=0, sync_to_lo = False)
    i.set_pid_by_gain(1, g=1, kp=1)
    i.set_pid_enable(1, True)
    i.set_pid_bypass(1, True)
    i.set_pid_by_gain(2, g = 1, kp = 1)
    i.set_pid_enable(2, True)
    i.set_pid_bypass(2, True)

    i.set_scan(frequency=1e4, phase=0.0, output = 'none', amplitude=0.25, waveform='sawtooth')
finally:
	m.close()
