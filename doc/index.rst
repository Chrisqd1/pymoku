.. pymoku documentation master file, created by
   sphinx-quickstart on Mon Nov 23 17:40:59 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

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


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

