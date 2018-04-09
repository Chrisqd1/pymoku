
Oscilloscope Instrument
=======================

The Oscilloscope instrument provides time-domain views of voltages. It contains a built-in Waveform Generator that can control the Moku:Lab analog outputs as well.

In normal operation, the Oscilloscope shows the signal present on the two analog inputs but it can be set to loop back the signals being generated (see :any:`set_source <pymoku.instruments.Oscilloscope.set_source>`). This loopback takes up a channel (only two signals in total may be viewed at once).  Data is provided at the :any:`framerate <Oscilloscope.framerate>` in the form of :any:`VoltsData` objects. These objects contain the channel data and the required metadata to interpret them.

If you wish to log or network stream time-series voltage data at low rate, the :any:`Datalogger` instrument provides this facility. 

Example Usage
-------------

For an in-depth walkthrough on using the pymoku Oscilloscope Instrument, see the `pymoku Oscilloscope tutorial <https://liquidinstruments.atlassian.net/wiki/display/MCS/The+Oscilloscope>`_. The following example code and a wide range of other pymoku demo scripts can be found at the `pymoku Github repository <https://github.com/liquidinstruments/pymoku>`_.

.. literalinclude:: ../examples/oscilloscope_basic.py
	:language: python
	:caption: oscilloscope_basic.py

The VoltsData Class
--------------------

.. autoclass:: pymoku.instruments.VoltsData

	.. Don't use :members: as it doesn't handle instance attributes well. Directives in the source code list required attributes directly.

The Oscilloscope Class
----------------------

.. autoclass:: pymoku.instruments.Oscilloscope
	:members:
	:inherited-members:

