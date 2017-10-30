
Phasemeter Instrument
=====================

The Phasemeter instrument is used to measure the amplitude and change in phase of periodic input signals. Using the auto-acquire feature, it can automatically lock to input frequencies in the range of 2-200MHz and track phase with a bandwidth of 10kHz. 

The Phasemeter is different from other instruments in that its data is not presented in the form of frames; instead, it is supplied as a stream of samples which may be logged to a file or streamed live to pymoku over the network. Each data sample is presented as a sequence of measurements of the form::

	( fs, f, count, phase, I, Q )

Where:

- **fs**: set-point frequency of the PLL (Hz)
- **f**: measured frequency of the input signal (Hz)
- **count**: the index of this measurement (n)
- **phase**: the measured phase of the input signal (cycles)
- **I**: in-phase amplitude component (V)
- **Q**: quadrature amplitude component (V)

.. note::
	For the output phase measure of a channel to be valid, it's tracking loop (PLL) must be "locked" to the input signal. A channel's PLL is considered to be "locked" if the ratio **I/Q** is large. That is, **Q ~ 0**. Note that the exact ratio depends upon the SNR of your signal. 


For logging data to a file, the *data_log* type functions should be used (see the `phasemeter_basic.py` example below). For networking streaming, the *stream_data* type functions should be used (see the `realtime_phasemeter.py` example script). 

Example Usage
-------------

For an in-depth walkthrough on using the pymoku Phasemeter Instrument, see the `pymoku Phasemeter tutorial <https://liquidinstruments.atlassian.net/wiki/display/MCS/The+Phasemeter>`_. For the following example code and a wide range of other pymoku demo scripts, see the `pymoku example repository <https://anaconda.org/liquidinstruments/pymoku-examples/files>`_.

.. literalinclude:: ../examples/phasemeter_basic.py
	:language: python
	:caption: phasemeter_basic.py

The Phasemeter Class
--------------------

.. autoclass:: pymoku.instruments.Phasemeter
	:members:
	:inherited-members:
