import pyvisa
import time
import threading
from pyvisa import constants


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
            print(f"Could not connect to scope at {resource_str}: {e}")
            return None
        
      
class TektronixMSO46B:
    """Interface for Tektronix MSO46B oscilloscope."""
    def __init__(self, inst):
        self.inst = inst
        self.inst.timeout =20000 #constants.VI_TMO_INFINITE

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

    def enable_measurements(self):
    # 1) Delete all existing measurements
        self.inst.write("MEASUrement:DELETEALL")  # clear any old measurements :contentReference[oaicite:0]{index=0}
        time.sleep(0.1)

        # 2) Add back only the four you want, in order
        types = ["MINIMUM", "MAXIMUM", "MEAN", "RMS"]
        for idx, mtype in enumerate(types, start=1):
            # Add a new measurement of the chosen type
            self.inst.write(f"MEASUrement:ADDMEAS {mtype}")  # add a MINIMUM/MAXIMUM/MEAN/RMS slot :contentReference[oaicite:1]{index=1}
            # Point it at CH1
            self.inst.write(f"MEASUrement:MEAS{idx}:SOURCE CH1")
            # Turn it on
            self.inst.write(f"MEASUrement:MEAS{idx}:STATE ON")
            time.sleep(0.1)

   

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
        self.inst.write(":MEASure:MEAS4:VALue?")
        
        # 2) read the reply (honors inst.timeout)
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

    def measure_mean(self):
    
        self.inst.write(":MEASure:MEAS3:VALue?")
        raw = self.inst.read().strip()
        try:
            v = round(float(self.inst.query("MEASUREMENT:MEAS3:VALUE?").strip()), 3)
            #v = float(raw)
        except ValueError:
            raise RuntimeError(f"Unexpected MEAN response from scope: '{raw}'")
        return round(v, 3)

    def close(self):
        self.inst.close()


if __name__ == "__main__":
    mgr = InstrumentManager()
    inst = mgr.discover()               # inst is a pyvisa resource with .write()/.query()
    if inst is None:
        raise RuntimeError("No MSO46B found on any VISA resource")
    scope = TektronixMSO46B(inst)       # ← now you’re passing the real instrument
    scope.enable_measurements()
    #scope.close()
