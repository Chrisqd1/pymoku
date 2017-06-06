from pymoku import Moku
from pymoku.instruments import *

m = Moku('192.168.69.234')#.get_by_name('Moku')

i = BodeAnalyser()
m.deploy_instrument(i)

i.set_output_amplitude(1, 1.0)
i.set_output_amplitude(2, 1.0)
i.start_sweep(sweep_points=256)
i.commit()

try:
	frame = i.get_data()
	print(len(frame.ch2.phase), len(frame.fs))
finally:
	m.close()
