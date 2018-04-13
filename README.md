# pymoku

Python library for the command, control and monitoring of the [Liquid Instruments Moku:Lab](http://www.liquidinstruments.com) device.

Primary documentation on [ReadTheDocs](http://pymoku.readthedocs.org)

## Installation
### 1. Install the package
#### Using pip
You can install pymoku directly from the Python Package Index (pypi) using the **pip** utility. Most Python distributions come with pip pre-installed. To do this, run

    $: sudo pip install --upgrade pymoku
    OR
    $: sudo pip3 install --upgrade pymoku # Python 3.x
    
#### Using conda
If you are using the [conda](https://www.anaconda.com/) package manager run

    $: conda config --add channels conda-forge
    $: conda config --add channels liquidinstruments
    $: conda install pymoku

Alternatively, use the Anaconda Navigator GUI to add the `liquidinstruments` channel to your desired conda environment and search for the `pymoku` package.
        
### 2. Test your install
You can test successful installation with

    $: python
    OR 
    $: python3 # Python 3.x
    >>> import pymoku
    >>> # No import errors should be seen here.
       
### 3. Update your Moku:Lab
To successfully connect to your Moku:Lab, you'll need to ensure it is running the latest instruments and firmware. First fetch the latest device files

    $: sudo moku update fetch
    
Then by using your Moku:Lab serial number (or [IP address](https://github.com/liquidinstruments/pymoku/wiki/Connecting-to-your-Moku:Lab)), upgrade your Moku:Lab's firmware

    $: moku --serial=123456 update install # Use --ip if Bonjour Discovery unavailable

You're good to go! You can find all Moku:Labs on your network using

    $: moku list


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
#### Can't import Bonjour Libraries
On **Windows** autodiscovery requires extra drivers from Apple. Install the [Apple Bonjour Printer Services](https://support.apple.com/kb/DL999). Note that you can choose not to install this service, and your Moku:Lab will still be accessible by IP address, you just won't be able to automatically connect by name or serial number.

On **Linux** install the dnssd compatibility libraries. For Ubuntu, this is

    $: sudo apt-get install libavahi-compat-libdnssd1
    
On **Mac** contact Liquid Instruments support, this shouldn't happen.

#### ImportError: No Module named pymoku
Make sure you are running the version of Python you installed pymoku to. Use **pip** and **python** for Python 2.7, and **pip3** and **python3** for Python 3.x.

If you installed pymoku inside an Environment (i.e. via virtualenv or conda-env), ensure that Environment is activated. You can check that pymoku is installed in your currently running environment using

    (myenv)$: pip list
    OR
    (myenv)$: conda list # For conda users
    
#### zmq.error.Again: Resource temporarily unavailable
1. Ensure your Moku:Lab is visible on the network by calling `moku list` or searching for the service using BonjourBrowser
2. Make sure you are using the latest version of pymoku, and that your Moku:Lab has been upgraded to the newest firmware. See the Installation section above for details.


## Issue Tracking
Please log issues here on Github.