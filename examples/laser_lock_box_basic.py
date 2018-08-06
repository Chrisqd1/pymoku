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
    # i.set_local_oscillator(1e6, 0)
    i.set_sample_rate('high')
    i.set_local_oscillator(1, 0)
    i.set_pid_by_gain(1, g=1, kp=1)
    i.set_pid_enable(1, True)
    i.set_pid_bypass(1, False)
    i.set_pid_by_gain(2, g = 1, kp = 1)
    i.set_pid_enable(2, True)
    i.set_pid_bypass(2, False)

    i.set_scan(frequency=100, phase=0.0, pid ='fast', amplitude=0.25)
finally:
    m.close()
