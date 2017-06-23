
Bode Analyser Instrument
============================

This instrument measures the transfer function of a system by generating a swept output sinewave and measuring the system response on the input. 

Example Usage
-------------

For the following example code and a wide range of other pymoku demo scripts, see the `pymoku example repository <https://anaconda.org/liquidinstruments/pymoku-examples>`_.

.. literalinclude:: ../examples/basic_bodeanalyser.py
	:language: python
	:caption: basic_bodeanalyser.py

The BodeData Class
-----------------------

.. autoclass:: pymoku.instruments.BodeData

	.. Don't use :members: as it doesn't handle instance attributes well. Directives in the source code list required attributes directly.


The BodeAnalyser Class
--------------------------

.. autoclass:: pymoku.instruments.BodeAnalyser
	:members:
	:inherited-members:
