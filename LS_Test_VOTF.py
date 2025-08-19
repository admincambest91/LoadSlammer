import LS_test_framework
import sys
import datetime
from time import sleep as sl
import excel_main_control as emc
import json
import os
from openpyxl.drawing.image import Image
from openpyxl.utils import column_index_from_string, get_column_letter
import general_function as ir
from console_app import (
    error_out_if,
    output_measurement,
    output_named_measurement,
    output_status,
    prompt,
    output_err
)


class VOTF():
    def setup(self, equipment, parameters,workbook,worksheet,SVI3_coordinate,excel_result_coordinate,test_key):
        self.parameters = parameters
        self.loadslammer=equipment["LoadSlammer"]
        self.SVI3=equipment["SVI3"]
        self.scope=equipment["MSO46B"]
        self.SVI3_coordinate=SVI3_coordinate
        self.excel_result_coordinate=excel_result_coordinate
        self.workbook=workbook
        self.worksheet=worksheet
        self.test_key=test_key
        self.gui=equipment["GUI"]
        
        

        #setting up test parameter
        self.dynamic_VID=self.parameters["VOTF Test"]["Test Case"]
        self.spec_calibration=self.parameters["SPEC calibration"]
        
        

        try:
        # Step 1: Connect to the application
            self.loadslammer.initialize()
            self.loadslammer.minimize()
            output_status("successfully load and connect LoadSlammer software")
        #Step 2: initialize SVI3 software
            self.SVI3.initialize()
            self.SVI3.minimize()
            output_status("successfully load and connect SVI3 software")  
            sl(1)
            
        except Exception as e:
                output_err(f"\nAn unhandled error occurred during automation: {e}")
    
    
    def run(self):
        
        #Step 3: Initialize output data structure
        # This will be used to store the results of the test
        Output_data = {
    "Spec_calibration": {"VID voltage": {}},
    "VOTF_test": {"Test Case":{}}
}

        #Step 4: set voltage rail in loadslammer:
        self.loadslammer.maximize()
        self.loadslammer.change_rail(self.test_key)
        
        # #run calibration first

        # #start with VID, iterate through the VID voltage
        # scope_measurements_setting=["MEAN"]
        # self.scope.clear_all_measurements()
        # self.scope.enable_measurements(scope_measurements_setting)
        # for vid_str, vid_info in self.spec_calibration["VID voltage"].items():
        #     self.loadslammer.minimize()

        #     #get the VID for SVI3 voltage set later
        #     vid_mV = int(vid_str)

        #     #create a dictionary for this VID
        #     #this will be used to store the results for this VID
        #     #e.g. Output_data["Spec_calibration"]["VID voltage"]["550"] = {}
        #     #where 550 is the VID in mV
        #     Output_data["Spec_calibration"]["VID voltage"][vid_mV] = {}  
            
            
        #     #set the voltage in SVI3
        #     #this will set the VID in SVI3 to the VID in mV
        #     #e.g. if vid_mV is 550, it will set the VID to 550mV
        #     output_status(f"Setting VID to {vid_mV}mV")
        #     self.SVI3.maximize()
        #     actual_VID=int(vid_mV)/1000
        #     self.SVI3.key_in_value('VID','{}V'.format(actual_VID))
        #     self.SVI3.click('Set_VID')
        #     sl(0.5)
        #     self.SVI3.minimize()

        #     #get the currents for this VID
        #     #this will be a list of currents in A
        #     #this will be used to set the current in LoadSlammer
        #     #and to store the results in Output_data
        #     currents = vid_info["IDD test current (A)"]

        #     #iterate through the currents for this VID
        #     for current in currents:   
        #         #create a dictionary for this current. value will be set later
        #         Output_data["Spec_calibration"]["VID voltage"][vid_mV][current] = {"measured_vout": None}  
        #         sl(0.2)
                
        #         #set the current
        #         self.loadslammer.maximize()
        #         self.loadslammer.adjust_test_current(current)
        #         self.loadslammer.slam()
        #         output_status(f"Setting current to {current}A for VID {vid_mV}mV")
        #         sl(0.1)
        #         self.loadslammer.minimize()

        #         #get the stable voltage measurement
        #         is_light_load = (float(current) <= 0.01)
        #         v_mean = self.scope.measure_stable_voltage(vid_mV, is_light_load)
        #         Output_data["Spec_calibration"]["VID voltage"][vid_mV][current]["measured_vout"] = v_mean
                
        #         # Add measurement quality indicators
        #         if is_light_load:
        #             expected_v = float(vid_mV)/1000
        #             deviation_pct = abs(v_mean - expected_v) / expected_v * 100
        #             Output_data["Spec_calibration"]["VID voltage"][vid_mV][current]["measurement_quality"] = {
        #                 "deviation_percent": round(deviation_pct, 2),
        #                 "is_within_spec": deviation_pct <= 5.0  # 5% tolerance
        #             }
                
        #         self.loadslammer.maximize()
        #         self.loadslammer.stop()
        #         self.loadslammer.minimize()
        #         v_mean = None
        
        self.scope.clear_all_measurements()
        # #run the VOTF test
        Output_data["VOTF_test"]["Test Case"]={}    
        for test_id, test_data in self.dynamic_VID.items():
            self.loadslammer.minimize()
            self.SVI3.minimize()

            #dict to store the results for  test case
            Output_data["VOTF_test"]["Test Case"]["{}".format(test_id)]={"measured data":None}
            
            self.SVI3.maximize()
            sl(0.1)
            
            #set the PSI mode in SVI3
            self.SVI3.key_in_value('PSI','{}'.format(test_data["PSI_Mode"]))
            self.SVI3.click('Set_PSI')

            #set the VID in SVI3
            self.SVI3.key_in_value('VID','{}mV'.format(test_data["Old_VID (mV)"]))
            self.SVI3.click('Set_VID')

            self.SVI3.minimize()

            #set scope offset following Old VID
            self.scope.offset(channel=1, offset=test_data["Old_VID (mV)"]/1000)
            
            self.loadslammer.maximize()
            self.loadslammer.adjust_test_current(test_data["IDD_Set (A)"])
            self.loadslammer.slam()


            self.loadslammer.minimize()
            
            #build the UI for the test case result capture from scope
            self.gui.build_ui(test_data["Old_VID (mV)"],test_data["Target_VID (mV)"],int(test_id),Output_data)
            self.loadslammer.maximize()
            self.loadslammer.stop()
            self.loadslammer.minimize()


            # for key, value in test_data.items():
            #     output_status(f"  {key} = {value}")
         
        
        output_dir  = "Result"
        output_file = os.path.join(output_dir, "Output_data.json")

        # 2. Create the directory if it doesn't exist
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)

        # 3. Dump (and overwrite) your JSON each run
        with open(output_file, "w") as f:
            json.dump(Output_data, f, indent=4)

        output_status(f"Results written to {output_file}")
        sl(1)
        

            
        
    def clean_up(self):
        with open('C:\\Users\\HPS Penang Tester\\Documents\\python\\Load_slammer\\Result\\Output_data.json', 'r') as file:
            data = json.load(file)

        calibration_coordinate=self.excel_result_coordinate[self.test_key]["Spec_Calibration"]
        VOTF_coordinate=self.excel_result_coordinate[self.test_key]["VOTF"]
        Calibration_data = data.get("Spec_calibration", {}).get("VID voltage", {})
        VOTF_data = data.get("VOTF_test", {}).get("Test Case", {})

        #caibration data
        
        for vid_mV, currents in Calibration_data.items():
            for current, values in currents.items():
                vout = values.get("measured_vout")
                if vout is not None:
                    # Convert column letter to number (A=1, B=2, etc.)
                    col_letter = calibration_coordinate["Test current"]["{}A".format(current)]["VID(mV)"][vid_mV]["column_start"]
                    col_number = ord(col_letter) - ord('A') + 1
                    
                    cell = self.worksheet.cell(row=calibration_coordinate["Test current"]["{}A".format(current)]["VID(mV)"][vid_mV]["row_start"],column=col_number)

                    cell.value = vout  # keep as a float, e.g., 1.234567
                    cell.number_format = "0.000"  # 3 decimal places

        #votf data

        
        ir.insert_votf_images(self.worksheet, VOTF_data, VOTF_coordinate)
        # for test_case, picture_files in VOTF_data.items():
        #     coordinates = VOTF_coordinate[f"Test_Case_{test_case}"]

        #     for i in range(1, 5):
        #         picture_key = f"Picture {i}"
        #         coord_key = list(coordinates.keys())[i - 1]  # get the coordinate dict key
        #         img_path = picture_files["measured data"][picture_key]

        #         if not os.path.exists(img_path):
        #             output_status(f"⚠ Missing file: {img_path}")
        #             continue
                
                

        #         # Extract coordinates
        #         row_start = coordinates[coord_key]["row_start"]
        #         row_end = coordinates[coord_key]["row_end"]
        #         col_start = coordinates[coord_key]["col_start"]
        #         col_end = coordinates[coord_key]["col_end"]

        #         # Convert column letters to numbers
        #         col_start_idx = column_index_from_string(col_start)
        #         col_end_idx = column_index_from_string(col_end)


        #         # Get starting cell reference
        #         row_start = coordinates[coord_key]["row_start"]
        #         col_start = coordinates[coord_key]["col_start"]
        #         cell_ref = f"{col_start}{row_start}"

               
        #         # Insert the image
        #         img = Image(img_path)
        #         self.worksheet.add_image(img, cell_ref)

        #         output_status("✅ All VOTF images inserted.")




                    
                    
        output_dir = "Result"
        os.makedirs(output_dir, exist_ok=True)  # ensure the folder exists
        time_date = ir.get_date_time_string()
        output_path = os.path.join(output_dir, "{}_{}.xlsx".format(self.parameters["raw_file_name"],time_date))  # change filename if needed
        self.workbook.save(output_path)
                    
        

    
    def describe(test_key):
        # This function describes the test parameters and equipment needed for the VOTF test.
        # It returns a dictionary with the necessary information.
        if test_key == "VDDCR_CPU0" or test_key == "VDDCR_SOC":
            parameter_json = "CPU0_SOC_votf_parameter.json"
            excel_result_coordinate= "CPU0_SOC_excel__result_coordinate.json"
        elif test_key == "VDDCR_CPU1" or test_key == "VDDIO":
            parameter_json = "CPU1_VDDIO_votf_parameter.json"
            excel_result_coordinate= "CPU1_VDD1O_excel__result_coordinate.json"
        
        #SVI3 software coordinate file
        SVI3_coordinate="SVI3_coordinate.json"

        #This function will return the main excel sheet for the test
        mainsheet_path=ir.select_file(test_key)
        
        # Extract parameters, and excel 
        extraction=emc.JSON_excel_extractor(parameter_json,mainsheet_path)
        parameter=extraction.load_json_file()
        workbook,worksheet=extraction.load_workbook()
        
        
        return {
            "requested_equipment": "LoadSlammer",
            "requested_parameters": parameter,
            "workbook": workbook,
            "worksheet":worksheet,
            "SVI3_coordinate":SVI3_coordinate,
            "excel_result_coordinate":excel_result_coordinate,
            "include_files": mainsheet_path,
            "about": "This test will apply a static current load to the test "
            + "target and measure various parameters.  The test will "
            + "iterate over multiple currents and VIDs to later analyze "
            + "between one another.",
        }


#main function to execute the test
if __name__ == "__main__":
    LS_test_framework.execute("VDDCR_CPU0", VOTF)
    

    