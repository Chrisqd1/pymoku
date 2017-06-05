from pymoku import Moku
from pymoku.instruments import *

m = Moku.get_by_name('Moku')

i = NetAn()
m.attach_instrument(i)

i.set_output_amplitude(1, 1.0)
i.set_output_amplitude(2, 1.0)
i.start_sweep()
i.commit()

try:
	frame = i.get_frame()
	print(frame.ch1.magnitude)
finally:
	m.close()
