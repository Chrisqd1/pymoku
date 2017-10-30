
Spectrum Analyzer Instrument
============================

This instrument provides frequency-domain analysis of input signals. It features switchable window functions, resolution bandwidth, averaging modes and more.

Example Usage
-------------

For an in-depth walkthrough on using the pymoku Spectrum Analyzer Instrument, see the `pymoku Spectrum Analyzer tutorial <https://liquidinstruments.atlassian.net/wiki/display/MCS/The+Spectrum+Analyser>`_. For the following example code and a wide range of other pymoku demo scripts, see the `pymoku example repository <https://anaconda.org/liquidinstruments/pymoku-examples/files>`_.

.. literalinclude:: ../examples/spectrumanalyzer_basic.py
	:language: python
	:caption: spectrumanalyzer_basic.py

The SpectrumData Class
-----------------------

.. autoclass:: pymoku.instruments.SpectrumData

	.. Don't use :members: as it doesn't handle instance attributes well. Directives in the source code list required attributes directly.


The SpectrumAnalyzer Class
--------------------------

.. autoclass:: pymoku.instruments.SpectrumAnalyzer
	:members:
	:inherited-members:
