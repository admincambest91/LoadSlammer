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
    """Discover and manage DMM and MDO34 instruments."""
    def __init__(self, resource_manager=None):
        try:
            self.rm = pyvisa.ResourceManager()
        except:
            try:
                self.rm = pyvisa.ResourceManager("C:\Program Files\IVI Foundation\VISA\Win64\ktvisa\ktbin\visa32.dll")
            except:
                self.rm = pyvisa.ResourceManager()
        self.dmm = None
        self.scope = None

    def discover(self):
        resource_str = "USB0::0x0699::0x0527::C071089::0::INSTR"  # Update as needed for MDO34
        try:
            inst = self.rm.open_resource(resource_str)
            inst.timeout = 5000
            inst.write('*IDN?')
            self.scope = inst
            return self.scope
        except pyvisa.errors.VisaIOError as e:
            output_err(f"Could not connect to scope at {resource_str}: {e}")
            return None

class TektronixMDO34:
    """Interface for Tektronix MDO34 oscilloscope."""
    def __init__(self, inst):
        self.inst = inst
        self.inst.timeout = 20000
        self.types = ["MINIMUM", "MAXIMUM", "MEAN", "RMS"]
        self.types_dict = {t.lower(): i+1 for i, t in enumerate(self.types)}

    def configure_vertical(self, channel=1, scale=1.0, bandwidth=20e6):
        # Set vertical scale
        self.inst.write(f"CH{channel}:SCALE {scale}")
        # Set bandwidth limit (MDO34 uses BANDWIDTH)
        self.inst.write(f"CH{channel}:BANDWIDTH {bandwidth}")
        # Disable persistence
        self.inst.write("DISP:PERS OFF")

    def set_horizontal_scale(self, scale=0.01):
        self.inst.write(f"HOR:SCALE {scale}")

    def setup_trigger(self, level=None, source="CH1", slope="RISE"):
        self.inst.write("TRIG:A:TYPE EDGE")
        self.inst.write("TRIG:A:EDGE:COUP DC")
        self.inst.write(f"TRIG:A:EDGE:SLOPE {slope}")
        self.inst.write(f"TRIG:A:EDGE:SOURCE {source}")
        if level is not None:
            self.inst.write(f"TRIG:A:LEVEL {level}")

    def take_screenshot(self, file_path: str):
        self.inst.write('*OPC?')
        self.inst.write("HARDCOPY:INKSAVER ON")
        self.inst.write("HARDCOPY:FORMAT PNG")
        self.inst.write("HARDCOPY:PORT FILE")
        self.inst.write("HARDCOPY:LAYOUT FULL")
        self.inst.write("HARDCOPY:PREVIEW OFF")
        self.inst.write("HARDCOPY START")
        self.inst.timeout = 20000
        self.inst.write('SAVE:IMAGE "C:/Temp.png"')
        self.inst.query('*OPC?')
        self.inst.write('FILESYSTEM:READFILE "C:/Temp.png"')
        time.sleep(1)
        raw_data = self.inst.read_raw()
        with open(file_path, 'wb') as f:
            f.write(raw_data)
        self.inst.write('FILESYSTEM:DELETE "C:/Temp.png"')

    def enable_measurements(self, types):
        self.inst.write("MEAS:DEL ALL")
        time.sleep(0.5)
        for idx, mtype in enumerate(types, start=1):
            self.inst.write(f"MEAS:ADD {mtype}")
            self.inst.write(f"MEAS:MEAS{idx}:SOURCE CH1")
            self.inst.write(f"MEAS:MEAS{idx}:STATE ON")
            time.sleep(0.5)

    def rise_time_cursor(self):
        self.inst.write("*CLS")
        time.sleep(0.5)
        self.inst.write("MEAS:REFLEVELS:PERCENT:RISEHIGH 80")
        time.sleep(0.5)
        self.inst.write("*CLS")
        time.sleep(0.5)
        self.inst.write("MEAS:REFLEVELS:PERCENT:RISELOW 20")
        time.sleep(0.5)

    def offset(self, channel=1, offset=0.0):
        self.inst.write(f"CH{channel}:OFFSET {offset}")
        time.sleep(0.2)

    def enable_cursor(self, mode="SCREEN", state="ON"):
        self.inst.write(f"CURSOR:STATE {state}")
        time.sleep(0.2)
        self.inst.write(f"CURSOR:FUNCTION {mode}")
        time.sleep(0.2)
        self.inst.write(f"CURSOR:SOURCE CH1")
        time.sleep(0.2)

    def voltage_cursor_position(self):
        self.inst.write("*CLS")
        time.sleep(0.5)
        A = self.inst.query("DISPLAY:WAVEVIEW1:CURSOR:CURSOR1:HBARS:APOS?")
        time.sleep(0.5)
        A = float(A.strip())
        time.sleep(0.2)
        B = float(self.inst.query("DISPLAY:WAVEVIEW1:CURSOR:CURSOR1:HBARS:BPOS?").strip())
        time.sleep(0.2)
        return A, B

    def get_all_cursor_positions(self):
        self.inst.write("*CLS")
        time.sleep(0.5)
        self.inst.write("DISPLAY:WAVEVIEW1:CURSOR:CURSOR1?")
        time.sleep(0.5)
        full = self.inst.read()
        if ";" not in full:
            self.inst.write("DISPLAY:WAVEVIEW1:CURSOR:CURSOR1?")
            time.sleep(0.5)
            full = self.inst.read()
        time.sleep(0.5)
        lst = full.strip().split(';')
        tA = float(lst[0]) * 1e6
        tA = round(tA, 3)
        tB = float(lst[1]) * 1e6
        tB = round(tB, 3)
        vA = float(lst[13])
        vA = round(vA * 1e3 if vA < 1 else vA, 3)
        vB = float(lst[14])
        vB = round(vB * 1e3 if vB < 1 else vB, 3)
        return tA, tB, vA, vB

    def get_vertical_cursor_delta_positions(self):
        delta = float(self.inst.query("DISPLAY:WAVEVIEW1:CURSOR:CURSOR1:VBARS:DELTA?").strip())
        delta_micro = delta * 1e6
        return round(delta_micro, 3)

    def get_horizontal_cursor_delta_positions(self):
        delta = float(self.inst.query("DISPLAY:WAVEVIEW1:CURSOR:CURSOR1:HBARS:DELTA?").strip())
        y1 = float(self.inst.query("CURSOR:HBARS:APOS?").strip())
        y2 = float(self.inst.query("CURSOR:HBARS:BPOS?").strip())
        delta = float(self.inst.query("CURSOR:HBARS:DELTA?").strip())
        return y1, y2, delta

    def set_trigger_level(self, v1, v2, mode="NORM", slope="RISE"):
        midpoint = round((v1 + v2) / 2.0, 3)
        self.inst.write(f"TRIG:A:MODE {mode}")
        time.sleep(0.5)
        self.setup_trigger(level=midpoint, slope=slope)

    def calculate_trigger_level(self):
        minv = float(self.inst.query("MEAS:MEAS1:VALUE?").strip())
        maxv = float(self.inst.query("MEAS:MEAS2:VALUE?").strip())
        level = round(minv + (maxv - minv) / 2, 3)
        self.setup_trigger(level=level)
        return level

    def measure_rms(self):
        self.inst.write(f":MEAS:MEAS{self.types_dict['rms']}:VALUE?")
        time.sleep(0.5)
        raw = self.inst.read().strip()
        try:
            v = float(raw)
        except ValueError:
            raise RuntimeError(f"Unexpected RMS response from scope: '{raw}'")
        return round(v, 3)

    def measure_rise_time(self, scope_measurement_key: list = None, v_ref: float = None):
        dict = {t.lower(): i+1 for i, t in enumerate(scope_measurement_key)}
        rise_time_idx = dict["risetime"]
        self.inst.write(f":MEAS:MEAS{rise_time_idx}:VALUE?")
        time.sleep(0.5)
        raw = self.inst.read().strip()
        if ";" in raw or "MDO34" in raw:
            self.inst.write(f":MEAS:MEAS{rise_time_idx}:VALUE?")
            time.sleep(0.5)
            raw = self.inst.read().strip()
        try:
            rise_time_value = float(raw)
            return round(rise_time_value * 1e6, 3)
        except ValueError:
            raise RuntimeError(f"Unexpected rise time response from scope: '{raw}'")

    def measure_mean(self, scope_measurement_key: list = None, v_ref: float = None):
        dict = {t.lower(): i+1 for i, t in enumerate(scope_measurement_key)}
        self.inst.write(f":MEAS:MEAS{dict['mean']}:VALUE?")
        time.sleep(0.5)
        try:
            raw = self.inst.read().strip()
            time.sleep(0.5)
            raw = float(raw)
            time.sleep(0.5)
        except ValueError:
            time.sleep(0.5)
            raw = float(self.inst.read().strip())
            time.sleep(0.5)
        try:
            v = round(raw, 3)
            if v > (v_ref + 0.2) or v < (v_ref - 0.2):
                pass
        except ValueError:
            raise RuntimeError(f"Unexpected MEAN response from scope: '{raw}'")
        return round(v, 3)

    def measure_maximum(self):
        self.inst.write(f":MEAS:MEAS{self.types_dict['maximum']}:VALUE?")
        time.sleep(0.5)
        raw = self.inst.read().strip()
        try:
            v = round(float(self.inst.query(f"MEAS:MEAS{self.types_dict['maximum']}:VALUE?").strip()) * 1e3, 3)
        except ValueError:
            raise RuntimeError(f"Unexpected MAXIMUM response from scope: '{raw}'")
        return round(v, 3)

    def measure_minimum(self, scope_measurement_key: list = None):
        dict = {t.lower(): i+1 for i, t in enumerate(scope_measurement_key)}
        self.inst.write(f":MEAS:MEAS{self.types_dict['minimum']}:VALUE?")
        time.sleep(0.5)
        raw = self.inst.read().strip()
        try:
            v = round(float(self.inst.query(f"MEAS:MEAS{self.types_dict['minimum']}:VALUE?").strip()), 3)
        except ValueError:
            raise RuntimeError(f"Unexpected MINIMUM response from scope: '{raw}'")
        return round(v, 3)

    def operation_complete(self):
        state = self.inst.query("*OPC?")
        time.sleep(0.5)
        return state.strip()

    def measure_stable_voltage(self, vid_mV, is_light_load=False):
        num_samples = 5 if is_light_load else 3
        settling_time = 0.5 if is_light_load else 0.2
        sl(settling_time)
        measurements = []
        for _ in range(num_samples):
            v_mean = self.measure_mean(["MEAN"], float(vid_mV)/1000)
            measurements.append(v_mean)
            sl(0.1)
        measurements = measurements[1:]
        avg_voltage = measurements[0]
        return avg_voltage

    def clear_screen(self):
        self.inst.write("CLEAR")
        time.sleep(0.2)

    def clear_all_measurements(self):
        self.inst.write("*CLS")
        time.sleep(0.2)
        self.inst.write("MEAS:DEL ALL")
        time.sleep(0.2)
        self.inst.write("MEAS:STAT:MODE OFF")
        time.sleep(0.2)
        self.inst.write("MEAS:REFLEVEL:METHOD ABS")
        time.sleep(0.2)

    def close(self):
        self.inst.close()

if __name__ == "__main__":
    mgr = InstrumentManager()
    inst = mgr.discover()
    if inst is None:
        raise RuntimeError("No MDO34 found on any VISA resource")
    scope = TektronixMDO34(inst)
    scope.clear_all_measurements()
    scope.enable_measurements(["MINIMUM"])
    mean = scope.measure_minimum(["MINIMUM"])
    scope.clear_all_measurements()
    scope.close()
