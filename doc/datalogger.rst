
Datalogger Instrument
=======================

The Datalogger instrument provides file logging (to CSV and Binary formats) and network streaming of time-series voltage data. It contains a built-in Signal Generator that can control the Moku:Lab analog outputs as well.

For file logging or network streaming, use the `_data_log` or `_stream_data` type functions, respectively.

.. note:: 
	To convert *.li* binary formatted log files, consult the tutorial on the `moku command line utility <http://confluence.liquidinstruments.com>`_.

Example Usage
-------------

.. TODO: Move back in to source file?
For an in-depth walkthrough on using the pymoku Datalogger Instrument, see the `pymoku Datalogger tutorial <http://confluence.liquidinstruments.com>`_. For the following example code and a wide range of other pymoku demo scripts, see the `pymoku example repository <https://anaconda.org/liquidinstruments/pymoku-examples>`_.

.. literalinclude:: ../examples/basic_datalogger.py
	:language: python
	:caption: basic_datalogger.py

.. literalinclude:: ../examples/livestream_datalogger.py
	:language: python
	:caption: livestream_datalogger.py

The Datalogger Class
----------------------

.. autoclass:: pymoku.instruments.Datalogger
	:members:
	:inherited-members:

