
Moku:Lab Python Interface
=========================

pymoku is a Python library for the command, control and monitoring of Liquid Instruments
Moku:Lab devices.  This interface can suppliment or replace the default iPad interface,
allowing the Moku:Lab to be scripted tightly in to your next experiment.

.. warning:: This documents the 0.1 version of pymoku. The library is known to be incomplete
	and has several known issues. Not all functions documented here will necessarily work 
	as documented. Use at your own risk (but thank you in advance for your feedback!).

For example usage, see the individual instrument pages or the **examples/** subdirectory
of this project.

Installation
============

pymoku is currently only supported on Linux platforms though is expected to work on Mac OSX as well.

pymoku depends on the *pyzmq* and *future* libraries. It also packages the *pybonjour* library internally. These can be automatically installed from the requirements.txt as below.

In order to support automatic discovery of Moku:Lab devices, a DNS-SD compatible library must be installed. On
Linux platforms the relevant library is likely to be called *libavahi-compat-dnssd*.

No package exists for pymoku at the time of writing, source code should be downloaded from the Liquid Instruments `github page <https://github.com/liquidinstruments/pymoku>`_ (`direct download <https://github.com/liquidinstruments/pymoku/archive/master.zip>`_).

.. code-block:: shell

	#: unzip pymoku-master.zip
	#: cd pymoku-master
	#: pip install -r requirements.txt
	#: pip install .

Contents
========

.. toctree::
   :maxdepth: 2

   moku
   oscilloscope
   siggen
   specan
   phasemeter


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

