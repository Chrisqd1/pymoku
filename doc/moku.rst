.. currentmodule:: pymoku

Moku:Lab Device Class
=====================

All interaction with pymoku starts with the creation of a :any:`Moku` object. This can be done directly
if one already knows the IP address of the target, or by using one of the *get_by_* functions to look
up a Moku by Name or Serial Number.

.. note:: If you are running on a Linux OS, use of the *get_by_* functions require that your platform has access to *libdnssd*. This
	is provided by the Avahi libdnssd compatibility library. For example, on Ubuntu::

		sudo apt-get install libavahi-compat-libdnssd1

A :any:`Moku` object is useful only for flashing lights until an instrument is deployed to it. The deployment process 
defines the functionality of the Moku:Lab. For examples on how to deploy an instrument, see demo scripts on each of the `Instruments`_ pages below.

Example Usage
-------------

For more details on searching for your Moku:Lab and retrieving device configuration information, see the `Bonjour Moku guide <https://liquidinstruments.atlassian.net/wiki/pages/viewpage.action?pageId=295806>`_. The following example code and a wide range of other pymoku demo scripts, can be found at the `pymoku example repository <https://anaconda.org/liquidinstruments/pymoku-examples/files>`_.

.. literalinclude:: ../examples/moku_basic.py
	:language: python
	:caption: moku_basic.py


--------------
The Moku Class
--------------

.. autoclass:: pymoku.Moku
	:members:

.. _instruments-contents:
-----------
Instruments
-----------

.. toctree::
	:maxdepth: 1

	oscilloscope
	datalogger
	wavegen
	specan
	phasemeter

----------
Exceptions
----------

.. Can't get automodule to work properly for this..
.. autoexception:: MokuException
.. autoexception:: DeployException
.. autoexception:: FileNotFound
.. autoexception:: FrameTimeout
.. autoexception:: InsufficientSpace
.. autoexception:: InvalidConfigurationException
.. autoexception:: InvalidOperationException
.. autoexception:: MokuBusy
.. autoexception:: MokuNotFound
.. autoexception:: MPNotMounted
.. autoexception:: MPReadOnly
.. autoexception:: NetworkError
.. autoexception:: NoDataException
.. autoexception:: NotDeployedException
.. autoexception:: StreamException
.. autoexception:: UnknownAction
.. autoexception:: ValueOutOfRangeException


