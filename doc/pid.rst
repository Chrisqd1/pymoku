
PID Controller Instrument
============================

The PID Controller allows for dual channel (independent or MIMO) control of voltage-input,
voltage-output signals. The PID includes a double-integrator and fully-configurable integrator
saturation (anti-windup) and differentiator saturation.

Example Usage
-------------

.. literalinclude:: ../examples/pidcontroller_basic.py
	:language: python
	:caption: pidcontroller_basic.py

The Lock-In Class
----------------------

.. autoclass:: pymoku.instruments.PIDController
	:members:
	:inherited-members:

