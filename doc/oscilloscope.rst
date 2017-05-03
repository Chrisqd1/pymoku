
Oscilloscope Instrument
=======================

The Oscilloscope instrument provides time-domain views of voltages. It contains a built-in Waveform Generator that can control the Moku:Lab analog outputs as well.

In normal operation, the Oscilloscope shows the signal present on the two analog inputs but it can be set to loop back the signals being synthesised. This loopback takes up a channel (only two signals in total may be viewed at once).  Data is provided at the :any:`Oscilloscope.framerate` in the form of :any:`VoltsFrame` objects. These objects contain the channel data and the required metadata to interpret them.

The Oscilloscope instrument also provides a facility for datalogging. The user should put the instrument in to Roll mode and turn the span down such that fewer than 10kS/s are being generated; then the datalogger may be enabled and all raw data points will be saved to the Moku:Lab's SD card.

Many functions or attributes must be :any:`commit()'d <pymoku.instruments.Oscilloscope.commit>` before taking effect. This allows you to set multiple settings across multiple calls and have them take effect atomically (e.g. set all output waveforms and input sampling at once).

.. note:: The requirement to :any:`commit() <pymoku.instruments.Oscilloscope.commit>` before a change takes effect is the most common cause of program malfunctions when interfacing with the Moku:Lab. Any *set_* or *gen_* function, or any direct manipulation of attributes such as :any:`Oscilloscope.framerate`, must be explicitly committed.

Example Usage
-------------

.. TODO: Move back in to source file?

.. code-block:: python

		from pymoku import Moku
		from pymoku.instruments import *

		# Can directly call the constructor with an IP address, or use
		# get_by_name or get_by_serial for autodiscovery.
		m = Moku.get_by_name('Moku')
		i = Oscilloscope()
		m.deploy_instrument(i)

		try:
			# Span from -1s to 1s i.e. trigger point centred
			i.set_timebase(-1, 1)
			i.commit()

			# Get and print a single frame's worth of data (time series
			# of voltage per channel)
			print(i.get_frame())

		finally:
			m.close()



The VoltsData Class
--------------------

.. autoclass:: pymoku.instruments.VoltsData

	.. Don't use :members: as it doesn't handle instance attributes well. Directives in the source code list required attributes directly.

The Oscilloscope Class
----------------------

.. autoclass:: pymoku.instruments.Oscilloscope
	:members:
	:inherited-members:

