
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

For logging data to a file, the *data_log* type functions should be used (see the `basic_phasemeter.py` example below). For networking streaming, the *stream_data* type functions should be used (see the `realtime_phasemeter.py` example below). 

Example Usage
-------------

.. literalinclude:: ../examples/basic_phasemeter.py
	:language: python
	:caption: basic_phasemeter.py

.. literalinclude:: ../examples/realtime_phasemeter.py
	:language: python
	:caption: realtime_phasemeter.py

The Phasemeter Class
--------------------

.. autoclass:: pymoku.instruments.Phasemeter
	:members:
	:inherited-members:
