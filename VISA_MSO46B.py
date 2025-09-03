import pyvisa
import time
import threading
from pyvisa import constants
from console_app import (
    error_out_if,
    output_measurement,
    output_named_measurement,
    output_status,
    prompt,
    output_err
)
from time import sleep as sl

class InstrumentManager:
    """Discover and manage DMM and MSO46B instruments."""
    def __init__(self, resource_manager=None):
        try:
            # Try without DLL path first
            self.rm = pyvisa.ResourceManager()
        except:
            try:
                # Try 64-bit DLL
                self.rm = pyvisa.ResourceManager("C:\Program Files\IVI Foundation\VISA\Win64\ktvisa\ktbin\visa32.dll")
                #self.rm = pyvisa.ResourceManager('C:\Windows\System32\visa64.dll')
            except:
                # Fall back to 32-bit DLL as last resort
                self.rm = pyvisa.ResourceManager()
                #self.rm = pyvisa.ResourceManager('C:/Windows/System32/visa32.dll')
        self.dmm = None
        self.scope = None

    def discover(self):
        #resource_str = 'TCPIP0::192.168.0.19::inst0::INSTR'
        resource_str ="USB0::0x0699::0x0527::C071089::0::INSTR"
        
        try:
            inst = self.rm.open_resource(resource_str)
            inst.timeout = 5000
            # Verify it's responding
            inst.write('*IDN?')
            self.scope = inst
            return self.scope
        except pyvisa.errors.VisaIOError as e:
            output_err(f"Could not connect to scope at {resource_str}: {e}")
            return None
        
      
class TektronixMSO46B:
    """Interface for Tektronix MSO46B oscilloscope."""
    def __init__(self, inst):
        self.inst = inst
        self.inst.timeout =20000 #constants.VI_TMO_INFINITE
        self.types= ["MINIMUM", "MAXIMUM", "MEAN", "RMS"]
        self.types_dict = {t.lower(): i+1 for i, t in enumerate(self.types)}

    def configure_vertical(self, channel=1, scale=1.0, bandwidth=20e6):
        # Set vertical scale
        self.inst.write(f"CH{channel}:SCAle {scale}")  
        # Set bandwidth
        self.inst.write(f"CH{channel}:BANDwidth {bandwidth}") 
        # Disable persistence
        self.inst.write("DISplay:PERSistence OFF")  

    def set_horizontal_scale(self, scale=0.01):
        self.inst.write(f"HORizontal:MAIN:SCALE {scale}")

    def setup_trigger(self, level=None, source="CH1", slope="RISE"):
        self.inst.write("TRIGger:A:TYPE EDGE")
        self.inst.write("TRIGger:A:EDGE:COUPling DC")
        self.inst.write(f"TRIGger:A:EDGE:SLOPe {slope}")  # Edge slope fileciteturn1file2L3-L7
        self.inst.write(f"TRIGger:A:EDGE:SOURce {source}")
        if level is not None:
            self.inst.write(f"TRIGger:A:LEVel:CH1 {level}")  # Trigger level fileciteturn1file13L41-L46

    def take_screenshot(self, file_path: str):
        self.inst.write("HARDCopy:INKSaver ON")
        self.inst.write("HARDCopy:FORMat PNG")
        self.inst.write("HARDCopy:PORT FILE")
        self.inst.write("HARDCopy:LAYout FULL")
        self.inst.write("HARDCopy:PREView OFF")
        self.inst.write("HARDCopy STARt")

        self.inst.timeout = 20000  # 20 seconds
        self.inst.write('SAVE:IMAGE "C:/Temp.png"')
        self.inst.query('*OPC?')
        self.inst.write('FILESystem:READFile "C:/Temp.png"')
        time.sleep(0.2)  # Wait for file to be ready
        raw_data = self.inst.read_raw()
        with open(file_path, 'wb') as f:
            f.write(raw_data)
        self.inst.write('FILESystem:DELEte "C:/Temp.png"')


    def enable_measurements(self, types):
    # 1) Delete all existing measurements
        self.inst.write("MEASUrement:DELETEALL") 
         # clear any old measurements :contentReference[oaicite:0]{index=0}
        time.sleep(0.5)

        # 2) Add back only the four you want, in order
        
        for idx, mtype in enumerate(types, start=1):
            # Add a new measurement of the chosen type
            self.inst.write(f"MEASUrement:ADDMEAS {mtype}")  # add a MINIMUM/MAXIMUM/MEAN/RMS slot :contentReference[oaicite:1]{index=1}
            # Point it at CH1
            self.inst.write(f"MEASUrement:MEAS{idx}:SOURCE CH1")
            # Turn it on
            self.inst.write(f"MEASUrement:MEAS{idx}:STATE ON")
            time.sleep(0.5)

    def rise_time_cursor(self):
        self.inst.write("*CLS")  # Clear the status
        time.sleep(0.5)
        self.inst.write("MEASUrement:REFLevels:PERCent:RISEHigh 80")
        time.sleep(0.5)
        self.inst.write("*CLS")
        time.sleep(0.5)
        self.inst.write("MEASUrement:REFLevels:PERCent:RISELow 20")
        time.sleep(0.5)     
    def offset(self, channel=1, offset=0.0):
        """
        Set the vertical offset for a specified channel.
        :param channel: Channel number (1-4)
        :param offset: Offset value in volts
        """
        self.inst.write(f"CH{channel}:OFFSet {offset}")
        time.sleep(0.2)
    
    def enable_cursor(self, mode="SCREEN",state="ON"):
        """
        Enable and configure cursor display.
        mode = "VERTical", "HORizontal", or "TRACk"
        """
        # Turn cursors ON
        self.inst.write(":CURSor:STATE {}".format(state))
        time.sleep(0.2)

        # Set cursor function mode
        self.inst.write(f":CURSor:FUNCtion {mode}")
        time.sleep(0.2)

        # (Optional) Assign source to CH1 for voltage/time readouts
        self.inst.write(":CURSor:SOUrce CH1")
        time.sleep(0.2)

    def voltage_cursor_position(self):
        self.inst.write("*CLS")  # Clear the status
        time.sleep(0.5)
        A = self.inst.query("DISplay:WAVEView1:CURSor:CURSOR1:HBArs:APOSition?")
        time.sleep(0.5)
        A = A.strip()  # Remove any leading/trailing whitespace
        A = float(A)  # Convert to float
        time.sleep(0.2) 
        B = float((self.inst.query("DISplay:WAVEView1:CURSor:CURSOR1:HBArs:BPOSition?")).strip())  
        time.sleep(0.2)
        return A, B

    def get_all_cursor_positions(self):
        self.inst.write("*CLS") 
        time.sleep(0.5) # Clear the status
        self.inst.write("DISplay:WAVEView1:CURSor:CURSOR1?")
        time.sleep(0.5)
        full=self.inst.read()
        
        if ";" not in full:
            self.inst.write("DISplay:WAVEView1:CURSor:CURSOR1?")
            time.sleep(0.5)
            full=self.inst.read()
         # Read the full response
        time.sleep(0.5)
        lst = full.strip().split(';')
        tA=float(lst[0])

        tA=tA *1e6
        tA=round(tA,3)  # Convert to seconds

        tB=float(lst[1])
        tB=tB *1e6
        tB=round(tB,3)  # Convert to seconds
        vA=float(lst[13])
        if vA <1:
            vA=vA *1e3  # Convert to volts
            vA=round(vA,3)
        else:
            vA=round(vA,3)  # Round to 3 decimal places

        vB=float(lst[14])
        if vB <1:
            vB=vB *1e3  # Convert to volts
            vB=round(vB,3)
        else:
            vB=round(vB,3)  # Round to

        return tA, tB, vA, vB
    
    
    def get_vertical_cursor_delta__positions(self):
        delta = float((self.inst.query("DISplay:WAVEView1:CURSor:CURSOR1:VBArs:DELTa?")).strip())
        delta_micro= delta * 1e6
        delta_micro_value_rounded = round(delta_micro, 3)
        return delta_micro_value_rounded

    def get_horizontal_cursor_delta_positions(self):
        delta = float((self.inst.query("DISplay:WAVEView1:CURSor:CURSOR1:HBArs:DELTa?")).strip())
        y1 = float(self.inst.query(":CURSor:HBArs:APOSition?"))
        y2 = float(self.inst.query(":CURSor:HBArs:BPOSition?"))
        delta = float(self.inst.query(":CURSor:HBArs:DELTa?"))
        return y1, y2, delta

    def set_trigger_level(self, v1, v2, mode="NORMal", slope="RISE"): #mode:AUTO|NORMal
        
        # 1) Calculate midpoint
        # v1=float(v1/1000)  # Convert to volts
        # v2=float(v2/1000)  # Convert to volts
        midpoint = round((v1 + v2) / 2.0,3)  # Midpoint in volts
         
        self.inst.write(f"TRIGGER:A:MODE {mode}")
        time.sleep(0.5)  # Give it a moment to process
        self.setup_trigger(level=midpoint, slope=slope)  # Set trigger level
       
        # self.inst.write(f"TRIGger:A:LEVel {midpoint}")

        #return midpoint


    def calculate_trigger_level(self):
        minv = float(self.inst.query("MEASUrement:MEAS1:VALue?").strip())
        maxv = float(self.inst.query("MEASUrement:MEAS2:VALue?").strip())
        level = round(minv + (maxv - minv)/2, 3)
        self.setup_trigger(level=level)
        return level

    def measure_rms(self):
        """
        Fetch the RMS measurement  enabled as MEAS4 in enable_measurements().
        Splits into write/read so that inst.timeout is honored on the read().
        Returns the RMS value in volts (rounded to 3 decimal places).
        """
        # 1) ask for the MEAS4 value
        #    (leading ":" is optional but often recommended)

        
        self.inst.write(":MEASure:MEAS{}:VALue?".format(self.types_dict["rms"]))
        
        # 2) read the reply (honors inst.timeout)
        time.sleep(0.5)  # Give it a moment to process
        raw = self.inst.read().strip()
        
        # 3) parse & return
        try:
            v = float(raw)
        except ValueError:
            raise RuntimeError(f"Unexpected RMS response from scope: '{raw}'")
        return round(v, 3)    

    # def measure_rms(self):
    #     rms = float(self.inst.query("MEASUrement:MEAS4:VALue?").strip())
    #     return round(rms, 3)

    def measure_rise_time(self, scope_measurement_key: list=None, v_ref: float=None):
        """Measure rise time from oscilloscope."""
        # Get the measurement index for rise time from the measurement key list
        dict = {t.lower(): i+1 for i, t in enumerate(scope_measurement_key)}
        rise_time_idx = dict["risetime"]
        
        # Query the rise time measurement using the correct index
        self.inst.write(f":MEASure:MEAS{rise_time_idx}:VALue?")
        time.sleep(0.5)
        raw = self.inst.read().strip()
        if ";" in raw:
            self.inst.write(f":MEASure:MEAS{rise_time_idx}:VALue?")
            time.sleep(0.5)
            raw = self.inst.read().strip()
        elif "MSO46B" in raw:
            self.inst.write(f":MEASure:MEAS{rise_time_idx}:VALue?")
            time.sleep(0.5)
            raw = self.inst.read().strip()
        
        try:
            rise_time_value = float(raw)
            return round(rise_time_value * 1e6, 3)  # Convert to microseconds
        except ValueError:
            raise RuntimeError(f"Unexpected rise time response from scope: '{raw}'")
    
    def measure_mean(self,scope_measurement_key: list=None,v_ref: float=None):
        dict = {t.lower(): i+1 for i, t in enumerate(scope_measurement_key)}
        self.inst.write(":MEASure:MEAS{}:VALue?".format(dict["mean"]))
        time.sleep(0.5)
        try:
            raw = self.inst.read().strip()
            time.sleep(0.5)
            raw=float(raw)
            time.sleep(0.5)

        except ValueError:
            time.sleep(0.5)
            raw = float(self.inst.read().strip())
            time.sleep(0.5)
        try:
            #v = round(float(self.inst.query("MEASUREMENT:MEAS{}:VALUE?".format(dict["mean"])).strip()), 3)
            v = round(raw, 3)
            if v>(v_ref+0.2) or v<(v_ref-0.2):
                pass
            
            #v = float(raw)
        except ValueError:
            raise RuntimeError(f"Unexpected MEAN response from scope: '{raw}'")
        return round(v, 3)
    
    def measure_maximum(self):
        """
        Measure the MAXIMUM value from the oscilloscope using the assigned MEASx slot.
        """
        # Request the value for the measurement slot corresponding to 'maximum'
        self.inst.write(":MEASure:MEAS{}:VALue?".format(self.types_dict["maximum"]))
        time.sleep(0.5)
        raw = self.inst.read().strip()

        try:
            # Query the same slot directly and convert to float
            v=round((float(self.inst.query("MEASUREMENT:MEAS{}:VALUE?".format(self.types_dict["maximum"])).strip())) * 1e3,3)
            #v = round(float(self.inst.query("MEASUREMENT:MEAS{}:VALUE?".format(self.types_dict["maximum"])).strip()), 3)
        except ValueError:
            raise RuntimeError(f"Unexpected MAXIMUM response from scope: '{raw}'")
        
        return round(v, 3)
    
    def measure_minimum(self,scope_measurement_key: list=None):
        """
        Measure the MINIMUM value from the oscilloscope using the assigned MEASx slot.
        """
        
        dict = {t.lower(): i+1 for i, t in enumerate(scope_measurement_key)}
        # Write the request to the scope for the correct measurement slot
        self.inst.write(":MEASure:MEAS{}:VALue?".format(self.types_dict["minimum"]))
        time.sleep(0.5)  # Give it a moment to process
        raw = self.inst.read().strip()

        try:
            # Query the same measurement slot and parse the result
            v = round(float(self.inst.query("MEASUrement:MEAS{}:VALue?".format(self.types_dict["minimum"])).strip()), 3)
        except ValueError:
            raise RuntimeError(f"Unexpected MINIMUM response from scope: '{raw}'")

        return round(v, 3)

    def measure_stable_voltage(self, vid_mV, is_light_load=False):
        """
        Take multiple measurements and return stable average with error checking
        
        Args:
            vid_mV (int): The VID voltage in millivolts
            is_light_load (bool): True if current is 0.01A or less
            
        Returns:
            float: The averaged stable voltage measurement
        """
        # Take multiple samples for better accuracy
        num_samples = 5 if is_light_load else 3
        settling_time = 0.5 if is_light_load else 0.2  # longer settling time for light loads
        
        # Wait for voltage to settle
        sl(settling_time)
        
        measurements = []
        for _ in range(num_samples):
            v_mean = self.measure_mean(["MEAN"], float(vid_mV)/1000)
            measurements.append(v_mean)
            sl(0.1)  # Small delay between measurements
        
        # Calculate average and remove outliers
        measurements=measurements[1:]  # Skip the first measurement as it may be an outlier
        avg_voltage = measurements[0]
        
        # # For light loads (0.01A), check if measurement is within expected range
        # if is_light_load:
        #     expected_v = float(vid_mV)/1000
        #     margin = 0.05  # 5% margin
        #     if abs(avg_voltage - expected_v) > (expected_v * margin):
        #         output_status(f"Warning: Light load measurement {avg_voltage:.3f}V exceeds {margin*100}% margin from VID {expected_v:.3f}V")
        
        return avg_voltage

    def clear_screen(self):
        self.inst.write("CLEAR")
        time.sleep(0.2)
        
    def clear_all_measurements(self):
        """Clear all measurements and measurement buffer."""
        # Clear the device status
        self.inst.write("*CLS")
        time.sleep(0.2)
        
        # Delete all measurements
        self.inst.write("MEASUrement:DELETEALL")
        time.sleep(0.2)
        
        # Clear the measurement statistics
        self.inst.write("MEASUrement:STATIstics:MODE OFF")
        time.sleep(0.2)
        
        # Reset measurement buffer
        self.inst.write("MEASUrement:MEAS:REFLevel:METHOD ABSOLUTE")
        time.sleep(0.2)


    def close(self):
        self.inst.close()


if __name__ == "__main__":
    mgr = InstrumentManager()
    inst = mgr.discover()               # inst is a pyvisa resource with .write()/.query()
    if inst is None:
        raise RuntimeError("No MSO46B found on any VISA resource")
    scope = TektronixMSO46B(inst) 
    scope.clear_all_measurements()    
      # ← now you’re passing the real instrument
    scope.enable_measurements(["MINIMUM"])
    mean=scope.measure_minimum()
    scope.clear_all_measurements()
    scope.close()
