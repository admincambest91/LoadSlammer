import os
from openpyxl import Workbook
from openpyxl.drawing.image import Image
from PIL import Image as PILImage
from openpyxl.utils import get_column_letter
from openpyxl.utils import column_index_from_string
from time import sleep
from datetime import datetime
import platform
import tkinter as tk
from tkinter import filedialog
from console_app import (
    error_out_if,
    output_measurement,
    output_named_measurement,
    output_status,
    prompt,
    output_err
)


def insert_votf_images(worksheet, VOTF_data, VOTF_coordinate,raw_file_name=None):
    """
    Insert up to 4 VOTF images per test case into the given worksheet.

    Args:
        worksheet (Worksheet): The target openpyxl worksheet object.
        VOTF_data (dict): Dictionary containing picture file paths.
        VOTF_coordinate (dict): Dictionary containing image placement coordinates.

    Example:
        insert_votf_images(ws, VOTF_data, VOTF_coordinate)
    """
    for test_case, picture_files in VOTF_data.items():
        coordinates = VOTF_coordinate.get(f"Test_Case_{test_case}")
        single_cell_coordinate=coordinates['single_cell_result']
        if not coordinates:
            output_status(f"⚠ No coordinates found for Test_Case_{test_case}")
            continue

        for i in range(1, 5):
            picture_key = f"Picture {i}"
            coord_key = list(coordinates.keys())[i - 1]  # get the coordinate dict key
            img_path =picture_files["measured data"][picture_key]["filepath"] #picture_files.get("measured data", {}).get(picture_key)

            #place for single cell result
            if picture_key == "Picture 1":
               #add rise time to excel
                worksheet.cell(row= single_cell_coordinate["change in time(us)"]["row"],
                               column=column_index_from_string(single_cell_coordinate["change in time(us)"]["column"])).value = VOTF_data[test_case]["measured data"][picture_key]["Change in time(us)"]
                
                #add measure 20% VID up to excel
                worksheet.cell(row= single_cell_coordinate["measured 20% VID up"]["row"],
                               column=column_index_from_string(single_cell_coordinate["measured 20% VID up"]["column"])).value = VOTF_data[test_case]["measured data"][picture_key]["Measure 20% VID up"]

                #add measure 80% VID up to excel
                worksheet.cell(row= single_cell_coordinate["measured 80% VID up"]["row"],
                        column=column_index_from_string(single_cell_coordinate["measured 80% VID up"]["column"])).value = VOTF_data[test_case]["measured data"][picture_key]["measure 80% VID up"]

                #add measure Vmax@VOTF(mV) to excel
                worksheet.cell(row= single_cell_coordinate["Vmax@VOTF"]["row"],
                        column=column_index_from_string(single_cell_coordinate["Vmax@VOTF"]["column"])).value = VOTF_data[test_case]["measured data"][picture_key]["Vmax@VOTF(mV)"]

            if picture_key == "Picture 2":
                #add measure VOTF Time(us) to excel
                worksheet.cell(row= single_cell_coordinate["VOTF time(us)"]["row"],
                        column=column_index_from_string(single_cell_coordinate["VOTF time(us)"]["column"])).value = VOTF_data[test_case]["measured data"][picture_key]["VOTF Time (us)"]

            if picture_key=="Picture 3":
                #add measure Vmin@VOTF(mV) to excel
                worksheet.cell(row= single_cell_coordinate["Vmin@VOTF"]["row"],
                        column=column_index_from_string(single_cell_coordinate["Vmin@VOTF"]["column"])).value = VOTF_data[test_case]["measured data"][picture_key]["Vmin@VOTF(mV)"]

            if not img_path:
                output_status(f"⚠ Missing path for {picture_key} in Test_Case_{test_case}")
                continue

            if not os.path.exists(img_path):
                output_status(f"⚠ Missing file: {img_path}")
                continue


            
            pil_img = PILImage.open(img_path)

            # Get dimensions
            original_width, original_height = pil_img.size
            #output_status(f"Original image dimensions: {original_width}x{original_height} pixels")
            
            col_start = column_index_from_string(coordinates[coord_key]["col_start"])
            col_end = column_index_from_string(coordinates[coord_key]["col_end"]) if "col_end" in coordinates[coord_key] else col_start

            # Calculate total width in pixels for the specified columns
            total_width_px = 0
            for col in range(col_start, col_end + 1):
                col_letter = get_column_letter(col)
                col_width = worksheet.column_dimensions[col_letter].width or 8.43
                total_width_px += col_width * 6.7
            
            # Calculate total height in pixels
            row_start = coordinates[coord_key]["row_start"]
            row_end = coordinates[coord_key]["row_end"] if "row_end" in coordinates[coord_key] else row_start
            total_height_px = 0
            for row in range(row_start, row_end + 1):
                row_height = worksheet.row_dimensions[row].height or 15
                total_height_px += int(row_height * 96 / 72)
            
            img = Image(img_path)
            img.height = total_width_px# insert image height in pixels as float or int (e.g. 305.5)
            img.width= total_height_px#insert image width in pixels as float or int (e.g. 405.8)
            img.anchor = "{}{}".format(coordinates[coord_key]["col_start"],row_start) # where you want image to be anchored/start from
            worksheet.add_image(img)
            output_status(f"✅ Inserted {picture_key} for Test_Case_{test_case} at {coordinates[coord_key]['col_start']}{row_start}")
            sleep(0.5)        
            
            

            # # Get starting cell reference
            # row_start = coordinates[coord_key]["row_start"]
            # col_start = coordinates[coord_key]["col_start"]
            # cell_ref = f"{col_start}{row_start}"

            # # Insert the image
            # img = Image(img_path)
            # worksheet.add_image(img, cell_ref)

    output_status("✅ All VOTF images inserted.")


def extract_sp5_name(file_path: str) -> str:
    # Step 1: Get just the file name
    file_name = os.path.basename(file_path)
    
    # Step 2: Remove extension
    name_without_ext = os.path.splitext(file_name)[0]
    
    # Step 3: Find where "SP5" starts and return from there
    start_index = name_without_ext.find("SP5")
    if start_index != -1:
        return name_without_ext[start_index:]
    else:
        return name_without_ext  # If "SP5" not found, just return the whole name



def get_date_time_string():
    now = datetime.now()
    
    if platform.system() == "Windows":
        return now.strftime("DATE_%#d_%#m_%Y_TIME_%#I_%M_%p")
    else:
        return now.strftime("DATE_%-d_%-m_%Y_TIME_%-I_%M_%p")



def select_file(test_key):
    root = tk.Tk()
    root.withdraw()  # Hide main window
    mainsheet = filedialog.askopenfilename(
        title="Select a mainsheet for {}".format(test_key),
        filetypes=[("Excel files", "*.xlsx *.xlsm *.xls"), ("All files", "*.*")]
    )
    return mainsheet




