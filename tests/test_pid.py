import pytest, math, itertools
import conftest

import matplotlib
import matplotlib.pyplot as plt

from pymoku import Moku
from pymoku.instruments import PIDController, BodeAnalyser

BODE_SWEEP_AMPLITUDE = 0.1 # Vpp
BODE_SWEEP_MIN = 10 # Hz
BODE_SWEEP_MAX = 1e6 # Hz


@pytest.fixture(scope="module")
def base_instrs(conn_mokus):
	moku_master = conn_mokus[0]
	moku_slave = conn_mokus[1]
	print("Connecting to Mokus")

	master_bode = BodeAnalyser() # Benchmark
	slave_pid = PIDController() # Under test

	moku_master.deploy_instrument(master_bode, use_external=True) # Master is 10MHz reference clock
	moku_slave.deploy_instrument(slave_pid, use_external=False)

	# Set attenuation on Bode Analyser (10Vpp range) to avoid saturation
	master_bode.set_frontend(1,fiftyr=True, atten=False, ac=False)
	master_bode.set_frontend(2,fiftyr=True, atten=False, ac=False)
	slave_pid.set_frontend(1,fiftyr=True, atten=False, ac=False)
	slave_pid.set_frontend(2,fiftyr=True, atten=False, ac=False)

	return (master_bode,slave_pid)

@pytest.fixture(scope="module")
def calibration_trace(base_instrs):
	print("Calibrating PID test setup.")
	# A calibration run to remove effects of the connected system
	master = base_instrs[0]
	slave = base_instrs[1]

	master.set_output(1, BODE_SWEEP_AMPLITUDE)
	master.set_output(2, BODE_SWEEP_AMPLITUDE)
	master.set_sweep(BODE_SWEEP_MIN,BODE_SWEEP_MAX,sweep_points=512,averaging_time=0.002, settling_time=0.002, averaging_cycles=4, settling_cycles=4)
	master.start_sweep(single=True)

	calibration_data = master.get_data()
	print("Waveform ID of calibration trace: %d" % calibration_data.waveformid)
	
	return calibration_data

def to_dB(v):
	return 20*math.log(10,v)

def from_dB(db):
	return 10**(db/20.0)

class Test_PID:

	"""
	@pytest.mark.parametrize("p_dB, in_offset, out_offset",
	itertools.product(
		[-60,-20,-3,0,3,20,60],
		[-1.0, -0.2, 0, 0.2, 1.0],
		[-1.0, -0.2, 0, 0.2, 1.0]
		))
	"""
	@pytest.mark.parametrize("p_dB, in_offset, out_offset", [
		(0,0,0),
		(3,0,0)])
	def test_proportional(self, base_instrs, calibration_trace, p_dB, in_offset, out_offset):
		"""
			Tests the Proportional (gain only) setting of both PID channels with various offsets.

			:type p_dB: float;
			:param p_dB: Proportional gain for PIDs (in dB/amplitude gain)

			:type in_offset: float; V
			:param in_offset: Signal offset at input

			:type out_offset: float; V
			:param out_offset: Signal offset at output
		"""
		master = base_instrs[0]
		slave = base_instrs[1]

		# Set up the Bode Analyser to be 10Hz-1MHz, 100mVpp sweep
		master.set_output(1, BODE_SWEEP_AMPLITUDE)
		master.set_output(2, BODE_SWEEP_AMPLITUDE)
		master.set_sweep(BODE_SWEEP_MIN,BODE_SWEEP_MAX,sweep_points=512,averaging_time=0.002, settling_time=0.002, averaging_cycles=4, settling_cycles=4)

		# Set up the PID Controller
		slave.set_by_frequency(1, kp=from_dB(p_dB), in_offset=in_offset, out_offset=out_offset)
		slave.set_by_frequency(2, kp=from_dB(p_dB), in_offset=in_offset, out_offset=out_offset)

		# Wait a moment before initialising the sweep

		# Check what data is returned by this
		data = master.get_data()

		# Take a single sweep of the system under test
		master.start_sweep(single=True)

		while(data.waveformid)
		# Get the sweep data
		data = master.get_data()

		# Check the data
		plt.ion()
		plt.show()
		plt.plot(data.frequency, data.ch1.magnitude_dB)
		#plt.plot(data.ch2.magnitude)
		plt.plot(calibration_trace.frequency, calibration_trace.ch1.magnitude_dB)
		#plt.plot(calibration_trace.ch2.magnitude)
		plt.pause(10)

		assert False