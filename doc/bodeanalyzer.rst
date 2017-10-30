
Bode Analyzer Instrument
============================

This instrument measures the transfer function of a system by generating a swept output sinewave and measuring the system response on the input. 

Example Usage
-------------

For the following example code and a wide range of other pymoku demo scripts, see the `pymoku example repository <https://anaconda.org/liquidinstruments/pymoku-examples>`_.

.. literalinclude:: ../examples/bodeanalyzer_basic.py
	:language: python
	:caption: bodeanalyzer_basic.py

The BodeData Class
-----------------------

.. autoclass:: pymoku.instruments.BodeData

	.. Don't use :members: as it doesn't handle instance attributes well. Directives in the source code list required attributes directly.


The BodeAnalyzer Class
--------------------------

.. autoclass:: pymoku.instruments.BodeAnalyzer
	:members:
	:inherited-members:
