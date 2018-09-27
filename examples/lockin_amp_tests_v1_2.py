import pytest
from pymoku import *
from pymoku.instruments import LockInAmp, Oscilloscope
import time
#logging.basicConfig(level=logging.DEBUG)
import numpy as np
import math

#############

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

######## Helper Functions ########

def sum_square_diffs(zs):
	sum_squares = 0
	mz = sum(zs)/len(zs)
	i = 0
	for z in zs:
		i += 1
		sum_squares += (z - mz)**2
	return sum_squares

def determine_r (xs, ys, d):
	mx = sum(xs)/len(xs)
	my = sum(ys)/len(ys)
	double_ys = []
	double_ys.extend(ys)
	double_ys.extend(ys)
	i = 0
	numerator = 0
	while i < len(xs):
		numerator += (xs[i] - mx)*(double_ys[i+d] - my)
		i +=1
	r = numerator / (np.sqrt(sum_square_diffs(xs) * sum_square_diffs(ys)))
	return r
	
def r_series (xs, ys):
	assert isinstance (xs[0], float) or isinstance(ys[0], float), "input series must be floats"
	assert len(xs) <= len(ys), "The first series must be shorter or same size as the second series"
	d = 0
	rs = []
	for x in xs:
		rs.append(determine_r(xs, ys, d))
		d += 1
	return rs

def find_best_r (xs, ys):
	r_max = max(r_series(xs, ys))
	return r_max

def construct_sinewave (amplitude,frequency, phase, offset, point_number): 
	sine = np.zeros(point_number)
	i = 0
	while i < point_number:
		sine[i] = amplitude * np.sin (2*np.pi*adjusted_frequency(frequency)* float(i)/point_number + phase) + offset
		i += 1
	return sine

def construct_rampwave (amplitude, offset, point_number):
	ramp = np.zeros(point_number)
	i = 0
	m = 2*amplitude/(1023-0)
	while i < point_number:
		ramp[i] =m * i - amplitude + offset
		i += 1
	return ramp

def adjusted_frequency (frequency):
	if frequency < 491850:
		return 1
	else:
		return float(frequency)/491850
######## Moku Connections ########

@pytest.fixture(scope = "module", params = ['65540'])
def oscill (request):
	m = Moku.get_by_serial(request.param)
	m.set_led_colour('red')	
	i = m.deploy_or_connect(Oscilloscope)
	i.gen_sinewave(1, 0.5, 10e6)
	i. gen_squarewave(2, 0.5, 10.0003e6)
	def close_Moku():
		m.set_led_colour('aqua')
		m.close()
	request.addfinalizer(close_Moku)
	return i

@pytest.fixture(scope = "module", params = ['41178'])
def lockin_amp (request):
	m = Moku.get_by_serial(request.param)
	m.set_led_colour('red')
	def close_Moku():
		m.set_led_colour('aqua')
		m.close()
	request.addfinalizer(close_Moku)
	return m.deploy_or_connect(LockInAmp)

######## Functions that Perform Tests ########

@pytest.fixture(params = [(1, 100, 1e-1), (2, 100, 1e-1), (1, 20e6, 2e-1), (2, 20e6, 2e-1)])
def monitor_I_and_Q (request):
	(channel, test_frequency, tolerance) = request.param
	sine_series = construct_sinewave (500e3, test_frequency,0.0, 0.0, 1024) 

	def _monitor_I_and_Q (lockin_amp, oscill):
		oscill.gen_sinewave(1, 500e-3, 10e6)
		oscill.gen_squarewave(2, 500e-3, 10.0003e6)
		if test_frequency == 100:
			timebase = 1.0/100
		else:
			timebase = 1.0/491850

		lockin_amp.set_timebase(0.0, timebase)
		lockin_amp.set_demodulation('internal', 10.0001e6) # set local oscillator to 10.0001 MHz. (100 Hz offset from the raw_input)
		lockin_amp.set_outputs('x', 'demod')
		lockin_amp.set_monitor('a','I') # set channel 1 of scope to view 'i'
		lockin_amp.set_monitor('b','Q') # set channel 2 of scope to view 'q'
		lockin_amp.commit()
		time.sleep(0.5)
		raw_data = lockin_amp.get_realtime_data() # get data from monitors
		if channel == 1:
			data = raw_data.ch1
		else: 
			data = raw_data.ch2
		if test_frequency == 20e6:
			i = 0
		r_value = 1 - find_best_r(sine_series, data)
		print r_value
		return r_value < tolerance
	return _monitor_I_and_Q

@pytest.fixture(params = [('r', 1.0e-2), ('theta', 1.0e-2)])
def monitor_R_and_Theta (request):
	(test_coordinate, shape_tolerance)= request.param
	def _monitor_R_And_Theta (lockin_amp, oscill):
		oscill.gen_sinewave(1, 500e-3, 10e6)
		oscill.gen_squarewave(2, 500e-3, 10.0003e6)

		lockin_amp.set_timebase(0.0, 1.0/100)
		lockin_amp.set_demodulation('internal', 10.0001e6) # set local oscillator to 10.0001 MHz. (100 Hz offset from the raw_input)
		lockin_amp.set_outputs(test_coordinate, 'demod')
		lockin_amp.set_monitor('a','main') # set channel 1 of scope to view 'i'
		lockin_amp.set_monitor('b', 'none')
		lockin_amp.set_filter(1e3, 1)
		lockin_amp.set_gain('main', 0.0)
		lockin_amp.commit()
		time.sleep(0.5)
		raw_data = lockin_amp.get_realtime_data()
		data = raw_data.ch1
		if test_coordinate == 'r':
			r_value =  max(data)-min(data)
		else:
			r_value  = 1 - find_best_r(construct_rampwave(0.4, 0.0, 1024), data)
		print r_value
		return r_value < shape_tolerance

	return _monitor_R_And_Theta

@pytest.fixture(params = [(100, 1e-2, 250e-3, 2e-2)])
def output_Q_voltage(request):
	(frequency, shape_frequency_tolerance, amplitude_ptp, amplitude_tolerance) = request.param
	def _output_Q_voltage(lockin_amp, oscill):
		oscill.gen_sinewave(1, 500e-3, 10e6)
		oscill.gen_squarewave(2, 500e-3, 10.0003e6)
		oscill.set_timebase(0.0, 1.0/100)
		oscill.commit()
		lockin_amp.set_demodulation('internal', 10.0001e6,0)
		lockin_amp.set_filter(1e3, 1)
		lockin_amp.set_outputs('x', 'y')
		lockin_amp.commit()
		time.sleep(0.1)
		sine = construct_sinewave (250.0/2, frequency, 0.0, 0.0, 1024)
		raw_data = oscill.get_realtime_data()
		data = raw_data.ch1
		print data
		r_value = 1 - find_best_r(sine, data)
		a_value = abs(amplitude_ptp-(max(data)-min(data)))
		print r_value
		print a_value
		return r_value < shape_frequency_tolerance and a_value < amplitude_tolerance
	return _output_Q_voltage

@pytest.fixture(params = [(100, 1e-2, 250e-3, 1e-2)])
def output_I_voltage(request):
	(frequency, shape_frequency_tolerance, amplitude_ptp, amplitude_tolerance) = request.param
	def _output_I_voltage(lockin_amp, oscill):
		oscill.gen_sinewave(1, 500e-3, 10e6)
		oscill.gen_squarewave(2, 500e-3, 10.0003e6)
		oscill.set_timebase(0.0, 1.0/100)
		oscill.commit()
		lockin_amp.set_demodulation('internal', 10.0001e6,0)
		lockin_amp.set_filter(1e3, 1)
		lockin_amp.set_outputs('x', 'y')
		lockin_amp.commit()
		time.sleep(0.1)
		sine = construct_sinewave (250.0/2, frequency, 0.0, 0.0, 1024)
		raw_data = oscill.get_realtime_data()
		data = raw_data.ch2
		print data
		r_value = 1 - find_best_r(sine, data)
		a_value = abs(amplitude_ptp-(max(data)-min(data)))
		print r_value
		print a_value
		return r_value < shape_frequency_tolerance and a_value < amplitude_tolerance
	return _output_I_voltage

@pytest.fixture(params = [(1e-2, 125e-3, 2e-2)])
def output_R_voltage(request):
	(variance_tolerence, offset, offset_tolerance) = request.param
	def _output_R_voltage(lockin_amp, oscill):
		oscill.gen_sinewave(1, 500e-3, 10e6)
		oscill.gen_squarewave(2, 500e-3, 10.0003e6)
		oscill.set_timebase(0.0, 1.0/100)
		oscill.commit()
		lockin_amp.set_demodulation('internal', 10.0001e6,0)
		lockin_amp.set_filter(1e3, 1)
		lockin_amp.set_outputs('r', 'theta')
		lockin_amp.commit()
		raw_data = oscill.get_realtime_data()
		data = raw_data.ch1
		print data
		r_value =  max(data)-min(data)
		o_value = offset - sum(data)/len(data)
		print r_value
		print o_value 
		return r_value < variance_tolerence and o_value < offset_tolerance
	return _output_R_voltage

@pytest.fixture(params = [(100, 1e-2, 800e-3, 3e-2)])
def output_Theta_voltage(request):
	(frequency, shape_frequency_tolerance, amplitude_ptp, amplitude_tolerance) = request.param
	def _output_Theta_voltage(lockin_amp, oscill):
		oscill.gen_sinewave(1, 500e-3, 10e6)
		oscill.gen_squarewave(2, 500e-3, 10.0003e6)
		oscill.set_timebase(0.0, 1.0/100)
		oscill.commit()
		lockin_amp.set_demodulation('internal', 10.0001e6,0)
		lockin_amp.set_filter(1e3, 1)
		lockin_amp.set_outputs('r', 'theta')
		lockin_amp.commit()
		raw_data = oscill.get_realtime_data()
		data = raw_data.ch2
		print data
		r_value = 1 - find_best_r(construct_rampwave(1.0, 0.0, 1024), data)
		a_value = abs(amplitude_ptp - (max(data) - min(data)))
		print r_value
		print a_value
		return r_value < shape_frequency_tolerance and a_value < amplitude_tolerance
	return _output_Theta_voltage

@pytest.fixture(params = [(10.0001e6, 1e-2, 500e-3, 3e-2)])
def local_oscill (request):
	(frequency, shape_frequency_tolerance, amplitude_ptp, amplitude_tolerance) = request.param
	def _local_oscill(lockin_amp, oscill):
		oscill.set_timebase(0.0, 1.0/491850)
		oscill.set_source(2, 'in2')
		oscill.set_trigger('in2', 'rising', 0, hysteresis = 0.1)
		lockin_amp.set_outputs('x', 'sine')
		lockin_amp.set_lo_output(500e-3, 10.0001e6, 0.0)
		lockin_amp.commit()
		raw_data = oscill.get_realtime_data()
		data = raw_data.ch2
		print data
		sine = construct_sinewave (amplitude_ptp, frequency, 0.0, 0.0, 1024)
		r_value = 1 - find_best_r(sine, data)
		a_value = abs(amplitude_ptp - (max(data) - min (data)))
		print r_value
		print a_value
		return r_value < shape_frequency_tolerance and a_value < amplitude_tolerance
	return _local_oscill

@pytest.fixture(params = [(300, 1e-2, 125e-3, 2e-2)])
def external_demod (request):
	(frequency, shape_frequency_tolerance, amplitude_ptp, amplitude_tolerance) = request.param
	def _external_demod (lockin_amp, oscill):
		oscill.gen_sinewave(1, 500e-3, 10e6)
		oscill.gen_sinewave(2, 500e-3, 10.0003e6)
		oscill.set_timebase(0.0, 1.0/frequency)
		oscill.set_source(2, 'in1')
		oscill.set_trigger('in1', 'rising', 0, hysteresis = 0.1)
		oscill.commit()
		lockin_amp.set_demodulation("external")
		lockin_amp.set_frontend(1, fiftyr=True, atten=False, ac=True)
		lockin_amp.set_monitor('a', 'main')
		lockin_amp.set_gain('main', 0.0)
		lockin_amp.commit()
		raw_data = oscill.get_realtime_data()
		data = raw_data.ch1
		print data
		sine = construct_sinewave (amplitude_ptp, frequency, 0.0, 0.0, 1024)
		r_value = 1 - find_best_r(sine, data)
		a_value = abs(amplitude_ptp - (max(data) - min (data)))
		print r_value
		print a_value
		return r_value < shape_frequency_tolerance and a_value < amplitude_tolerance
	return _external_demod

