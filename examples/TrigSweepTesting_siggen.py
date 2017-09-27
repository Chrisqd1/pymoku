from pymoku import Moku, ValueOutOfRangeException
from pymoku.instruments import *
import time, logging

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s::%(message)s')
logging.getLogger('pymoku').setLevel(logging.DEBUG)


# Use Moku.get_by_serial() or get_by_name() if you don't know the IP
#m = Moku.get_by_name("Oil Rigs")
m = Moku('192.168.69.56')
i = WaveformGenerator()
m.deploy_instrument(i)

#Initialize waveform generator:
i.gen_sinewave(1, 1.0, 5)
i.gen_sinewave(2, 1.0, 5)

# i.set_frontend(channel = 1, fiftyr=False, atten=False, ac=False)
# i.set_frontend(channel = 2, fiftyr=True, atten=False, ac=False)

"""
#### TEST MAIN TRIGGER MODES:
"""

### Test trigger sources for each trigger mode:

## GATED MODE: ##
print("\n\n *** TESTING TRIGGER MODES *** ")
print("\nTesting trigger sources for gated mode. Connect DAC 1/2 to an oscolliscope and configure a 2 Vpp trigger with a one second period and 40percent duty cycle.\n")
# Test Ext Trig IN
i.set_trigger_mode(ch = 1, mode = 'gateway')
i.set_trigger_mode(ch = 2, mode = 'gateway')
i.set_trigger_source(ch = 1, trigger_source = 'external')
i.set_trigger_source(ch = 2, trigger_source = 'external')
input("\n Connect trigger to the Moku trigger in. Two 5 Hz cycles seen on channel 1/2 when triggered? Press enter to continue...")

# Test ADC trigger in
i.set_trigger_threshold(ch = 1)
i.set_trigger_threshold(ch = 2)
i.set_trigger_source(ch = 1, trigger_source = 'adc')
i.set_trigger_source(ch = 2, trigger_source = 'adc')
input("\n Connect trigger to Moku ADC 1/2. Two 5 Hz cycles seen on channel 1/2 when triggered? Press enter to continue...")

# Test DAC trigger
i.set_trigger_source(ch = 1, trigger_source = 'dac')
i.set_trigger_source(ch = 2, trigger_source = 'dac')
i.set_trigger_mode(ch = 1, mode = 'off')
i.gen_squarewave(2, 1.0, 1, risetime = 0.0001, falltime = 0.0001, duty = 0.4, offset = 0)
input("\n Testing trigger source from DAC 2. Two 5 Hz cycles seen on channel 1 every second? Press enter to continue ... ")

i.gen_squarewave(1, 1.0, 1, risetime = 0.0001, falltime = 0.0001, duty = 0.4, offset = 0)
i.set_trigger_mode(ch = 1, mode = 'off')
i.set_trigger_mode(ch = 2, mode = 'gateway')
i.gen_sinewave(2, 1.0, 5)
input("\n Testing trigger source from DAC 1. Two 5 Hz cycles seen on channel 2 every second? Press enter to continue ... ")

# Test internal trigger
i.set_trigger_source(ch = 1, trigger_source = 'internal')
i.set_trigger_source(ch = 2, trigger_source = 'internal')
i.set_trigger_mode(ch = 1, mode = 'gateway')
i.set_trigger_mode(ch = 2, mode = 'gateway')
i.gen_sinewave(1, 1.0, 5)
i.gen_sinewave(2, 1.0, 5)
input("\n Testing internal trigger, configured with a one second period and 40 percent duty cycle. Two 5 Hz cycles seen on channels 1/2 every second? Press enter to continue ... ")

## START MODE: ##
print("\nTesting trigger sources for start mode. Connect DAC 1/2 to an oscolliscope and configure a 2 Vpp trigger with any period/duty cycle.\n")
# Test Ext Trig IN
i.set_trigger_mode(ch = 1, mode = 'startmode')
i.set_trigger_mode(ch = 2, mode = 'startmode')
i.set_trigger_source(ch = 1, trigger_source = 'external')
i.set_trigger_source(ch = 2, trigger_source = 'external')
input("\n Connect trigger to the Moku trigger in. 5 Hz sinewave seen on channels 1/2 when triggered? Press enter to continue...")

# Test ADC trigger in
i.set_trigger_threshold(ch = 1)
i.set_trigger_threshold(ch = 2)
i.set_trigger_source(ch = 1, trigger_source = 'adc')
i.set_trigger_source(ch = 2, trigger_source = 'adc')
input("\n Connect trigger to Moku ADC 1/2. 5 Hz sinewave seen on channels 1/2 when triggered? Press enter to continue...")

# Test DAC trigger
i.set_trigger_source(ch = 1, trigger_source = 'dac')
i.set_trigger_source(ch = 2, trigger_source = 'dac')
i.set_trigger_mode(ch = 1, mode = 'off')
i.gen_squarewave(2, 1.0, 1, risetime = 0.0001, falltime = 0.0001, duty = 0.4, offset = 0)
input("\n Testing trigger source from DAC 2. 5 Hz sinewave seen on channel 1 coinciding with the first positive edge on channel 2? Press enter to continue ... ")

i.gen_squarewave(1, 1.0, 1, risetime = 0.0001, falltime = 0.0001, duty = 0.4, offset = 0)
i.set_trigger_mode(ch = 1, mode = 'off')
i.set_trigger_mode(ch = 2, mode = 'startmode')
i.gen_sinewave(2, 1.0, 5)
input("\n Testing trigger source from DAC 1. 5 Hz sinewave seen on channel 2 coinciding with the first positive edge on channel 1? Press enter to continue ... ")

i.gen_sinewave(1, 1.0, 5)
i.gen_sinewave(2, 1.0, 5)

## NCYCLE MODE: ##
print("\nTesting trigger sources for N cycle mode. Connect DAC 1/2 to an oscolliscope and configure a 2 Vpp trigger with any period/duty cycle.\n")
# Test Ext Trig IN
i.set_trigger_mode(ch = 1, mode = 'ncycle', ncycles = 1)
i.set_trigger_mode(ch = 2, mode = 'ncycle', ncycles = 1)
i.set_trigger_source(ch = 1, trigger_source = 'external')
i.set_trigger_source(ch = 2, trigger_source = 'external')
input("\n Connect trigger to the Moku trigger in. One 5 Hz cycle seen on channels 1/2 when triggered? Press enter to continue...")

# Test ADC trigger in
i.set_trigger_threshold(ch = 1)
i.set_trigger_threshold(ch = 2)
i.set_trigger_source(ch = 1, trigger_source = 'adc')
i.set_trigger_source(ch = 2, trigger_source = 'adc')
input("\n Connect trigger to Moku ADC 1/2. One 5 Hz cycle seen on channels 1/2 when triggered? Press enter to continue...")

# Test DAC trigger
i.set_trigger_source(ch = 1, trigger_source = 'dac')
i.set_trigger_source(ch = 2, trigger_source = 'dac')
i.set_trigger_mode(ch = 2, mode = 'off')
i.gen_squarewave(2, 1.0, 1, risetime = 0.0001, falltime = 0.0001, duty = 0.4, offset = 0)
input("\n Testing trigger source from DAC 2. One 5 Hz cycle seen on channel 1 coinciding with each positive edge on channel 2? Press enter to continue ... ")

i.gen_squarewave(1, 1.0, 1, risetime = 0.0001, falltime = 0.0001, duty = 0.4, offset = 0)
i.set_trigger_mode(ch = 1, mode = 'off')
i.set_trigger_mode(ch = 2, mode = 'ncycle', ncycles = 1)
i.gen_sinewave(2, 1.0, 5)
input("\n Testing trigger source from DAC 1. One 5 Hz cycle seen on channel 2 coinciding with each positive edge on channel 1? Press enter to continue ... ")

# Test internal trigger
i.set_trigger_source(ch = 1, trigger_source = 'internal')
i.set_trigger_source(ch = 2, trigger_source = 'internal')
i.set_trigger_mode(ch = 1, mode = 'ncycle', ncycles = 1)
i.set_trigger_mode(ch = 2, mode = 'ncycle', ncycles = 1)
i.gen_sinewave(1, 1.0, 5)
i.gen_sinewave(2, 1.0, 5)
input("\n Testing internal trigger. One 5 Hz cycle seen on channels 1/2 every second? Press enter to continue ... ")

"""
### FURTHER TRIGGER MODE TESTING ###
"""

## Test gate/start/ncycle trigger modes for sinewave frequencies 200 Hz, 2 KHz and 2 MHz.
print("\n\n Testing trigger modes for sinewave frequencies 20 Hz, 200 Hz, 2 KHz, 2 MHz. Connect 2 Vpp trigger of appropriate period/duty cycle to Ext Trig In")
print("\n\n Testing gate, start and Ncycle trigger modes for a 200 Hz sinewave: \n")

