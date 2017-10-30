# This basic example will show basic methods of using the pymoku lock-in amplifier


from pymoku import Moku
from pymoku.instruments import *
import time, logging

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s::%(message)s')
# logging.getLogger('pymoku').setLevel(logging.DEBUG)

# Use Moku.get_by_serial() or get_by_name() if you don't know the IP
m = Moku('192.168.69.224')

i = LockInAmp()

m.deploy_instrument(i)
i.set_defaults()



# i.set_trigger('in1', 'rising', 0, hysteresis=0.1)
i.set_timebase(-0.05, 0.05)


data = i.get_realtime_data()

# Set up the plotting parameters
plt.ion()
plt.show()
plt.grid(b=True)
plt.ylim([-1,1])
plt.xlim([data.time[0], data.time[-1]])

line1, = plt.plot([])
line2, = plt.plot([])

# Configure labels for axes
ax = plt.gca()
ax.xaxis.set_major_formatter(FuncFormatter(data.get_xaxis_fmt))
ax.yaxis.set_major_formatter(FuncFormatter(data.get_yaxis_fmt))
ax.fmt_xdata = data.get_xcoord_fmt
ax.fmt_ydata = data.get_ycoord_fmt

data = i.get_realtime_data() # get data from monitors

# Update the plot
line1.set_ydata(data.ch1)
# line2.set_ydata(data.ch2)
line1.set_xdata(data.time)
# line2.set_xdata(data.time)


# connect In1 to 10 MHz sine signal at 500 mVpp no offset
# connect In2 to 10 MHz square at 500 mVpp no offset

i.set_lo_parameters(10.0001e6,0) # set local oscillator to 10.0001 MHz. (100 Hz offset from the input)

i.set_monitor(1,'out') # set channel 1 of scope to view 'i'
i.set_monitor(2,'aux') # set channel 2 of scope to view 'q'

time.sleep(0.1)

data = i.get_realtime_data() # get data from monitors

# Update the plot
line1.set_ydata(data.ch1)
# line2.set_ydata(data.ch2)
line1.set_xdata(data.time)
# line2.set_xdata(data.time)

raw_input("monitor is set to measure 'i' and 'q'. Press Enter to continue ... ")

i.set_signal_mode('r_theta') # set signal mode to measure r and theta.

time.sleep(0.1)
data = i.get_realtime_data() # get data from monitors
# Update the plot
line1.set_ydata(data.ch1)
# line2.set_ydata(data.ch2)
line1.set_xdata(data.time)
# line2.set_xdata(data.time)

raw_input("monitor is set to measure 'r' and 'theta'. Press Enter to continue ... ")


# CHECK OUTPUT 1 SELECT
i.set_single_channel_sig('q') # sets the channel to output q.
raw_input("Output 1 set to output 'q'. Press Enter to continue ... ")

i.set_single_channel_sig('r') # sets Output 1 to output the magnitude of the input
raw_input("Output 1 set to output 'r'. Press Enter to continue ... ")

i.set_single_channel_sig('theta') # sets Output 1 to output the phase of the input with respect to the local oscillator
raw_input("Output 1 set to output 'theta'. Press Enter to continue ... ")

i.set_single_channel_sig('i') # sets Output 1 to output i
raw_input("Output 1 set to output 'i'. Press Enter to continue ... ")

# CHECK EXT LO SETTINGS
i.set_lo_mode('internal')
raw_input("Internal LO set. Press Enter to continue ... ")

i.set_lo_mode('external')
raw_input("direct external LO set. Press Enter to continue ... ")

i.set_lo_mode('external_pll')
raw_input("PLLed external LO set. Press Enter to continue ... ")

# CHECK OUTPUT 2 SELECT
i.set_lo_output(0.5, 0.0, 100, 0) # set output 2 to 100 Hz at 500 mV
i.set_aux_out('sine')
raw_input("Output 2 to output sinewave. Press Enter to continue ... ")

i.set_aux_out('ch2')
raw_input("Output 2 to output channel 2. Press Enter to continue ... ")

i.set_aux_out('demod')
raw_input("Output 2 to output demod. Press Enter to continue ... ")

## CHECK OUTPUT 2 OUTPUTS

i.set_aux_out('ch2')
i.set_signal_mode('iq')
raw_input("Output 2 to output to q. Press Enter to continue ... ")

i.set_aux_out('ch2')
i.set_signal_mode('r_theta')
raw_input("Output 2 to output to theta. Press Enter to continue ... ")

m.close()