@pytest.fixture(params = [(300, 1e-2, 250e-3, 2e-2)])
def external_demod_PLL (request):
	(frequency, shape_frequency_tolerance, amplitude_ptp, amplitude_tolerance) = request.param
	def _external_demod_PLL (lockin_amp, oscill):
		oscill.gen_sinewave(1, 500e-3, 10e6)
		oscill.gen_squarewave(2, 10e-3, 10.0003e6)
		oscill.set_timebase(0.0, 1.0/frequency)

		oscill.commit()
		lockin_amp.set_demodulation("external_pll")
		lockin_amp.set_frontend(1, fiftyr=True, atten=False, ac=True)
		lockin_amp.set_monitor('a', 'main')
		lockin_amp.set_gain('main', 0.0)
		lockin_amp.commit()
		raw_data = oscill.get_realtime_data()
		data = raw_data.ch1
		print data
		sine = construct_sinewave (amplitude_ptp, frequency, 0.0, 0.0, 1024)
		r_value = 1 - find_best_r(sine, data)
		a_value = abs(amplitude_ptp - (max(data) - min (data)))
		print r_value
		print a_value
		return r_value < shape_frequency_tolerance and a_value < amplitude_tolerance
	return _external_demod_PLL

@pytest.fixture(params=['XY', 'RT'])
def filtered_signal_auxiliary_output (request):
	coords = request.param
	phase_tolerence = 1e-2
	shape_frequency_tolerance = 1e-2
	amplitude_tolerance = 2e-2
	def _filtered_signal_auxiliary_output (lockin_amp, oscill):
		oscill.gen_sinewave(1, 500e-3, 10e6)
		oscill.gen_squarewave(2, 500e-3, 10.0003e6)
		oscill.set_timebase(0.0, 1.0/300)
		oscill.set_trigger('in1', 'rising', 0)
		oscill.commit()
		lockin_amp.set_timebase(0.0, 1.0/300)
		lockin_amp.set_demodulation("external_pll")
		lockin_amp.set_frontend(1, fiftyr=True, atten=False, ac=False)
		lockin_amp.set_frontend(2, fiftyr=True, atten=False, ac=True)

		lockin_amp.set_trigger('A', 'rising', 0)
		if coords == 'XY':
			lockin_amp.set_outputs('x','y')
		else:
			lockin_amp.set_outputs('r','theta')

		lockin_amp.set_monitor('A', 'aux')		
		lockin_amp.set_monitor('B', 'main')

		lockin_amp.set_gain('main', 0.0)
		lockin_amp.set_gain('aux', 0.0)
		lockin_amp.commit()
		time.sleep(0.1)
		data_lockin = lockin_amp.get_realtime_data()
		data_oscill = oscill.get_realtime_data()
		print data_lockin.ch1
		print data_lockin.ch2
		out_of_phase_90 = True
		ch1_consistent = True
		ch2_consistent = True
		if coords =='XY':
			find_90_r_value = abs(determine_r(data_oscill.ch1, data_oscill.ch2, 0))
			#print find_90_r_value
			out_of_phase_90 = find_90_r_value < phase_tolerence
		ch1_r_value = 1 - find_best_r(data_oscill.ch1, data_lockin.ch1)
		ch1_a_value = (max(data_oscill.ch1) - min(data_oscill.ch1)) - (max(data_lockin.ch1) - min(data_lockin.ch1))
		ch2_r_value = 1 - find_best_r(data_oscill.ch2, data_lockin.ch2)
		ch2_a_value = (max(data_oscill.ch2) - min(data_oscill.ch2)) - (max(data_lockin.ch2) - min(data_lockin.ch2))
		#print ch1_r_value
		#print ch1_a_value
		#print ch2_r_value
		#print ch2_a_value
		ch1_consistent = ch1_r_value < shape_frequency_tolerance and ch1_a_value < amplitude_tolerance
		ch2_consistent = ch2_r_value < shape_frequency_tolerance and ch2_a_value < amplitude_tolerance
		return out_of_phase_90 and ch1_consistent and ch2_consistent
	return _filtered_signal_auxiliary_output

