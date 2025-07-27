import os
from datetime import datetime

def capture_votf_screenshots(self, rail_name):
    """
    Captures 4 screenshots from the MSO46B and stores them in Result/<rail_name> folder.
    Screenshots are saved as PNG images with predefined names.
    """
    folder = os.path.join("Result", rail_name)
    os.makedirs(folder, exist_ok=True)  # Create if not exist

    picture_names = [
        "Picture_1_Slew_rate_capture",
        "Picture_2_VOTFC_Time_capture",
        "Picture_3_Vmin@VOTF_capture",
        "Picture_4_VOTF_Down_Slop_Capture"
    ]

    for i, name in enumerate(picture_names, start=1):
        filename = os.path.join(folder, f"{name}.png")

        try:
            # Set the file format (PNG is better for clarity)
            self.inst.write("HARDCopy:FORMat PNG")
            
            # Set destination as file
            self.inst.write(f"HARDCopy:PORT FILE")

            # Set file path
            self.inst.write(f"HARDCopy:FILename '{filename}'")

            # Trigger the capture
            self.inst.write("HARDCopy START")
            time.sleep(0.5)  # Let the file finish writing

            print(f"[INFO] Saved screenshot {i} as {filename}")
        except Exception as e:
            print(f"[ERROR] Could not save screenshot {i}: {e}")
