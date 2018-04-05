
# pymoku

Python library for the command, control and monitoring of the [Liquid Instruments Moku:Lab](http://www.liquidinstruments.com) device.

Primary documentation on [ReadTheDocs](http://pymoku.readthedocs.org)

## WARNING
This is currently in an Alpha release. The library is usable for a range of tasks, but not all functions are known to work as documented. If you find a problem where the code looks like it *should* work but doesn't, please submit an issue.

## Installation

    sudo pip install --upgrade pymoku

You'll also need to fetch binary artefacts to configure the Moku:Lab with

    sudo moku update fetch

And if you already have a Moku:Lab running an old firmware version you can update it with

    moku --serial=123456 update install

To find Moku:Labs on your network

    moku list

## Examples
You can find a few example scripts in the **examples/** folder.

Here is a basic example of how to connect to a Moku:Lab, deploy the Oscilloscope and fetch a single data trace.

```python
from pymoku import *
from pymoku.instruments import Oscilloscope

m = Moku.get_by_serial('123456')
i = m.deploy_instrument(Oscilloscope)

i.set_timebase(-1e-3, 1e-3) #1ms before and after trigger event
i.set_trigger('in1', 'rising', 0) #risinge edge through 0 volts

data = i.get_data()
print(data.ch1, data.ch2, data.time)

m.close()
```

## Issue Tracking
Please log issues here on Github.