@pytest.fixture(params = [500e-3, 300e-3, 100e-3, 50e-3, 10e-3])
def demod_signal_auxiliary_output (request):
	shape_frequency_tolerance = 1e-2
	amplitude_tolerance = 1e-1
	expected_ptp_amplitude = 500e-3
	def _demod_signal_auxiliary_output (lockin_amp, oscill):
		oscill.gen_sinewave(1, 500e-3, 10e6)
		oscill.gen_squarewave(2, 10e-3, 10.0003e6)
		oscill.set_trigger('in2', 'rising', 0)
		oscill.set_timebase(0.0, 1.0/491850)
		oscill.commit()
		lockin_amp.set_timebase(0.0, 1.0/300)
		lockin_amp.set_demodulation("external_pll")
		lockin_amp.set_frontend(1, fiftyr=True, atten=False, ac=False)
		lockin_amp.set_frontend(2, fiftyr=True, atten=False, ac=True)

		lockin_amp.set_trigger('A', 'rising', 0)
		lockin_amp.set_outputs('x','demod')
		lockin_amp.set_monitor('A', 'aux')		
		lockin_amp.set_monitor('B', 'demod')

		lockin_amp.set_gain('main', 0.0)
		lockin_amp.set_gain('aux', 0.0)
		lockin_amp.commit()
		oscill_data = oscill.get_realtime_data()
		lockin_data = lockin_amp.get_realtime_data()
		print oscill_data.ch2
		print lockin_data.ch1
		sine = construct_sinewave(1,10e6, 0.0, 0.0, 1024)
		r_value = 1 - find_best_r(lockin_data.ch1, oscill_data.ch2)
		a_value = abs((max(lockin_data.ch2) - min(lockin_data.ch2)) - (max(oscill_data.ch2) - min(oscill_data.ch2)))
		print r_value
		print a_value
		return shape_frequency_tolerance > r_value and amplitude_tolerance > a_value
	return _demod_signal_auxiliary_output


######## tests called by pytest ########

def test_monitor_I_and_Q (monitor_I_and_Q, lockin_amp, oscill):
	assert monitor_I_and_Q(lockin_amp, oscill)
	assert 0

# @pytest.mark.skip(reason="no way of currently testing this")
def test_monitor_R_and_Theta (monitor_R_and_Theta, lockin_amp, oscill):
	assert monitor_R_and_Theta(lockin_amp, oscill)
	assert 0

# @pytest.mark.skip(reason="no way of currently testing this")
def test_output_Q_voltage (output_Q_voltage, lockin_amp, oscill):
	assert output_Q_voltage (lockin_amp, oscill)
	assert 0

# @pytest.mark.skip(reason="no way of currently testing this")
def test_output_I_voltage (output_I_voltage, lockin_amp, oscill):
	assert output_I_voltage (lockin_amp, oscill)
	assert 0

@pytest.mark.skip(reason="no way of currently testing this")
def test_output_R_voltage (output_R_voltage, lockin_amp, oscill):
	assert output_R_voltage (lockin_amp, oscill)	
	assert 0

@pytest.mark.skip(reason="no way of currently testing this")
def test_output_Theta_voltage (output_Theta_voltage, lockin_amp, oscill):
	assert output_Theta_voltage (lockin_amp, oscill)
	assert 0

@pytest.mark.skip(reason="no way of currently testing this")
def test_local_oscill (local_oscill, lockin_amp, oscill):
	assert local_oscill(lockin_amp, oscill)
	assert 0

@pytest.mark.skip(reason="no way of currently testing this")
def test_external_demod (external_demod, lockin_amp, oscill):
	assert external_demod(lockin_amp, oscill)
	assert 0

@pytest.mark.skip(reason="no way of currently testing this")
def test_external_demod_PLL (external_demod_PLL, lockin_amp, oscill):
	assert external_demod_PLL(lockin_amp, oscill)
	assert 0

@pytest.mark.skip(reason="no way of currently testing this")
def test_filtered_signal_aux_output (filtered_signal_auxiliary_output, lockin_amp, oscill):
	assert filtered_signal_auxiliary_output(lockin_amp, oscill)
	assert 0

@pytest.mark.skip(reason="no way of currently testing this")
def test_demod_signal_aux_output (demod_signal_auxiliary_output, lockin_amp, oscill):
	assert demod_signal_auxiliary_output(lockin_amp, oscill)
	assert 0
