from pymoku import Moku
from pymoku.instruments import *
import pytest

def pytest_addoption(parser):
	parser.addoption("--masterip", help="IP address of the master device to test against.")
	parser.addoption("--slaveip", help="IP address of the slave device to test against")

@pytest.fixture(scope="session")
def conn_mokus(request):
	'''
		Connects to both Mokus used throughout tests
	'''
	print "Connecting to Mokus"
	masterip = pytest.config.getoption("--masterip")
	slaveip = pytest.config.getoption("--slaveip")
	m1 = Moku(masterip)
	m2 = Moku(slaveip) #Moku(slaveip)

	print("Master IP: %s" % masterip)
	print("Slave IP: %s" % slaveip)

	request.addfinalizer(m1.close)
	request.addfinalizer(m2.close)
	return (m1, m2)

'''
@pytest.fixture(scope="function")
def base_instr(instruments):
	
		Per test setup function
	
	# Extract Mokus
	m1 = conn_mokus[0]
	m2 = conn_mokus[1]

	print "Setting defaults."
	m1.set_defaults()
	m2.set_defaults()

	return m1
'''