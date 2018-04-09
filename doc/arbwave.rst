
Arbitrary Waveform Generator Instrument
=======================================

The Arbitrary Waveform Generator takes a time-series of voltage values, and generates the corresponding
waveform at the DACs at a configurable rate.

The API for the AWG is made of two parts: :any:`write_lut` defines the shape of the wave, while
:any:`gen_waveform` defines the speed and amplitude of the wave along with other parameters such
as interpolation, dead time and so on.

You must call both functions at least once in order to generate a waveform.

Example Usage
-------------

The following example code and a wide range of other pymoku demo scripts can be found at the `pymoku Github repository <https://github.com/liquidinstruments/pymoku>`_.

.. literalinclude:: ../examples/arbitrarywavegen_basic.py
	:language: python
	:caption: arbitrarywaveformgen_basic.py

The ArbitraryWaveGen Class
--------------------------

.. autoclass:: pymoku.instruments.ArbitraryWaveGen
	:members:

.. Intentionally leave out inheritedmembers, there's an Oscilloscope object in here which isn't fully-supported.
