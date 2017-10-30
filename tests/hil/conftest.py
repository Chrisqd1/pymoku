from pymoku import Moku
from pymoku.instruments import *
import pytest

def pytest_addoption(parser):
	parser.addoption("--masterip", help="IP address of the master device to test against.")
	parser.addoption("--slaveip", help="IP address of the slave device to test against.")
	parser.addoption("--ip", help="IP address of the slave device to test against.")

@pytest.fixture(scope="session")
def conn_mokus(request):
	'''
		Connects to both Mokus used throughout tests
	'''
	print "Connecting to Mokus"
	masterip = pytest.config.getoption("--masterip")
	slaveip = pytest.config.getoption("--slaveip")
	m1 = Moku(masterip)
	m2 = Moku(slaveip)

	print("Master IP: %s" % masterip)
	print("Slave IP: %s" % slaveip)

	request.addfinalizer(m1.close)
	request.addfinalizer(m2.close)
	return (m1, m2)

@pytest.fixture(scope="session")
def conn_instr(request):
	ip = pytest.config.getoption("--ip")

	print "Connecting to Moku"
	moku = Moku(ip)
	instr = PIDController()
	moku.deploy_instrument(instr)

	request.addfinalizer(moku.close)
	return instr