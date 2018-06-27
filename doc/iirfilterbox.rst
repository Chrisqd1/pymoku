
IIR Filter Box Instrument
============================

The IIR Filter Box implements infinite impulse response (IIR) filters using 4 cascaded Direct Form 1 second-order stages with a final output gain stage. The instrument has two independent filter chains, a control matrix to combine signals from both ADCs, input/output scaling and offsets and oscilloscope monitor probes to view signals at different points in the instrument. 

Example Usage
-------------

The following example code and a wide range of other pymoku demo scripts can be found at the `pymoku Github repository <https://github.com/liquidinstruments/pymoku>`_.

.. literalinclude:: ../examples/iirfilterbox_basic.py
	:language: python
	:caption: iirfilterbox_basic.py


The IIRFilterBox Class
-----------------------

.. autoclass:: pymoku.instruments.IIRFilterBox
	:members:
	:inherited-members:

