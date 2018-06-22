# PyMoku

A Python library for the command, control and monitoring of the [Liquid Instruments Moku:Lab](http://www.liquidinstruments.com).

API documentation can be found at [ReadTheDocs](http://pymoku.readthedocs.org).

## Installation

Before installing *pymoku*, ensure you have

- The latest [Python](https://www.python.org) distribution installed.  We support Python **2.7** and **3.6**.

- (optional) Bonjour services installed. See [Installing Bonjour Libraries](#Installing-Bonjour-Libraries).

Install using pip

    $ pip install --upgrade pymoku
    $ moku update fetch

Find Moku:Labs on your network with

    $ moku list

Check your Moku:Lab is running the latest firmware with

    $ moku --serial=123456 update install

or

    $ moku --ip=192.168.0.1 update install

The serial number is the middle 6 digits on the underside of the Moku:Lab.

**NOTE:** The update process is indicated by alternating orange and white lights, or a pulsing orange light. This process can take up to 30 minutes.

## Examples

You can find a few example scripts in the **examples/** folder.

Here is a basic example of how to connect to a Moku:Lab, deploy the Oscilloscope and fetch a single data trace.

```python
from pymoku import *
from pymoku.instruments import Oscilloscope

m = Moku.get_by_serial('123456')
i = m.deploy_instrument(Oscilloscope)

i.set_timebase(-1e-3, 1e-3) # 1ms before and after trigger event
i.set_trigger('in1', 'rising', 0) # rising edge through 0 volts

data = i.get_data()
print(data.ch1, data.ch2, data.time)

m.close()
```

## Troubleshooting

#### Installing Bonjour Libraries

To automatically discover Moku:Lab on your network (i.e. by *name* or *serial*) you must have Bonjour installed.

Without Bonjour, your Moku:Lab will still be accessible by IP address, you just won't be able to automatically connect by name or serial number, or find it using `moku list`.

To install Bonjour:

- **Windows** install the [Apple Bonjour Printer Services](https://support.apple.com/kb/DL999). Note that you can choose not to install this service, and

- **Linux** install the dnssd compatibility libraries. For Ubuntu, this is

        $ sudo apt-get install libavahi-compat-libdnssd1

- **OSX** comes with Bonjour by default.

#### I can't find my Moku:Lab on the network

Search your local network for running Moku:Labs with

    $ moku list

If you do not see your Moku:Lab, confirm that your Moku:Lab is powered ON, and that you have Bonjour installed on your operating system [Installing Bonjour Libraries](#Installing-Bonjour-Libraries).

If you are connecting over

- **Access Point Mode** Ensure your computer is connected to the Moku:Lab's WiFi network.  The Moku:Lab will default to the IP address `192.168.73.1`.
- **Ethernet** Ensure the cable is plugged in an you see the orange activity light.  You will need a DHCP server running on your network to provide the Moku:Lab an IP address.
- **WiFi** After configuring the WiFi in the Moku:Lab (currently requires an iPad), you should see a solid blue light on the front.  If it's blinking indefinitely or off, check the configuration again using an iPad.
- **USB** ensure you have plugged the Moku:Lab's micro-USB port into the USB port of your PC. For Linux users, you will have to change the USB-Ethernet network settings to "Link Local" for IPv4 and IPv6. **NOTE:** Currently only one Moku:Lab can be connected over USB at a time.

See [Connecting to your Moku:Lab](https://github.com/liquidinstruments/pymoku/wiki/Connecting-to-your-Moku:Lab) guide on how to find your device's IP address.

If you are still having difficulty, contact support@liquidinstruments.com.

#### ImportError: No Module named pymoku

Make sure you are running the version of Python you installed pymoku to.  Often a system will have multiple Python installations. Try substituting `pip` with `python -m pip` in the installation.

If you installed pymoku inside an Environment (i.e. via virtualenv or conda-env), ensure that Environment is activated. You can check that pymoku is installed in your currently running environment using

    (myenv)$ pip list

or

    (myenv)$ conda list # For conda users

#### zmq.error.Again: Resource temporarily unavailable

1. Ensure your Moku:Lab is visible on the network by calling `moku list` or searching for the service using BonjourBrowser
2. Make sure you are using the latest version of pymoku, and that your Moku:Lab has been upgraded to the newest firmware. See the Installation section above for details.

#### pymoku.DeployException: Deploy Error 3

Confirm you have have the latest binary data pack and that your Moku:Lab is running the latest firmware

    $ moku update fetch
    $ moku --serial=123456 update install

## Issue Tracking

Please log issues here on Github.
