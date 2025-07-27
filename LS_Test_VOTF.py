import LS_test_framework
import sys
import datetime
from time import sleep as sl
import excel_main_control as emc
import json
import os


class VOTF():
    def setup(self, equipment, parameters,workbook,worksheet,SVI3_coordinate,test_key):
        self.parameters = parameters
        self.loadslammer=equipment["LoadSlammer"]
        self.SVI3=equipment["SVI3"]
        self.scope=equipment["MSO46B"]
        self.SVI3_coordinate=SVI3_coordinate
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
        

        # #run calibration first
        # for vid_str, vid_info in self.spec_calibration["VID voltage"].items():
            
        #     # vid_str is e.g. "550" (string); convert to int if you need numeric VID
        #     vid_mV = int(vid_str) 
        #     Output_data["Spec_calibration"]["VID voltage"][vid_mV] = {}  
        #     # pull out the current list
        #     currents = vid_info["IDD test current (A)"]
            
            
        #     for current in currents:
                
        #         Output_data["Spec_calibration"]["VID voltage"][vid_mV][current] = {
        #     "measured_vout": None
        # }  
        #         self.SVI3.maximize()
        #         #click rail under test in SVI3
        #         self.SVI3.click(self.test_key)
        #         sl(0.2)

        #         #set the voltage
        #         actual_VID=int(vid_mV)/1000
        #         self.SVI3.key_in_value('VID','{}V'.format(actual_VID))
        #         self.SVI3.click('Set_VID')
        #         sl(0.1)
        #         self.SVI3.minimize()

        #         self.loadslammer.adjust_test_current(current)
        #         self.loadslammer.slam()
        #         sl(0.1)
        #         self.loadslammer.minimize()


        #         ############
        #         #change to scope rading later
        #         v_rms="{} mV".format(current)#self.scope.measure_rms()
                
        #         Output_data["Spec_calibration"]["VID voltage"][vid_mV][current]["measured_vout"] = v_rms
        #         self.loadslammer.maximize()
        #         self.loadslammer.stop()
        #         self.loadslammer.minimize()
        
        
        #run the VOTF test
        #for Test_case, num in self.dynamic_VID["Test Case"].items():
        
        

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
            self.gui.build_ui(test_data["Old_VID (mV)"],test_data["Target_VID (mV)"],int(test_id))
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
        #sys.exit(1) # Exit if connection fails
        pass

    
    def describe():
        CPU0_SOC_json="CPU0_SOC_votf_parameter.json"
        CPU1_VDDIO_json="CPU1_VDDIO_votf_parameter.json"
        CPU0_SOC_mainsheet="C:\\Users\\HPS Penang Tester\\Documents\\python\Load_slammer\\LoadSlammer_Testplan\\SP5_CPU_SVI3_VDDCRCPU0_VDDCRSOC_Analysis_V0_2.xlsm"
        CPU1_VDDIO_mainsheet="C:\\Users\\HPS Penang Tester\\Documents\\python\\Load_slammer\\LoadSlammer_Testplan\\SP5_CPU_SVI3_VDDCRCPU1_VDDIO_ Analysis_V0_2.xlsm"
        SVI3_coordinate="SVI3_coordinate.json"
        extraction=emc.JSON_excel_extractor(CPU0_SOC_json,CPU0_SOC_mainsheet)
        parameter=extraction.load_json_file()
        workbook,worksheet=extraction.load_workbook()
        
        
        return {
            "requested_equipment": "LoadSlammer",
            "requested_parameters": parameter,
            "workbook": workbook,
            "worksheet":worksheet,
            "SVI3_coordinate":SVI3_coordinate,
            "include_files": None,
            "about": "This test will apply a static current load to the test "
            + "target and measure various parameters.  The test will "
            + "iterate over multiple currents and VIDs to later analyze "
            + "between one another.",
        }

if __name__ == "__main__":
    LS_test_framework.execute("VDDCR_SOC", VOTF)
    

    