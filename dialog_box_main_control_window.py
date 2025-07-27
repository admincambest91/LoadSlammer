import os
import tkinter as tk
from tkinter import ttk


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

    def build_ui(self, old_vid, target_vid, test_case_num):
        self.old_vid = old_vid
        self.target_vid = target_vid
        self.test_case_num = test_case_num

        self.root = tk.Tk()
        self.root.title("Scope Setup Prompt")
        self.root.geometry("550x420")
        self.root.resizable(False, False)

        # Title
        ttk.Label(self.root, text=f"Test Case: {self.test_case_num}", font=("Segoe UI", 14, "bold")).pack(pady=10)

        # Voltage Group Frame
        voltage_frame = ttk.LabelFrame(self.root, text="Set Voltage", padding=10)
        voltage_frame.pack(padx=10, pady=10, fill="x")

        self.add_voltage_row(voltage_frame, f"Old VID ({old_vid}mV):", old_vid)
        self.add_voltage_row(voltage_frame, f"Target VID ({target_vid}mV):", target_vid)

        # Screenshot Group Frame
        screenshot_frame = ttk.LabelFrame(self.root, text="Scope Capture (stored in Result folder)", padding=10)
        screenshot_frame.pack(padx=10, pady=10, fill="x")

        self.add_capture_button(screenshot_frame, "Picture_1_Slew_rate_capture")
        self.add_capture_button(screenshot_frame, "Picture_2_VOTFC_Time_capture")
        self.add_capture_button(screenshot_frame, "Picture_3_Vmin@VOTF_capture")
        self.add_capture_button(screenshot_frame, "Picture_4_VOTF_Down_Slop_Capture")

        # Next Button
        ttk.Button(self.root, text="Next", command=self.on_next).pack(pady=15)

        self.root.protocol("WM_DELETE_WINDOW", self.disable_close)
        self.root.mainloop()

    def add_voltage_row(self, parent, label, value):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=5)

        ttk.Label(row, text=label, width=30).pack(side="left", padx=5)
        ttk.Button(row, text="Set VID", command=lambda: self.set_vid(value)).pack(side="left", padx=5)

    def add_capture_button(self, parent, pic_name):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=5)

        ttk.Label(row, text=f"Case_{self.test_case_num}_{pic_name}", width=35).pack(side="left", padx=5)
        ttk.Button(row, text="Capture", command=lambda name=pic_name: self.capture_screenshot(name)).pack(side="left")

    def set_vid(self, value):
        """
        Sends VID to SVI3.
        """
        try:
            mv_value = f"{value}mV"
            self.svi3.maximize()
            self.svi3.key_in_value("VID", mv_value)
            self.svi3.click("Set_VID")
            print(f"[INFO] Set VID to {mv_value}")
            self.svi3.minimize()
        except Exception as e:
            print(f"[ERROR] Failed to set VID: {e}")

    def capture_screenshot(self, name):
        """
        Captures screenshot from MSO46B scope and saves into Result/rail_name.
        """
        try:
            folder = os.path.join("Result", self.rail_name)
            os.makedirs(folder, exist_ok=True)

            filename = f"Case_{self.test_case_num}_{name}.png"
            filepath = os.path.join(folder, filename)

            self.scope.inst.write("HARDCopy:INKSaver OFF")
            self.scope.inst.write("HARDCopy:FORMat PNG")
            self.scope.inst.write("HARDCopy:PORT FILE")
            self.scope.inst.write("HARDCopy:LAYout FULL")
            self.scope.inst.write("HARDCopy:PREView OFF")
            self.scope.inst.write("HARDCopy STARt")

            raw_data = self.scope.inst.read_raw()

            with open(filepath, "wb") as f:
                f.write(raw_data)

            print(f"[INFO] Screenshot saved: {filepath}")
        except Exception as e:
            print(f"[ERROR] Scope screenshot failed for {name}: {e}")

    def on_next(self):
        print("[INFO] Test case complete.")
        self.root.destroy()

    def disable_close(self):
        pass  # Prevent manual window close
