
import math
import logging

from pymoku._instrument import *
from pymoku._oscilloscope import _CoreOscilloscope, VoltsData
from . import _instrument
from ._pid import PID
from ._sweep import SweepGenerator
log = logging.getLogger(__name__)

REGBASE_LLB_DEMOD			= 23
REGBASE_LLB_SCAN			= 32
REGBASE_LLB_AUX_SINE		= 41

REG_LLB_RATE_SEL			= 76

REGBASE_LLB_PID1			= 106
REGBASE_LLB_PID2			= 117

_LLB_PHASESCALE				= 2**64 / 360.0
_LLB_FREQSCALE				= 2**64 / 1e9
_LLB_HIGH_RATE				= 0
_LLB_LOW_RATE				= 1

_LLB_COEFFICIENT_WIDTH		= 24


class LaserLockBox(_CoreOscilloscope):
	def __init__(self):
		super(LaserLockBox).__init__()
		self._register_accessors(_llb_reg_hdl)

		self.id = 16
		self.type = "laserlockbox"

		self.fast_fs = 31.25e6
		seld.slow_fs = 31.25e6

		self.fast_pid = PID(self, reg_base = REGBASE_LLB_PID1, self.fast_fs)
		self.slow_pid = PID(self, reg_base = REGBASE_LLB_PID2, self.slow_fs)

		self.demod_sweep = SweepGenerator(self, reg_base = REGBASE_LLB_DEMOD)
		self.scan_sweep = SweepGenerator(self, reg_base = REGBASE_LLB_SCAN)
		self.aux_sine_sweep = SweepGenerator(self, reg_base = REGBASE_LLB_AUX_SINE)
		SweepGenerator.step = 0
		SweepGenerator.stop = 2**64 -1
		SweepGenerator.duration = 0
		SweepGenerator.waveform = 2
		SweepGenerator.start = 0
		SweepGenerator.wait_for_trig = False
		SweepGenerator.hold_last = False

	@needs_commit
	def set_pid_by_gain(self, pid_block, g=1, kp=1, ki=0, kd=0, si=None, sd=None):
		"""

		Configure the selected PID controller using gain coefficients.

		:type ch: int; [1,2]
		:param ch: Channel of the PID controller to be configured.

		:type g: float; [0,2^16 - 1]
		:param g: Gain

		:type kp: float; [-1e3,1e3]
		:param kp: Proportional gain factor

		:type ki: float;
		:param ki: Integrator gain factor

		:type kd: float;
		:param kd: Differentiator gain factor

		:type si: float; float; [-1e3,1e3]
		:param si: Integrator gain saturation

		:type sd: float; [-1e3,1e3]
		:param sd: Differentiator gain saturation

		:raises InvalidConfigurationException: if the configuration of PID gains is not possible.
		"""
		pid_array = [self.fast_pid, self.slow_pid]
		pid_array[pid_block -1].set_reg_by_gain(g, kp, ki, kd, si, sd)

	@needs_commit
	def set_pid_by_freq(self, pid_block, kp=1, i_xover=None, d_xover=None, si=None, sd=None):
		"""

		Configure the selected PID controller using crossover frequencies.

		:type ch: int; [1,2]
		:param ch: PID controller to  configure

		:type kp: float; [-1e3,1e3]
		:param kp: Proportional gain factor

		:type i_xover: float; [1e-3,1e6] Hz
		:param i_xover: Integrator crossover frequency

		:type d_xover: float; [1,10e6] Hz
		:param d_xover: Differentiator crossover frequency

		:type si: float; float; [-1e3,1e3]
		:param si: Integrator gain saturation

		:type sd: float; [-1e3,1e3]
		:param sd: Differentiator gain saturation

		:raises InvalidConfigurationException: if the configuration of PID gains is not possible.
		"""
		pid_array = [self.fast_pid, self.slow_pid]
		pid_array[pid_block -1].set_reg_by_frequency(kp, i_xover, d_xover, si, sd)

	@needs_commit
	def set_demodulation(self, frequency, phase):
		"""
		Configure the demodulation stage.

		:type frequency : float; [0, 200e6] Hz
		:param frequency : Internal demodulation frequency

		:type phase : float; [0, 360] degrees
		:param phase : float; Internal demodulation phase

		"""
		self.demod_sweep.step = frequency * _LLB_FREQSCALE
		self.demod_phase.start = phase * _LLB_PHASESCALE

	@needs_commit
	def set_scan(self, frequency, phase):
		"""
		Configure the scan signal.

		:type frequency : float; [0, 200e6] Hz
		:param frequency : Internal demodulation frequency

		:type phase : float; [0, 360] degrees
		:param phase : float; Internal demodulation phase

		"""
		self.scan_sweep.step = frequency * _LLB_FREQSCALE
		seld.scan_sweep.phase = phase * _LLB_PHASESCALE

	@needs_commit
	def set_aux_sine(self, frequency, phase):
		"""
		Configure the aux sine signal.

		:type frequency : float; [0, 200e6] Hz
		:param frequency : Internal demodulation frequency

		:type phase : float; [0, 360] degrees
		:param phase : float; Internal demodulation phase

		"""
		self.aux_sine_sweep.step = frequency * _LLB_FREQSCALE
		seld.aux_sine_sweep.phase = phase * _LLB_PHASESCALE

	@needs_commit
	def set_sample_rate(self, rate):
		"""
		Configure the sample rate of the filters and pid controllers of the laser locker.
		
		selectable rates:
			-**high** : 62.5 MHz
			-**low**  : 31.25 MHz
		
		:type rate : string; {'high', 'low'}
		:param rate: sample rate

		"""
		_str_to_rate = {
			'high' 	: _LLB_HIGH_RATE,
			'low'	: _LLB_LOW_RATE
		}
		self.rate_sel = _utils.str_to_val(_str_to_rate, rate, 'sampling rate')




# NOTE: This function avoids @needs_commit because it calls _set_mmap_access which requires an immediate commit
	def set_filter(self, filter_coefficients):
		"""
		Set SOS filter sample rate and filter coefficients. This also enables the input and outputs of the specified Moku:Lab channel.

		:type ch: int; {1,2}
		:param ch: target channel

		:type filter_coefficients: array;
		:param filter_coefficients: array containing SOS filter coefficients. Format is described in class documentation above.
		"""
		_utils.check_parameter_valid('set', ch, [1, 2], 'filter channel')
		_utils.check_parameter_valid('set', sample_rate, ['high', 'low'], 'filter sample rate')


		# Conversion of input array (typically generated by Scipy/Matlab) to HDL memory map format
		if filter_coefficients != None:

			# Deep copy to avoid modifying user's original input array 
			intermediate_filter = deepcopy(filter_coefficients)

			# Array dimension check
			if len(filter_coefficients) != 5:
				_utils.check_parameter_valid('set', len(filter_coefficients), [5],'number of coefficient array rows')
			for m in range(4):
				if m == 0:
					if len(filter_coefficients[0]) != 1:
						_utils.check_parameter_valid('set', len(filter_coefficients[0]), [1],'number of columns in coefficient array row 0')
				else:
					if len(filter_coefficients[m]) != 6:
						_utils.check_parameter_valid('set', len(filter_coefficients[m]), [6],("number of columns in coefficient array row %s"%(m)))

			# Array values check
			_utils.check_parameter_valid('range', filter_coefficients[0][0], [-8e6,8e6 - 2**(-24)],("coefficient array entry m = %s, n = %s"%(0,0)))
			for m in range(1, 5):
				for n in range(6):
					_utils.check_parameter_valid('range', filter_coefficients[m][n], [-4.0,4.0 - 2**(-45)],("coefficient array entry m = %s, n = %s"%(0,0)))


			# multiply S coefficients into B coefficients and replace all S coefficients with 1.0
			for n in range(1,5):
				intermediate_filter[n][1] *= intermediate_filter[n][0]
				intermediate_filter[n][2] *= intermediate_filter[n][0]
				intermediate_filter[n][3] *= intermediate_filter[n][0]
				intermediate_filter[n][0] = 1.0

			# place gain factor G into S coefficient position 4 to comply with HDL requirements:
			intermediate_filter[4][0] = intermediate_filter[0][0]
			intermediate_filter = intermediate_filter[1:5]

			if ch == 1:
				self.filter_ch1 = intermediate_filter
			else:
				self.filter_ch2 = intermediate_filter

		# combine both filter arrays:
		filter_coeffs = [[0.0]*6]*4
		coeff_list = [ [ [0 for k in range(2)] for x in range(6)] for y in range(8) ]
		for n in range(4):
		 	filter_coeffs[n] = self.filter_ch1[n] + self.filter_ch2[n]

		for stage in range(4):
			for coeff in range(6):
				if coeff == 0:
					coeff_list[stage][coeff] = int(round( 2**(_LLB_COEFFICIENT_WIDTH - 24) * filter_coeffs[x][y + k*6]))
				else:
					coeff_list[stage][coeff] = int(round( 2**(_LLB_COEFFICIENT_WIDTH - 3) * filter_coeffs[x][y + k*6]))

		with open('.data.dat', 'wb') as f:
			for coeff in range(6):
				for stage in range(4):
					f.write(struct.pack('<q', coeff_list[stage][coeff]))

		self._set_mmap_access(True)
		self._moku._send_file('j', '.data.dat')
		self._set_mmap_access(False)
		os.remove('.data.dat')

		# Enable the output and input of the set channel
		if ch==1:
			self.output_en1 = True
			self.input_en1 = True
		else:
			self.output_en2 = True
			self.input_en2 = True

		# Manually commit the above register settings as @needs_commit is not used in this function
		self.commit()


	def _write_coeffs(self, ch, coeffs):
		assert ch in [1,2], "Invalid channel"
		assert len(coeffs) <= _FIR_NUM_BLOCKS * _FIR_BLOCK_SIZE, "Invalid number of filter coefficients."

		coeffs = list(coeffs)

		# Create a list of coefficients in each FIR block
		n = int(math.ceil(len(coeffs)/float(_FIR_NUM_BLOCKS)))
		blocks = [coeffs[x:x+n] for x in range(0, len(coeffs), n)]
		blocks += [[]] * (_FIR_NUM_BLOCKS - len(blocks))

		# Construct a bytearray from the FIR block contents
		coeff_bytes = bytearray()
		for b in blocks:
			b.reverse()
			coeff_bytes += bytearray(struct.pack('<I', len(b)))
			coeff_bytes += bytearray(struct.pack('<' + 'i'*len(b), *[int(round((2.0**24-1) * c)) for c in b]))
			coeff_bytes += bytearray(b'\x00'*4*(_FIR_BLOCK_SIZE-len(b)))

		# Sanity check the coefficient byte array length
		assert len(coeff_bytes) == (_FIR_BLOCK_SIZE+1) * _FIR_NUM_BLOCKS * 4, "Invalid length for FIR coefficient memory map."

		# Write the coefficients to the FIR coefficient memory map
		self._set_mmap_access(True)
		self._moku._send_file_bytes('j', '', coeff_bytes, offset=_FIR_MMAP_BLOCK_SIZE*(ch-1))
		self._set_mmap_access(False)

		# Release the memory map "file" to other resources
		self._moku._fs_finalise('j', '', _FIR_MMAP_BLOCK_SIZE*2)


_llb_reg_hdl = {
	'rate_sel':		(REG_LLB_RATE_SEL,	to_reg_unsigned(0, 1),
										from_reg_unsigned(0, 1)),
}