# Gatemode, 200 Hz:
i.gen_sinewave(1, 1.0, 200)
i.gen_sinewave(2, 1.0, 200)
i.set_trigger_mode(ch = 1, mode = 'gateway')
i.set_trigger_mode(ch = 2, mode = 'gateway')
i.set_trigger_source(ch = 1, trigger_source = 'external')
i.set_trigger_source(ch = 2, trigger_source = 'external')
input("\n 200 Hz sinewaves, gated corresponding to the trigger period/duty cycle combination, seen on channels 1/2? Press enter to continue ... ")

# Startmode, 200 Hz:
i.set_trigger_mode(ch = 1, mode = 'startmode')
i.set_trigger_mode(ch = 2, mode = 'startmode')
input("\n 200 Hz sinewaves seen on channels 1/2 when triggered? Press enter to continue ... ")

# NCycle mode, 200 Hz:
i.set_trigger_mode(ch = 1, mode = 'ncycle', ncycles = 1)
i.set_trigger_mode(ch = 2, mode = 'ncycle', ncycles = 1)
input("\n One 200 Hz sinewave cycle seen on channels 1/2 when triggered? Press enter to continue ... ")

print("\n\n Testing gate, start and Ncycle trigger modes for a 2 KHz sinewave: \n")

# Gatemode, 2 KHz:
i.gen_sinewave(1, 1.0, 2000)
i.gen_sinewave(2, 1.0, 2000)
i.set_trigger_mode(ch = 1, mode = 'gateway')
i.set_trigger_mode(ch = 2, mode = 'gateway')
i.set_trigger_source(ch = 1, trigger_source = 'external')
i.set_trigger_source(ch = 2, trigger_source = 'external')
input("\n 2 KHz sinewaves, gated corresponding to the trigger period/duty cycle combination, seen on channels 1/2? Press enter to continue ... ")

# Startmode, 2 KHz:
i.set_trigger_mode(ch = 1, mode = 'startmode')
i.set_trigger_mode(ch = 2, mode = 'startmode')
input("\n 2 KHz sinewaves seen on channels 1/2 when triggered? Press enter to continue ... ")

# NCycle mode, 2 KHz:
i.set_trigger_mode(ch = 1, mode = 'ncycle', ncycles = 1)
i.set_trigger_mode(ch = 2, mode = 'ncycle', ncycles = 1)
input("\n One 2 KHz sinewave cycle seen on channels 1/2 when triggered? Press enter to continue ... ")


print("\n\n Testing gate, start and Ncycle trigger modes for a 2 MHz sinewave: \n")

# Gatemode, 2 MHz:
i.gen_sinewave(1, 1.0, 2e6)
i.gen_sinewave(2, 1.0, 2e6)
i.set_trigger_mode(ch = 1, mode = 'gateway')
i.set_trigger_mode(ch = 2, mode = 'gateway')
i.set_trigger_source(ch = 1, trigger_source = 'external')
i.set_trigger_source(ch = 2, trigger_source = 'external')
input("\n 2 MHz sinewaves, gated corresponding to the trigger period/duty cycle combination, seen on channels 1/2? Press enter to continue ... ")

# Startmode, 2 MHz:
i.set_trigger_mode(ch = 1, mode = 'startmode')
i.set_trigger_mode(ch = 2, mode = 'startmode')
input("\n 2 MHz sinewaves seen on channels 1/2 when triggered? Press enter to continue ... ")

# NCycle mode, 2 MHz:
i.set_trigger_mode(ch = 1, mode = 'ncycle', ncycles = 1)
i.set_trigger_mode(ch = 2, mode = 'ncycle', ncycles = 1)
input("\n One 2 MHz sinewave cycle seen on channels 1/2 when triggered? Press enter to continue ... ")


"""
#### SWEEP MODE TESTING:
"""

print("\n\n SWEEP MODE TESTING: \n")
print("\n Test trigger sources: \n")

### Test different trigger sources:

i.set_trigger_source(ch = 1, trigger_source = 'external')
i.set_trigger_source(ch = 2, trigger_source = 'external')
i.set_trigger_mode(ch = 1, mode = 'sweep', sweep_final_freq = 5.0, sweep_duration = 10.0)
i.set_trigger_mode(ch = 2, mode = 'sweep', sweep_final_freq = 5.0, sweep_duration = 10.0)
input("\nTesting Ext trigger source. A 10 second sweep from 1 Hz to 5 Hz is seen on channel 1/2 when triggered externally? Press enter to continue ... ")

i.set_trigger_threshold(ch = 1)
i.set_trigger_threshold(ch = 2)
i.set_trigger_source(ch = 1, trigger_source = 'adc')
i.set_trigger_source(ch = 2, trigger_source = 'adc')
i.set_trigger_mode(ch = 1, mode = 'sweep', sweep_final_freq = 5.0, sweep_duration = 10.0)
i.set_trigger_mode(ch = 2, mode = 'sweep', sweep_final_freq = 5.0, sweep_duration = 10.0)
input("\nTesting ADC trigger source. A 10 second sweep from 1 Hz to 5 Hz is seen on channel 1/2 when triggered? Press enter to continue ... ")

i.set_trigger_source(ch = 1, trigger_source = 'dac')
i.set_trigger_source(ch = 2, trigger_source = 'dac')
i.set_trigger_mode(ch = 2, mode = 'off')
i.gen_squarewave(2, 1.0, 1, risetime = 0.0001, falltime = 0.0001, duty = 0.5, offset = 0)
input("\nTesting DAC trigger source. A 10 second sweep from 1 Hz to 5 Hz is seen on channel 1 corresponding to the rising edge of channel 2? Press enter to continue ... ")

i.gen_squarewave(1, 1.0, 1, risetime = 0.0001, falltime = 0.0001, duty = 0.5, offset = 0)
i.set_trigger_mode(ch = 1, mode = 'off')
i.set_trigger_mode(ch = 2, mode = 'sweep', sweep_final_freq = 5.0, sweep_duration = 10.0)
i.set_trigger_source(ch = 2, trigger_source = 'dac')
i.gen_sinewave(2, 1.0, 10)
input("\nTesting DAC trigger source. A 10 second sweep from 1 Hz to 5 Hz is seen on channel 2 corresponding to the rising edge of channel 1? Press enter to continue ... ")


### Test different sweep lengths, init frequencies and final frequencies:
print("\n Testing varying sweep lengths, init frequencies and final frequencies. Connect trigger to external trigger in: \n")

i.set_trigger_source(ch = 1, trigger_source = 'external')
i.gen_sinewave(1, 1.0, 10)
i.set_trigger_mode(ch = 1, mode = 'sweep', sweep_final_freq = 1000.0, sweep_duration = 10.0)
input("\n Sweep from 50 Hz to 1 KHz over 10 seconds seen on channel 1? Press enter to continue ... ")

i.set_trigger_source(ch = 1, trigger_source = 'external')
i.gen_sinewave(1, 1.0, 10)
i.set_trigger_mode(ch = 1, mode = 'sweep', sweep_final_freq = 1.0e6, sweep_duration = 10.0)
input("\n Sweep from 100 KHz to 1 MHz over 10 seconds seen on channel 1? Press enter to continue ... ")

i.set_trigger_source(ch = 1, trigger_source = 'external')
i.gen_sinewave(1, 1.0, 10)
i.set_trigger_mode(ch = 1, mode = 'sweep', sweep_final_freq = 50.0e6, sweep_duration = 10.0)
input("\n Sweep from 1 MHz to 50 MHz over 10 seconds seen on channel 1? Press enter to continue ... ")

### Test square/pulse wave sweeps:
print("\n Testing square/pulse wave sweeps: \n")
i.set_trigger_source(ch = 1, trigger_source = 'external')
i.gen_squarewave(1, 1.0, 1, risetime = 0.0001, falltime = 0.0001, duty = 0.5, offset = 0)
i.set_trigger_mode(ch = 1, mode = 'sweep', sweep_final_freq = 1.0e6, sweep_duration = 10.0)
input("\n Square wave sweep from 100 KHz to 1 KHz over 10 seconds seen on channel 1? Press enter to continue ... ")

i.set_trigger_source(ch = 1, trigger_source = 'external')
i.gen_squarewave(1, 1.0, 1, risetime = 0.0001, falltime = 0.0001, duty = 0.1, offset = 0)
i.set_trigger_mode(ch = 1, mode = 'sweep', sweep_final_freq = 1.0e6, sweep_duration = 10.0)
input("\n Pulse wave (10percent duty cycle) sweep from 100 KHz to 1 KHz over 10 seconds seen on channel 1? Press enter to continue ... ")

i.gen_sinewave(1, 1.0, 10e6)
#i.synth_modulate(1, SG_MOD_FREQ, SG_MODSOURCE_INT, 1, 10)
i.set_trigger_source(ch=1, trigger_source = 'external')
i.set_trigger_mode(ch = 1, mode = 'ncycle', ncycles = 1)
#i.set_mode(ch = 1, mode = 'sweep', sweep_init_freq = 1.0, sweep_final_freq = 5.0, sweep_duration = 10.0)
