
FIR Filter Box Instrument
============================

The FIR Filter Box implements finite impulse response (FIR) filters at up to 15 MS/s and with over 14,000 coefficients at 244 kS/s. The instrument has two independent filter chains, a control matrix to combine signals from both ADCs, input/output scaling and offsets and oscilloscope monitor probes to view signals at different points in the instrument. 

Example Usage
-------------

The following example code and a wide range of other pymoku demo scripts can be found at the `pymoku Github repository <https://github.com/liquidinstruments/pymoku>`_.

.. literalinclude:: ../examples/firfilter_basic.py
	:language: python
	:caption: firfilter_basic.py


The FIR Filter Box Class
-----------------------

.. autoclass:: pymoku.instruments.FIRFilter
	:members:
	:inherited-members:
