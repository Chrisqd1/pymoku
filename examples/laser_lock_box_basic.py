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
m = Moku.get_by_name('Moku')
i = m.deploy_instrument(LaserLockBox)

try:
    i.set_local_oscillator(1e6, 0)
finally:
    m.close()
