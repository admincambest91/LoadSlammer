import os
import tkinter as tk
from tkinter import ttk
import time
from console_app import (
    error_out_if,
    output_measurement,
    output_named_measurement,
    output_status,
    prompt,
    output_err
)


class ScopePromptUI:
    def __init__(self, svi3_controller, scope_controller, rail_name):
        """
        Initialize with SVI3 automation object and scope controller.
        The Tk window will be created during build_ui().
        """
        self.svi3 = svi3_controller
        self.scope = scope_controller
        self.rail_name = rail_name
        self.root = None
        self.old_vid = None
        self.target_vid = None
        self.test_case_num = None
        self.completed = False  # Flag to indicate completion

    def build_ui(self, old_vid, target_vid, test_case_num, output_data):
        self.output_data = output_data
        self.old_vid = old_vid
        self.target_vid = target_vid
        self.test_case_num = test_case_num

        self.root = tk.Tk()
        self.root.title("Scope Setup Prompt")
        self.root.geometry("600x500")  # Increased height
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Half the screen width, full screen height
        width = screen_width // 2
        height = screen_height

        # Align to the left edge
        x = 0
        y = 0

        self.root.geometry(f"{width}x{height}+{x}+{y}")

        self.root.resizable(False, False)
        # Bring to front immediately
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(500, lambda: self.root.attributes("-topmost", False))  # Let it stay on top briefly
        # Title
        ttk.Label(self.root, text=f"Test Case: {self.test_case_num}", font=("Segoe UI", 14, "bold")).pack(pady=10)

        # Voltage Group Frame
        voltage_frame = ttk.LabelFrame(self.root, text="Set Voltage", padding=10)
        voltage_frame.pack(padx=10, pady=10, fill="x")

        self.add_voltage_row(voltage_frame, f"Old VID ({old_vid}mV):", old_vid)
        self.add_voltage_row(voltage_frame, f"Target VID ({target_vid}mV):", target_vid)

         # Measurement Group Frame
        measurement_frame = ttk.LabelFrame(self.root, text="Measurements", padding=10)
        measurement_frame.pack(padx=10, pady=10, fill="x")

        self.add_measurement_row(measurement_frame, "Picture_1_Slew_rate:")
        self.add_measurement_row(measurement_frame, "Picture_2_VOTFC_Time:")
        self.add_measurement_row(measurement_frame, "Picture_3_Vmin@VOTF:")
        self.add_measurement_row(measurement_frame, "Picture_4_VOTF_Down_Slop:")
        

        # Screenshot Group Frame
        screenshot_frame = ttk.LabelFrame(self.root, text="Scope Capture (stored in Result folder)", padding=10)
        screenshot_frame.pack(padx=10, pady=10, fill="x")

        self.add_capture_button(screenshot_frame, "Picture_1_Slew_rate_capture")
        self.add_capture_button(screenshot_frame, "Picture_2_VOTFC_Time_capture")
        self.add_capture_button(screenshot_frame, "Picture_3_Vmin@VOTF_capture")
        self.add_capture_button(screenshot_frame, "Picture_4_VOTF_Down_Slop_Capture")
        
       
        # Next Button
        Output_data = ttk.Button(self.root, text="Next", command=self.on_next).pack(pady=15)

        self.root.protocol("WM_DELETE_WINDOW", self.disable_close)
        self.root.mainloop()

        return Output_data

    def add_measurement_row(self, parent, pic_name):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=5)

        ttk.Label(row, text=f"Case_{self.test_case_num}_{pic_name}", width=35).pack(side="left", padx=5)
        ttk.Button(row, text="Enable Measurement", command=lambda name=pic_name: self.scope_measurement(name)).pack(side="left")

    def scope_measurement(self, pic_name):
        if "Picture_1" in pic_name:
            self.scope.clear_all_measurements()
            time.sleep(0.5) 
            self.scope.enable_measurements(["RISetime","MAXIMUM"]) 
            time.sleep(0.5)  
            self.scope.enable_cursor()
            time.sleep(0.5)
            self.scope.rise_time_cursor()
            time.sleep(0.5)
            
        elif "Picture_2" in pic_name:
            self.scope.clear_all_measurements()
            time.sleep(0.5) 
            self.scope.enable_cursor("OFF")
            time.sleep(0.5)
            self.scope.enable_cursor("ON")
            time.sleep(0.5) 
            
        elif "Picture_3" in pic_name:
            self.scope.clear_all_measurements()
            time.sleep(0.5) 
            self.scope.enable_cursor("OFF")
            time.sleep(0.5)
            self.scope.enable_cursor("ON")
            time.sleep(0.5) 
        elif "Picture_4" in pic_name:
            self.scope.clear_all_measurements()
            time.sleep(0.5) 
            self.scope.enable_cursor("OFF")
            time.sleep(0.5)
            self.scope.enable_cursor("ON")
            time.sleep(0.5) 
        else:
            output_err(f"[ERROR] Unknown measurement type for {pic_name}")
            return
    
    def add_voltage_row(self, parent, label, value):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=5)

        # Left side - VID setting
        left_frame = ttk.Frame(row)
        left_frame.pack(side="left", fill="x", expand=True)
        
        ttk.Label(left_frame, text=label, width=30).pack(side="left", padx=5)
        ttk.Button(left_frame, text="Set VID", command=lambda: self.set_vid(value)).pack(side="left", padx=5)
        
        # Right side - Trigger level buttons (only for the first row)
        if "Old VID" in label:
            right_frame = ttk.Frame(row)
            right_frame.pack(side="right", padx=10)
            
            # Rise trigger button
            ttk.Button(right_frame, text="Set Trigger Rise", 
                    command=lambda: self.scope.set_trigger_level(self.old_vid/1000, 
                                                                self.target_vid/1000, 
                                                                slope="RISE")).pack(side="left", padx=2)
            
            # Fall trigger button
            ttk.Button(right_frame, text="Set Trigger Fall", 
                    command=lambda: self.scope.set_trigger_level(self.old_vid/1000, 
                                                                self.target_vid/1000, 
                                                                slope="FALL")).pack(side="left", padx=2)
    
    
    # def add_voltage_row(self, parent, label, value):
    #     row = ttk.Frame(parent)
    #     row.pack(fill="x", pady=5)

    #     # Left side - VID setting
    #     left_frame = ttk.Frame(row)
    #     left_frame.pack(side="left", fill="x", expand=True)
        
    #     ttk.Label(left_frame, text=label, width=30).pack(side="left", padx=5)
    #     ttk.Button(left_frame, text="Set VID", command=lambda: self.set_vid(value)).pack(side="left", padx=5)
        
    #     # Right side - Trigger level button (only for the first row)
    #     if "Old VID" in label:
    #         trigger_btn = ttk.Button(row, text="Set Trigger Level", 
    #                             command=lambda: self.scope.set_trigger_level(self.old_vid/1000, self.target_vid/1000))
    #         trigger_btn.pack(side="right", padx=10)    

    # def add_voltage_row(self, parent, label, value):
    #     row = ttk.Frame(parent)
    #     row.pack(fill="x", pady=5)

    #     ttk.Label(row, text=label, width=30).pack(side="left", padx=5)
    #     ttk.Button(row, text="Set VID", command=lambda: self.set_vid(value)).pack(side="left", padx=5)

    # def add_capture_button(self, parent, pic_name):
    #     row = ttk.Frame(parent)
    #     row.pack(fill="x", pady=7)

    #     ttk.Label(row, text=f"Case_{self.test_case_num}_{pic_name}", width=35).pack(side="left", padx=5)
    #     ttk.Button(row, text="Capture", command=lambda name=pic_name: self.capture_screen(name)).pack(side="left")
    #     # if pic_name == "Picture_1_Slew_rate_capture":
    #     #     ttk.Button(row, text="Minimum", command=lambda name=pic_name: self.get_minimum(name)).pack(side="left", padx=2)
    # ############new line to add tooltip
    
    
    def add_capture_button(self, parent, pic_name):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=7)

        # Create label and capture button
        ttk.Label(row, text=f"Case_{self.test_case_num}_{pic_name}", width=35).pack(side="left", padx=5)
        capture_btn = ttk.Button(row, text="Capture", command=lambda name=pic_name: self.capture_screen(name))
        capture_btn.pack(side="left")

        # Create info box with tooltip
        info_text = self.get_tooltip_text(pic_name)
        info_box = ttk.Label(row, text="ℹ", background='lightgray', width=3)
        info_box.pack(side="left", padx=5)

        # Create tooltip
        self.create_tooltip(info_box, info_text)

    def get_tooltip_text(self, pic_name):
        """Return specific tooltip text based on picture name"""
        tooltips = {
            "Picture_1_Slew_rate_capture": "Capture slew rate measurement\n- Before capture, Set x and y cursors at the intersection for 20% and 80% VID\n",
            "Picture_2_VOTFC_Time_capture": "Capture VOTF time measurement\n- Place vertical cursor B at the end of clk and Place vertical cursor A at 20 percent lower than targeted voltage\n- Measure time between points",
            "Picture_3_Vmin@VOTF_capture": "Capture minimum voltage during VOTF\n- Place horizontal cursor B at the level 20 percent lower than targeted voltage. Place horizontal cursor A at targeted voltage\n",
            "Picture_4_VOTF_Down_Slop_Capture": "Capture VOTF down slope\n- Set cursors for target VID and VID-20mV\n -Dont forget to change slope to falling\n- Measure time between points",
        }
        return tooltips.get(pic_name, "No tooltip available")

    def create_tooltip(self, widget, text):
        """Create a tooltip for a given widget"""
        tooltip = tk.Toplevel(widget)
        tooltip.withdraw()
        tooltip.overrideredirect(True)
        
        label = ttk.Label(tooltip, text=text, justify="left", background="#ffffe0", 
                        relief="solid", borderwidth=1, padding=(5, 5))
        label.pack()

        def show_tooltip(event=None):
            tooltip.deiconify()
            # Position tooltip near the info box
            x = widget.winfo_rootx() + widget.winfo_width()
            y = widget.winfo_rooty()
            tooltip.geometry(f"+{x+5}+{y}")

        def hide_tooltip(event=None):
            tooltip.withdraw()

        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)
        
    
    
    
    
    
    def set_vid(self, value):
        """
        Sends VID to SVI3.
        """
        try:
            mv_value = f"{value}mV"
            self.svi3.maximize()
            self.svi3.key_in_value("VID", mv_value)
            self.svi3.click("Set_VID")
            output_status(f"[INFO] Set VID to {mv_value}")
            self.svi3.minimize()
        except Exception as e:
            output_err(f"[ERROR] Failed to set VID: {e}")

    
    def capture_screen(self, name):
        """
        Captures screenshot from MSO46B scope and saves into Result/rail_name.
        """
        try:
            # folder = os.path.join("Result", self.rail_name)
            folder = os.path.join("C:\\Users\\HPS Penang Tester\\Documents\\python\\Load_slammer\\Result", self.rail_name)
            os.makedirs(folder, exist_ok=True)

            filename = f"Case_{self.test_case_num}_{name}.png"
            filepath = os.path.join(folder, filename)

            
            # Ensure "measured data" is a dictionary
            if self.output_data["VOTF_test"]["Test Case"]["{}".format(self.test_case_num)]["measured data"] is None:
                self.output_data["VOTF_test"]["Test Case"]["{}".format(self.test_case_num)]["measured data"] = {}

            # Now safely add your picture path

            if "Picture_1" in filepath:
                rise_time = self.scope.measure_rise_time(["RISETIME"]) 
                maximum_voltage=self.scope.measure_maximum() # Get the measurement
                #tA tB in us. 
                # vA vB in mV
                tA,tB, vA,vB = self.scope.get_all_cursor_positions()
                #self.output_data["VOTF_test"]["Test Case"]["{}".format(self.test_case_num)]["measured data"][
                #    "Picture 1"] = filepath
                self.output_data["VOTF_test"]["Test Case"]["{}".format(self.test_case_num)]["measured data"][
                    "Picture 1"] = {
                        "filepath": filepath,
                        "rise_time": rise_time,
                        "time_cursor_A(us)": tA,
                        "time_cursor_B(us)": tB,
                        "measure 80% VID up": vA if vA>2 else vA*1000,
                        "Measure 20% VID up": vB if vB>2 else vB*1000,
                        "voltage_delta": abs(vB - vA),
                        "Change in time(us)": abs(tB - tA),
                        "Vmax@VOTF(mV)": maximum_voltage if maximum_voltage>2 else maximum_voltage*1000,    
                    }
            elif "Picture_2" in filepath:
                #tA tB in us. 
                # vA vB in mV
                tA,tB, vA,vB = self.scope.get_all_cursor_positions()
                time.sleep(0.1)
                self.output_data["VOTF_test"]["Test Case"]["{}".format(self.test_case_num)]["measured data"][
                    "Picture 2"] = {
                        "filepath": filepath,
                        "VOTF Time (us)": abs(tB - tA)
                    }
                # self.output_data["VOTF_test"]["Test Case"]["{}".format(self.test_case_num)]["measured data"][
                #     "Picture 2"] = filepath

            if "Picture_3" in filepath:
                #tA tB in us. 
                # vA vB in mV
                tA,tB, vA,vB = self.scope.get_all_cursor_positions()
                time.sleep(0.1)
                self.output_data["VOTF_test"]["Test Case"]["{}".format(self.test_case_num)]["measured data"][
                    "Picture 3"] = {
                        "filepath": filepath,
                        "Vmin@VOTF(mV)": vB if vB>2 else vB*1000, 
                    }
                # self.output_data["VOTF_test"]["Test Case"]["{}".format(self.test_case_num)]["measured data"][
                #     "Picture 3"] = filepath

            if "Picture_4" in filepath:
                #tA tB in us. 
                # vA vB in mV
                tA,tB, vA,vB = self.scope.get_all_cursor_positions()
                time.sleep(0.1)
                self.output_data["VOTF_test"]["Test Case"]["{}".format(self.test_case_num)]["measured data"][
                    "Picture 4"] = {
                        "filepath": filepath,
                        "measure target  VID(mV))": vA, 
                        "measure target VID -20mV(mV)": vB,
                    }   

                # self.output_data["VOTF_test"]["Test Case"]["{}".format(self.test_case_num)]["measured data"][
                #     "Picture 4"] = filepath

            self.scope.inst.write("HARDCopy:INKSaver ON")
            self.scope.inst.write("HARDCopy:FORMat PNG")
            self.scope.inst.write("HARDCopy:PORT FILE")
            self.scope.inst.write("HARDCopy:LAYout FULL")
            self.scope.inst.write("HARDCopy:PREView OFF")
            self.scope.inst.write("HARDCopy STARt")

            self.scope.inst.timeout = 20000  # 20 seconds
            self.scope.inst.write('SAVE:IMAGE "C:/Temp.png"')
            time.sleep(0.5)  # Wait for the command to process
            self.scope.inst.query('*OPC?')
            self.scope.inst.write('FILESystem:READFile "C:/Temp.png"')
            time.sleep(0.5)  # Wait for file to be ready
            raw_data = self.scope.inst.read_raw()
            with open(filepath, 'wb') as f:
                f.write(raw_data)
            self.scope.inst.write('FILESystem:DELEte "C:/Temp.png"')

            # raw_data = self.scope.inst.read_raw()
            # raw_data = self.scope.inst.write("SAVe:IMAGe:{}".format(filepath))
            # self.scope.inst.write("SAVe:IMAGe:{}".format(filepath))
            # self.scope.inst.query('*OPC?')

            # self.scope.inst.write('FILESystem:READFile {}'.format(filepath))
            # self.scope.inst.query('*OPC?')
            # imgData = self.scope.inst.read_raw(1024*1024)

            # raw_data = self.scope.inst.write("SAVe:IMAGe:VIEWTYpe {FULLScreen}")
            # SAVE:IMAGE “C:/Dut12–tests.png”

            # with open(filepath, "wb") as f:
            #     f.write(raw_data)

            output_status(f"[INFO] Screenshot of Test{self.test_case_num} - {name} saved: {filepath}")
        except Exception as e:
            output_err(f"[ERROR] Scope screenshot failed for {name}: {e}")

    def on_next(self):
        output_status("[INFO] Test case complete.")
        output_status("[INFO] Test case complete.")
        self.completed = True
        self.root.iconify()   # minimize the window
        self.root.quit() # Use quit() instead of destroy() to allow mainloop to finish

    def get_output_data(self):
        """
        Call this method after mainloop() completes to get the output data
        """
        if self.completed:
            return self.output_data
        return None

    def disable_close(self):
        pass  # Prevent manual window close
