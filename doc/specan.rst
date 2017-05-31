
Spectrum Analyser Instrument
============================

This instrument provides frequency-domain analysis of input signals. It features switchable window functions, resolution bandwidth, averaging modes and more.

Example Usage
-------------

For an in-depth walkthrough on using the pymoku Spectrum Analyser Instrument, see the `pymoku Spectrum Analyser tutorial <http://confluence.liquidinstruments.com>`_. For the following example code and a wide range of other pymoku demo scripts, see the `pymoku example repository <https://anaconda.org/liquidinstruments/pymoku-examples/files>`_.

.. literalinclude:: ../examples/basic_specan.py
	:language: python
	:caption: basic_specan.py

The SpectrumData Class
-----------------------

.. autoclass:: pymoku.instruments.SpectrumData

	.. Don't use :members: as it doesn't handle instance attributes well. Directives in the source code list required attributes directly.


The SpectrumAnalyser Class
--------------------------

.. autoclass:: pymoku.instruments.SpectrumAnalyser
	:members:
	:inherited-members:
