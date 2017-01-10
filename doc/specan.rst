
Moku:Lab Spectrum Analyser
==========================

Spectrum Analyser Instrument class.

This instrument provides frequency-domain analysis of input signals. It features switchable window functions, resolution bandwidth, averaging modes and more.

.. note:: The requirement to :any:`commit() <pymoku.instruments.Oscilloscope.commit>` before a change takes effect is the most common cause of program malfunctions when interfacing with the Moku:Lab. Any *set_* or *synth_* function, or any direct manipulation of attributes such as :any:`framerate`, must be explicitly committed.

Example Usage
-------------

.. TODO: Move back in to the source file?

.. code-block:: python

	from pymoku import Moku
	from pymoku.instruments import *

	m = Moku.get_by_name('example')
	i = SpecAn()
	m.attach_instrument(i)

	# DC to 100MHz span, apply changes
	i.set_span(0, 10000000)
	i.commit()

	# Get the scan results and print them out (power vs frequency, two channels)
	print(i.get_frame())

	# Close the connection to the Moku.
	m.close()

The SpectrumFrame Class
-----------------------

.. autoclass:: pymoku.instruments.SpectrumFrame

	.. Don't use :members: as it doesn't handle instance attributes well. Directives in the source code list required attributes directly.

The SpecAn Class
----------------

.. autoclass:: pymoku.instruments.SpecAn
	:members:
	:inherited-members:
