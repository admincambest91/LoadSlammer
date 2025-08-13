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
            #initialize SVI3 software
            self.SVI3.initialize()
            self.SVI3.minimize()
            print("successfully load and connect SVI3 software")
                
            sl(1)
            
        except Exception as e:
                print(f"\nAn unhandled error occurred during automation: {e}")
    
    
    def run(self):
        
        Output_data = {
    "Spec_calibration": {"VID voltage": {}},
    "VOTF_test": {"Test Case":{}}
}

        #set voltage rail in loadslammer:
        self.loadslammer.maximize()
        self.loadslammer.change_rail(self.test_key)
        #self.loadslammer.minimize()
        
        #################################################################################
        #run calibration first
        for vid_str, vid_info in self.spec_calibration["VID voltage"].items():
            self.loadslammer.minimize()
            # vid_str is e.g. "550" (string); convert to int if you need numeric VID
            vid_mV = int(vid_str) 
            Output_data["Spec_calibration"]["VID voltage"][vid_mV] = {}  
            # pull out the current list
            
            #set the voltage
            print(f"Setting VID to {vid_mV}mV")
            self.SVI3.maximize()
            actual_VID=int(vid_mV)/1000
            self.SVI3.key_in_value('VID','{}V'.format(actual_VID))
            self.SVI3.click('Set_VID')
            sl(0.1)
            self.SVI3.minimize()
            currents = vid_info["IDD test current (A)"]
            
            
            for current in currents:
                
                Output_data["Spec_calibration"]["VID voltage"][vid_mV][current] = {
            "measured_vout": None}  
                
                #click rail under test in SVI3
                #disable change rail in SVI3, do it manually during start of the test
                #self.SVI3.click(self.test_key)
                sl(0.2)

                
                #set the current
                self.loadslammer.maximize()
                
                self.loadslammer.adjust_test_current(current)
                self.loadslammer.slam()
                sl(0.1)
                self.loadslammer.minimize()
                v_mean=self.scope.measure_mean()


                ############
                #change to scope rading later
                
                
                Output_data["Spec_calibration"]["VID voltage"][vid_mV][current]["measured_vout"] =v_mean
                self.loadslammer.maximize()
                self.loadslammer.stop()
                self.loadslammer.minimize()
        
        
        # #run the VOTF test
        # #for Test_case, num in self.dynamic_VID["Test Case"].items():
        
        

        Output_data["VOTF_test"]["Test Case"]={}    
        for test_id, test_data in self.dynamic_VID.items():
            self.loadslammer.minimize()
            self.SVI3.minimize()

            Output_data["VOTF_test"]["Test Case"]["{}".format(test_id)]={"measured data":None}
            
            self.SVI3.maximize()
            sl(0.1)
            
            self.SVI3.key_in_value('PSI','{}'.format(test_data["PSI_Mode"]))
            self.SVI3.click('Set_PSI')

            self.SVI3.key_in_value('VID','{}mV'.format(test_data["Old_VID (mV)"]))
            self.SVI3.click('Set_VID')

            self.SVI3.minimize()
            self.loadslammer.maximize()
            self.loadslammer.adjust_test_current(test_data["IDD_Set (A)"])
            self.loadslammer.slam()


            self.loadslammer.minimize()
            #ADD FUNCTION TO TRIGGER THE SCOPE
            data=self.gui.build_ui(test_data["Old_VID (mV)"],test_data["Target_VID (mV)"],int(test_id),Output_data)
            #self.gui.show()
            self.loadslammer.maximize()
            self.loadslammer.stop()


            # for key, value in test_data.items():
            #     print(f"  {key} = {value}")
         
        
        output_dir  = "Result"
        output_file = os.path.join(output_dir, "Output_data.json")

        # 2. Create the directory if it doesn't exist
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)

        # 3. Dump (and overwrite) your JSON each run
        with open(output_file, "w") as f:
            json.dump(Output_data, f, indent=4)

        print(f"Results written to {output_file}")
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
        #             print(f"⚠ Missing file: {img_path}")
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

        #         print("✅ All VOTF images inserted.")




                    
                    
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
        
        #This function will return the main excel sheet for the test
        if test_key == "VDDCR_CPU0" or test_key == "VDDCR_SOC":
            # CPU0_SOC_mainsheet is the main excel sheet for CPU0_SOC test
            mainsheet_path="C:\\Users\\HPS Penang Tester\\Documents\\python\Load_slammer\\LoadSlammer_Testplan\\SP5_CPU_SVI3_VDDCRCPU0_VDDCRSOC_Analysis_V0_2.xlsm"
        elif test_key == "VDDCR_CPU1" or test_key == "VDDIO":
            # CPU1_VDDIO_mainsheet is the main excel sheet for CPU1_VDDIO test
            mainsheet_path="C:\\Users\\HPS Penang Tester\\Documents\\python\\Load_slammer\\LoadSlammer_Testplan\\SP5_CPU_SVI3_VDDCRCPU1_VDDIO_ Analysis_V0_2.xlsm"
        


    # File does not exist; handle the error
        SVI3_coordinate="SVI3_coordinate.json"

        # with open(excel_result_coordinate, 'r') as f:
        #     excel_result_data = json.load(f)

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
    

    