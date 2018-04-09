
Datalogger Instrument
=======================

The Datalogger instrument provides file logging (to CSV and Binary formats) and network streaming of time-series voltage data. It contains a built-in Waveform Generator that can control the Moku:Lab analog outputs as well.

For file logging or network streaming, use the `_data_log` or `_stream_data` type functions, respectively.

.. note:: 
	To convert *.li* binary formatted log files, use the `moku_convert` command line utility that comes with your pymoku installation. Alternatively, you can download an exectuable version `here <https://www.liquidinstruments.com/utilities/>`_.

Example Usage
-------------

For an in-depth walkthrough on using the pymoku Datalogger Instrument, see the `pymoku Datalogger tutorial <https://liquidinstruments.atlassian.net/wiki/display/MCS/The+Datalogger>`_. The following example code and a wide range of other pymoku demo scripts can be found at the `pymoku Github repository <https://github.com/liquidinstruments/pymoku>`_.

.. literalinclude:: ../examples/datalogger_basic.py
	:language: python
	:caption: datalogger_basic.py

.. literalinclude:: ../examples/datalogger_streaming.py
	:language: python
	:caption: datalogger_streaming.py

The Datalogger Class
----------------------

.. autoclass:: pymoku.instruments.Datalogger
	:members:
	:inherited-members:

