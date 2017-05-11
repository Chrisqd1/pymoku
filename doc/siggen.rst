
Signal Generator Instrument
=============================

Supports the generation of Sine, Square and Ramp waves. 

The output waveforms can also be frequency, phase or amplitude modulated. The modulation source can
be another internally-generated Sinewave, the associated analog input channel or the other output channel.
That other output channel may itself be modulated in some way, allowing the creation of very complex
waveforms.

.. note:: 

	For frequencies over approximately 30MHz, the Square Wave can be subject to edge jitter due to the
	DDS technology used in the Moku:Lab. If this is a problem, and you don't need duty-cycle control,
	a clipped Sine Wave can provide better performance.


Example Usage
-------------

For an in-depth walkthrough on using the pymoku Signal Generator Instrument, see the `pymoku Signal Generator tutorial <http://confluence.liquidinstruments.com>`_. For the following example code and a wide range of other pymoku demo scripts, see the `pymoku example repository <https://anaconda.org/liquidinstruments/pymoku-examples>`_.

.. literalinclude:: ../examples/basic_siggen.py
	:language: python
	:caption: basic_siggen.py

The SignalGenerator Class
-------------------------

.. autoclass:: pymoku.instruments.SignalGenerator
	:members:
	:inherited-members:
