import pyvisa

dll_path = r"C:\Program Files\IVI Foundation\VISA\Win64\ktvisa\ktbin\visa32.dll"
rm = pyvisa.ResourceManager()

print("Loaded:", rm.visalib.library_path)
print("Resources:", rm.list_resources())

inst = rm.open_resource('TCPIP0::10.0.140.140::inst0::INSTR')
print(inst.query("*IDN?"))



# def measurement_enable(scope):
#     scope.write("MEASUREMENT:MEAS1:SOURCE CH1")
#     scope.write("MEASUREMENT:MEAS1:TYPE MIN")
#     scope.write("MEASUREMENT:MEAS1:STATE ON")
#     time.sleep(0.5)
#     scope.write("MEASUREMENT:MEAS2:SOURCE CH1")
#     scope.write("MEASUREMENT:MEAS2:TYPE MAX")
#     scope.write("MEASUREMENT:MEAS2:STATE ON")
#     time.sleep(0.5)
#     scope.write("MEASUREMENT:MEAS3:SOURCE CH1")
#     scope.write("MEASUREMENT:MEAS3:TYPE MEAN")
#     scope.write("MEASUREMENT:MEAS3:STATE ON")
#     time.sleep(0.5)
#     scope.write("MEASUREMENT:MEAS4:SOURCE CH1")
#     scope.write("MEASUREMENT:MEAS4:TYPE RMS")
#     scope.write("MEASUREMENT:MEAS4:STATE ON")
#     time.sleep(0.5)

# def trigger_level(scope):

#     min = round(float(scope.query("MEASUREMENT:MEAS1:VALUE?").strip()), 3)
#     time.sleep(1)
#     max = round(float(scope.query("MEASUREMENT:MEAS2:VALUE?").strip()), 3)
#     time.sleep(1)

#     # Calculate the trigger level as min_value + 10%
#     trigger_level = round(min + (max-min)/2,3)

#     scope.write("TRIGger:A:LEVel:CH1 {}".format(trigger_level)) #hashtag#set the trigger level
#     time.sleep(1)

# def RMS_current_value(scope):
#     rms = round(float(scope.query("MEASUREMENT:MEAS4:VALUE?").strip()), 3)
#     time.sleep(0.5)

#     return rms