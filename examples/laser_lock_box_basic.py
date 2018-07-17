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
m = Moku.get_by_name('Denethor', force = True)
i = m.deploy_instrument(LaserLockBox)

try:
    # i.set_local_oscillator(1e6, 0)
    i.set_sample_rate('high')
    i.set_local_oscillator(1, 0)
    i.set_pid_by_gain(1, 1, 1)
    i.set_pid_enable(1, True)
    i.set_pid_bypass(1, False)
finally:
    m.close()
