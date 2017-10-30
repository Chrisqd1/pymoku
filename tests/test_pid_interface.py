from pymoku import Moku  
from pymoku.instruments import PIDController

import pytest, conftest

class Test_PID:

	@pytest.fixture
	def instr(self, conn_instr):
		# Reset the settings before every test
		conn_instr.set_defaults()
		return conn_instr

	"""
	@pytest.fixture
	def pause_test(self, pytestconfig):
	    capmanager = pytestconfig.pluginmanager.getplugin('capturemanager')
	    capmanager.suspendcapture(in_=True)
	    input('Disconnect component, then press enter')
	    capmanager.resumecapture()
	"""
	def test_set_by_frequency_noparams(self, instr):
		instr.set_by_frequency(1)
		instr.set_by_frequency(2)

	@pytest.mark.parametrize("p, in_offset, out_offset", [
		(0,0,0),
		(1,0,0),
		(0,0.2,0.5)])
	def test_proportional(self, instr, p, in_offset, out_offset):
		"""
			Tests the PID proportional gain and in/out offsets of both channels
		"""
		instr.set_by_frequency(1, kp=p, in_offset=in_offset, out_offset=out_offset)
		instr.set_by_frequency(2, kp=p, in_offset=in_offset, out_offset=out_offset)

	@pytest.mark.parametrize("i, ii, si, in_offset, out_offset", [
		(0,0,0,0,0)])
	def test_integrator(self, instr, i, ii, si, in_offset, out_offset):
		"""
			Tests the Integrator of both channels
		"""

		assert True

	"""
	@pytest.mark.parametrize("ch, g1, g2", [
		(1,0),
		(0,1),
		(0,0),
		(-20,20),
		(20,-20),
		(5,5)])
	"""
	#def test_control_matrix(self, instr, ch, g1, g2):



	#def test_invalid_control_matrix(self, instr, )