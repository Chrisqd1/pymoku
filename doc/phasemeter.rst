
Phasemeter Instrument
=====================

Phasemeter Instrument class.

The Phasemeter is different from other instruments in that its data is not presented in the form of frames
of presented data; instead, the data must be streamed to a file or live to pymoku over the network. This
stream contains a sequence of measurements of the form::

	( fs, f, count, phase, I, Q )

Where:

- **fs**: set-point frequency of the PLL
- **f**: measured frequency of the input signal
- **count**: the index of this measurement
- **phase**: the measured phase of the input signal
- **I**: in-phase amplitude component
- **Q**: quadrature amplitude component

The stream is accessed using the *datalogger_* functions; especially :any:`datalogger_start` and, if streaming
in real-time to pymoku over the network (rather than to a file), :any:`datalogger_get_samples`.

.. note:: The requirement to :any:`commit() <pymoku.instruments.Oscilloscope.commit>` before a change takes effect is the most common cause of program malfunctions when interfacing with the Moku:Lab. Any *set_* or *synth_* function, or any direct manipulation of attributes such as :any:`framerate`, must be explicitly committed.

Example Usage
-------------

.. TODO: Move back in to the source file?

.. code-block:: python

	from pymoku import Moku, NoDataException
	from pymoku.instruments import *
	import math

	m = Moku.get_by_name('example')
	i = PhaseMeter()
	m.deploy_instrument(i)

	try:
		# Set the initial phase-lock loop frequency to 10MHz and a measurement rate of 10Hz
		i.set_initfreq(1, 10000000)
		i.set_samplerate(10)
		i.commit()

		# Stop any previous measurement and recording sessions if any and start a new CSV recording
		# session, single channel, 10 seconds long to the SD card.
		i.datalogger_stop()
		i.datalogger_start(start=0, duration=10, use_sd=True, ch1=True, ch2=False, filetype='csv')

		while True:
			if i.datalogger_completed():
				break

		# Check if there were any errors
		e = i.datalogger_error()
		if e:
			print("Error occured: %s" % e)

		i.datalogger_stop()
	except Exception as e:
		print(e)
	finally:
		m.close()


The DataBuffer Class
--------------------

.. autoclass:: pymoku.instruments.DataBuffer

	.. Don't use :members: as it doesn't handle instance attributes well. Directives in the source code list required attributes directly.


The Phasemeter Class
--------------------

.. autoclass:: pymoku.instruments.PhaseMeter
	:members:
	:inherited-members:
