import LS_test_framework
import automate_gui_yes_no 
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


class PSI_Transition():
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
        self.PSI_transition_parameter=self.parameters["PSI Validation"]["Test Case"]
        
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
        pass
#         #Step 3: Initialize output data structure
#         # This will be used to store the results of the test
#         self.Output_data = {
#     "PSI_Transition": {"Test Case":{}}
# }

#         #Step 4: set voltage rail in loadslammer:
#         self.loadslammer.maximize()
#         self.loadslammer.change_rail(self.test_key)
        
#         #clear all previous measurement in scope and add maximum for while loop later
#         output_status("Clearing all previous measurements in scope")
#         sl(0.1)
#         self.scope.clear_all_measurements()
#         #set horizontal scale
#         output_status("Setting scope horizontal scale to 200us/div")
#         sl(0.1)
#         self.scope.set_horizontal_scale(0.0002)

#         #set scope vertical scale to 200mV/div
#         output_status("Setting scope vertical scale to 200mV/div")
#         sl(0.1)
#         self.scope.configure_vertical(channel=1, scale=0.2)
        
    
#         #iterate through the test case
#         for test_id, test_data in self.PSI_transition_parameter.items():
#             self.loadslammer.minimize()
#             self.SVI3.minimize()

#             #dict to store the results for  test case
#             self.Output_data["PSI_Transition"]["Test Case"]["{}".format(test_id)]={"measured data":None}
#             self.Output_data["PSI_Transition"]["Test Case"]["{}".format(test_id)]["measured data"]={"Rising_edge":{},"Falling_edge":{}}
#             #grab the value for the rising and falling edge test cases
#             rising_edge=test_data["rising_edge"]
#             falling_edge=test_data["falling_edge"]
            
#             if self.test_key == "VDDCR_CPU0" or self.test_key == "VDDCR_CPU1":
#                 if test_id =="1":
#                     output_status("Starting test case ID: {} rising edge", test_id)
#                     output_status("clear scope screen")
#                     self.scope.clear_screen()
#                     #run rising edge first
#                     #set scope offset following Old VID

#                     #set the test current
#                     self.loadslammer.maximize()
#                     output_status("Setting LoadSlammer current to {}A", rising_edge["IDD Set(A)"])
#                     self.loadslammer.stop()
#                     self.loadslammer.adjust_test_current(rising_edge["IDD Set(A)"])
#                     self.loadslammer.slam()
#                     self.loadslammer.minimize()

#                     output_status("Setting scope offset to {}V", rising_edge["Old_VID (mV)"]/1000)
#                     self.scope.offset(channel=1, offset=rising_edge["Old_VID (mV)"]/1000)
#                     sl(0.1)

#                     #set the old PSI and VID in SVI3
#                     self.SVI3.maximize()
#                     sl(0.1)
#                     output_status("Setting SVI3 Old VID to {}mV", rising_edge["Old_VID (mV)"])
#                     self.SVI3.key_in_value('VID','{}mV'.format(rising_edge["Old_VID (mV)"]))
#                     self.SVI3.click('Set_VID')
#                     sl(2)

#                     #set scope trigger 
#                     output_status("Setting scope trigger level to below {}V", rising_edge["Target_VID (mV)"]/1000)
#                     self.scope.set_trigger_level(rising_edge["Old_VID (mV)"]/1000, rising_edge["Target_VID (mV)"]/1000, slope="RISE")
#                     sl(0.1)

#                     output_status("Setting SVI3 Old PSI to {}", rising_edge["Old_PSI"])
#                     self.SVI3.key_in_value('PSI','{}'.format(rising_edge["Old_PSI"]))
#                     self.SVI3.click('Set_PSI')
#                     sl(1)

#                     output_status("Setting SVI3 Target VID to {}mV", rising_edge["Target_VID (mV)"])
#                     self.SVI3.key_in_value('VID','{}mV'.format(rising_edge["Target_VID (mV)"]))
#                     self.SVI3.click('Set_VID')
#                     # output_status("sleep for 10 seconds to wait for the voltage to settle")
#                     # sl(10)
#                     self.SVI3.minimize()
                    
#                     filepath=ir.filepath_creation(self.test_key,test_id,"Rising_edge")
#                     output_status(f"save rising edge  test:{test_id} screenshot to {filepath}")
#                     self.scope.take_screenshot(filepath)
#                     self.Output_data["PSI_Transition"]["Test Case"]["{}".format(test_id)]["measured data"]["Rising_edge"]["screenshot_path"]=filepath
#                     sl(1)

#                     #run falling edge next
#                     output_status("Starting falling edge test case for test ID: {}", test_id)
#                     output_status("clear scope screen")
#                     self.scope.clear_screen()
                    
#                     #set scope trigger 
#                     output_status("starting falling edge test case for test ID: {}", test_id)

#                     output_status("Setting scope trigger level to below {}V", rising_edge["Target_VID (mV)"]/1000)
#                     self.scope.set_trigger_level(rising_edge["Old_VID (mV)"]/1000, rising_edge["Target_VID (mV)"]/1000, slope="FALL")
#                     sl(0.1)

#                     self.SVI3.maximize()

#                     output_status("Setting SVI3 Old PSI to {}", falling_edge["Old_PSI"])
#                     self.SVI3.key_in_value('PSI','{}'.format(falling_edge["Old_PSI"]))
#                     self.SVI3.click('Set_PSI')
#                     sl(1)

#                     output_status("Setting SVI3 targt VID to {}mV", falling_edge["Target_VID (mV)"])
#                     self.SVI3.key_in_value('VID','{}mV'.format(falling_edge["Target_VID (mV)"]))
#                     self.SVI3.click('Set_VID')
#                     # output_status("sleep for 10 seconds to wait for the voltage to settle")
#                     # sl(10)
#                     self.SVI3.minimize()

                    
#                     filepath=ir.filepath_creation(self.test_key,test_id,"Falling_edge")
#                     output_status(f"save falling edge  test:{test_id} screenshot to {filepath}")
#                     self.scope.take_screenshot(filepath)
#                     self.Output_data["PSI_Transition"]["Test Case"]["{}".format(test_id)]["measured data"]["Falling_edge"]["screenshot_path"]=filepath
#                     sl(1)

#                 if test_id =="2":
#                     output_status("Starting test case ID: {} rising edge", test_id)
#                     output_status("clear scope screen")
#                     self.scope.clear_screen()
#                     #run rising edge first
#                     #set scope offset following Old VID

#                     output_status("Setting LoadSlammer current to {}A", rising_edge["IDD Set(A)"])
#                     self.loadslammer.maximize()
#                     self.loadslammer.stop()
#                     self.loadslammer.adjust_test_current(rising_edge["IDD Set(A)"])
#                     self.loadslammer.slam()
#                     self.loadslammer.minimize()


#                     output_status("Setting scope offset to {}V", rising_edge["Old_VID (mV)"]/1000)
#                     self.scope.offset(channel=1, offset=rising_edge["Old_VID (mV)"]/1000)
#                     sl(0.1)

#                     #set the old PSI and VID in SVI3
#                     self.SVI3.maximize()
#                     sl(0.1)

#                     output_status("Setting SVI3 Old VID to {}mV", rising_edge["Old_VID (mV)"])
#                     self.SVI3.key_in_value('VID','{}mV'.format(rising_edge["Old_VID (mV)"]))
#                     self.SVI3.click('Set_VID')
#                     sl(2)

#                     #set scope trigger 
#                     output_status("Setting scope trigger level to below {}V", rising_edge["Target_VID (mV)"]/1000)
#                     self.scope.set_trigger_level(rising_edge["Old_VID (mV)"]/1000, rising_edge["Target_VID (mV)"]/1000, slope="RISE")
#                     sl(0.1)

#                     output_status("Setting SVI3 Old PSI to {}", rising_edge["Old_PSI"])
#                     self.SVI3.key_in_value('PSI','{}'.format(rising_edge["Old_PSI"]))
#                     self.SVI3.click('Set_PSI')
#                     sl(1)

#                     output_status("Setting SVI3 Target VID to {}mV", rising_edge["Target_VID (mV)"])
#                     self.SVI3.key_in_value('VID','{}mV'.format(rising_edge["Target_VID (mV)"]))
#                     self.SVI3.click('Set_VID')
#                     # output_status("sleep for 10 seconds to wait for the voltage to settle")
#                     # sl(10)
#                     self.SVI3.minimize()
                    
#                     filepath=ir.filepath_creation(self.test_key,test_id,"Rising_edge")
#                     output_status(f"save rising edge  test:{test_id} screenshot to {filepath}")
#                     self.scope.take_screenshot(filepath)
#                     self.Output_data["PSI_Transition"]["Test Case"]["{}".format(test_id)]["measured data"]["Rising_edge"]["screenshot_path"]=filepath
#                     sl(1)

#                     #capture for the falling edge
#                     output_status("Starting falling edge test case for test ID: {}", test_id)
#                     output_status("clear scope screen")
#                     self.scope.clear_screen()
#                     #set scope trigger 
#                     output_status("Setting scope trigger level to below {}V", rising_edge["Target_VID (mV)"]/1000)
#                     self.scope.set_trigger_level(rising_edge["Old_VID (mV)"]/1000, rising_edge["Target_VID (mV)"]/1000, slope="FALL")
#                     sl(0.1)

#                     self.SVI3.maximize()
#                     output_status("Setting SVI3 Old PSI to {}", falling_edge["Old_PSI"])
#                     self.SVI3.key_in_value('PSI','{}'.format(falling_edge["Old_PSI"]))
#                     self.SVI3.click('Set_PSI')
#                     sl(1)

#                     output_status("Setting SVI3 targt VID to {}mV", falling_edge["Target_VID (mV)"])
#                     self.SVI3.key_in_value('VID','{}mV'.format(falling_edge["Old_VID (mV)"]))
#                     self.SVI3.click('Set_VID')
#                     # output_status("sleep for 10 seconds to wait for the voltage to settle")
#                     # sl(10)
#                     output_status("Setting SVI3 New PSI to {}", falling_edge["New_PSI"])
#                     self.SVI3.key_in_value('PSI','{}'.format(falling_edge["New_PSI"]))
#                     self.SVI3.click('Set_PSI')
#                     sl(1)


#                     output_status("Setting back the PSI to PSI: {}", rising_edge["New_PSI"])
#                     self.SVI3.key_in_value('PSI','{}'.format(rising_edge["New_PSI"]))
#                     self.SVI3.click('Set_PSI')
#                     sl(1)

#                     self.SVI3.minimize()

#                     filepath=ir.filepath_creation(self.test_key,test_id,"Falling_edge")
#                     output_status(f"save falling edge  test:{test_id} screenshot to {filepath}")
#                     self.scope.take_screenshot(filepath)
#                     self.Output_data["PSI_Transition"]["Test Case"]["{}".format(test_id)]["measured data"]["Falling_edge"]["screenshot_path"]=filepath
#                     sl(1)

#                 if test_id =="3":
#                     output_status("Starting test case ID: {} rising edge", test_id)
#                     output_status("clear scope screen")
#                     self.scope.clear_screen()

#                     output_status("Setting LoadSlammer current to {}A", rising_edge["IDD Set(A)"])
#                     self.loadslammer.maximize()
#                     self.loadslammer.stop()
#                     self.loadslammer.adjust_test_current(rising_edge["IDD Set(A)"])
#                     self.loadslammer.slam()
#                     self.loadslammer.minimize()
#                     #run rising edge first
#                     #set scope offset following Old VID
#                     output_status("Setting LoadSlammer current to {}A", rising_edge["IDD Set(A)"])
#                     self.scope.offset(channel=1, offset=rising_edge["Old_VID (mV)"]/1000)
#                     sl(0.1)

#                     #set the old PSI and VID in SVI3
#                     self.SVI3.maximize()
#                     sl(0.1)
#                     output_status("Setting SVI3 Old VID to {}mV", rising_edge["Old_VID (mV)"])
#                     self.SVI3.key_in_value('VID','{}mV'.format(rising_edge["Old_VID (mV)"]))
#                     self.SVI3.click('Set_VID')
#                     sl(2)

#                     #set scope trigger 
#                     output_status("Setting scope trigger level to below {}V", rising_edge["Target_VID (mV)"]/1000)
#                     self.scope.set_trigger_level(rising_edge["Old_VID (mV)"]/1000, rising_edge["Target_VID (mV)"]/1000, slope="RISE")
#                     sl(0.1)

#                     output_status("Setting SVI3 Old PSI to {}", rising_edge["Old_PSI"])
#                     self.SVI3.key_in_value('PSI','{}'.format(rising_edge["Old_PSI"]))
#                     self.SVI3.click('Set_PSI')
#                     sl(1)

#                     output_status("Setting SVI3 Target VID to {}mV", rising_edge["Target_VID (mV)"])
#                     self.SVI3.key_in_value('VID','{}mV'.format(rising_edge["Target_VID (mV)"]))
#                     self.SVI3.click('Set_VID')
#                     # output_status("sleep for 10 seconds to wait for the voltage to settle")
#                     # sl(10)
#                     self.SVI3.minimize()
                    
#                     filepath=ir.filepath_creation(self.test_key,test_id,"Rising_edge")
#                     output_status(f"save rising edge  test:{test_id} screenshot to {filepath}")
#                     self.scope.take_screenshot(filepath)
#                     self.Output_data["PSI_Transition"]["Test Case"]["{}".format(test_id)]["measured data"]["Rising_edge"]["screenshot_path"]=filepath
#                     sl(1)

#                     #capture for the falling edge
#                     output_status("Starting falling edge test case for test ID: {}", test_id)
#                     output_status("clear scope screen")
#                     self.scope.clear_screen()
#                     #set scope trigger 
#                     output_status("Setting scope trigger level to below {}V", rising_edge["Target_VID (mV)"]/1000)
#                     self.scope.set_trigger_level(rising_edge["Old_VID (mV)"]/1000, rising_edge["Target_VID (mV)"]/1000, slope="FALL")
#                     sl(0.1)

#                     output_status("Setting SVI3 Old PSI to {}", falling_edge["Old_PSI"])
#                     self.SVI3.maximize()
#                     self.SVI3.key_in_value('PSI','{}'.format(falling_edge["Old_PSI"]))
#                     self.SVI3.click('Set_PSI')
#                     sl(1)

#                     output_status("Setting SVI3 targt VID to {}mV", falling_edge["Target_VID (mV)"])
#                     self.SVI3.key_in_value('VID','{}mV'.format(falling_edge["Old_VID (mV)"]))
#                     self.SVI3.click('Set_VID')
#                     # output_status("sleep for 10 seconds to wait for the voltage to settle")
#                     # sl(10)
#                     output_status("Setting SVI3 New PSI to {}", falling_edge["New_PSI"])
#                     self.SVI3.key_in_value('PSI','{}'.format(falling_edge["New_PSI"]))
#                     self.SVI3.click('Set_PSI')
#                     sl(1)

#                     output_status("Setting back the PSI to PSI: {}", rising_edge["New_PSI"])
#                     self.SVI3.key_in_value('PSI','{}'.format(rising_edge["New_PSI"]))
#                     self.SVI3.click('Set_PSI')
#                     sl(1)

#                     self.SVI3.minimize()

#                     filepath=ir.filepath_creation(self.test_key,test_id,"Falling_edge")
#                     output_status(f"save falling edge  test:{test_id} screenshot to {filepath}")
#                     self.scope.take_screenshot(filepath)
#                     self.Output_data["PSI_Transition"]["Test Case"]["{}".format(test_id)]["measured data"]["Falling_edge"]["screenshot_path"]=filepath
#                     sl(1)

                    

#                 if test_id =="4":
#                     output_status("Starting test case ID: {} rising edge", test_id)
#                     output_status("clear scope screen")
#                     self.scope.clear_screen()
#                     #run rising edge first
#                     #set scope offset following falling edge VID because rising edge VID start at 1.2V.
#                     output_status("Setting LoadSlammer current to {}A", rising_edge["IDD Set(A)"])
#                     self.loadslammer.maximize()
#                     self.loadslammer.stop()
#                     self.loadslammer.adjust_test_current(rising_edge["IDD Set(A)"])
#                     self.loadslammer.slam()
#                     self.loadslammer.minimize()

#                     output_status("Setting scope offset to {}V", falling_edge["Target_VID (mV)"]/1000)
#                     self.scope.offset(channel=1, offset=falling_edge["Target_VID (mV)"]/1000)
#                     sl(0.1)

                    

#                     #set scope trigger 
#                     output_status("Setting scope trigger level to below {}V", falling_edge["Target_VID (mV)"]/1000)
#                     self.scope.set_trigger_level(falling_edge["Target_VID (mV)"]/1000, rising_edge["Target_VID (mV)"]/1000, slope="RISE")
#                     sl(0.1)

#                     #set the old PSI and VID in SVI3
#                     self.SVI3.maximize()
#                     sl(0.1)
                    
#                     output_status("settting Old PSI to {}", rising_edge["Old_PSI"])
#                     self.SVI3.key_in_value('PSI','{}'.format(rising_edge["Old_PSI"]))
#                     self.SVI3.click('Set_PSI')
#                     sl(1)

#                     output_status("settting New PSI to {}", rising_edge["New_PSI"])
#                     self.SVI3.key_in_value('PSI','{}'.format(rising_edge["New_PSI"]))
#                     self.SVI3.click('Set_PSI')
#                     sl(1)

#                     # output_status("Setting SVI3 Target VID to {}mV", rising_edge["Target_VID (mV)"])
#                     # self.SVI3.key_in_value('VID','{}mV'.format(rising_edge["Target_VID (mV)"]))
#                     # self.SVI3.click('Set_VID')
#                     # output_status("sleep for 10 seconds to wait for the voltage to settle")
#                     # sl(10)

#                     output_status("Setting back the PSI to PSI: {}", falling_edge["New_PSI"])
#                     self.SVI3.key_in_value('PSI','{}'.format(falling_edge["New_PSI"]))
#                     self.SVI3.click('Set_PSI')
#                     sl(1)

#                     self.SVI3.minimize()
                    
#                     filepath=ir.filepath_creation(self.test_key,test_id,"Rising_edge")
#                     output_status(f"save rising edge  test:{test_id} screenshot to {filepath}")
#                     self.scope.take_screenshot(filepath)
#                     self.Output_data["PSI_Transition"]["Test Case"]["{}".format(test_id)]["measured data"]["Rising_edge"]["screenshot_path"]=filepath
#                     sl(1)

                    

#                     #capture for the falling edge
#                     output_status("Starting falling edge test case for test ID: {}", test_id)
#                     output_status("clear scope screen")
#                     self.scope.clear_screen()
#                     #set scope trigger 
#                     output_status("Setting scope trigger level to {}V", rising_edge["Target_VID (mV)"]/1000)
#                     self.scope.set_trigger_level(rising_edge["Old_VID (mV)"]/1000, rising_edge["Target_VID (mV)"]/1000, slope="FALL")
#                     sl(0.1)

#                     self.SVI3.maximize()

#                     output_status("Setting SVI3 Old PSI to {}", falling_edge["Old_PSI"])
#                     self.SVI3.key_in_value('PSI','{}'.format(falling_edge["Old_PSI"]))
#                     self.SVI3.click('Set_PSI')
#                     sl(1)

#                     output_status("Setting SVI3 Old VID to {}mV", falling_edge["Old_VID (mV)"])
#                     self.SVI3.key_in_value('VID','{}mV'.format(falling_edge["Old_VID (mV)"]))
#                     self.SVI3.click('Set_VID')
                    
#                     output_status("Setting SVI3 New VID to {}mV", falling_edge["Target_VID (mV)"])
#                     self.SVI3.key_in_value('VID','{}mV'.format(falling_edge["Target_VID (mV)"]))
#                     self.SVI3.click('Set_VID')
                    
#                     self.SVI3.minimize()
                    
#                     filepath=ir.filepath_creation(self.test_key,test_id,"Falling_edge")
#                     output_status(f"save falling edge  test:{test_id} screenshot to {filepath}")
#                     self.scope.take_screenshot(filepath)
#                     self.Output_data["PSI_Transition"]["Test Case"]["{}".format(test_id)]["measured data"]["Falling_edge"]["screenshot_path"]=filepath
#                     sl(1)

#                     output_status("Releasing LoadSlammer current to 0A")
#                     self.loadslammer.maximize()
#                     self.loadslammer.stop()
#                     self.loadslammer.minimize()

#             elif self.test_key == "VDDCR_SOC" or self.test_key == "VDDIO":
#                 if test_id =="1":
#                     output_status("Starting test case ID: {} rising edge for rail {}", test_id, self.test_key)
#                     output_status("clear scope screen")
#                     self.scope.clear_screen()
#                     #run rising edge first
#                     #set scope offset following Old VID

#                     #set the test current
#                     self.loadslammer.maximize()
#                     output_status("Setting LoadSlammer current to {}A", rising_edge["IDD Set(A)"])
#                     self.loadslammer.stop()
#                     self.loadslammer.adjust_test_current(rising_edge["IDD Set(A)"])
#                     self.loadslammer.slam()
#                     self.loadslammer.minimize()

#                     output_status("Setting scope offset to {}V", rising_edge["Old_VID (mV)"]/1000)
#                     self.scope.offset(channel=1, offset=rising_edge["Old_VID (mV)"]/1000)
#                     sl(0.1)

#                     #set the old PSI and VID in SVI3
#                     self.SVI3.maximize()
#                     sl(0.1)
                    

#                     #set scope trigger 
#                     output_status("Setting scope trigger level to below {}V", rising_edge["Target_VID (mV)"]/1000)
#                     self.scope.set_trigger_level(rising_edge["Old_VID (mV)"]/1000, rising_edge["Target_VID (mV)"]/1000, slope="RISE")
#                     sl(0.1)

#                     output_status("Setting SVI3 Old PSI to {}", rising_edge["Old_PSI"])
#                     self.SVI3.key_in_value('PSI','{}'.format(rising_edge["Old_PSI"]))
#                     self.SVI3.click('Set_PSI')
#                     sl(1)

#                     output_status("Setting SVI3 Old VID to {}mV", rising_edge["Old_VID (mV)"])
#                     self.SVI3.key_in_value('VID','{}mV'.format(rising_edge["Old_VID (mV)"]))
#                     self.SVI3.click('Set_VID')
#                     sl(2)

#                     output_status("Setting SVI3 Target VID to {}mV", rising_edge["Target_VID (mV)"])
#                     self.SVI3.key_in_value('VID','{}mV'.format(rising_edge["Target_VID (mV)"]))
#                     self.SVI3.click('Set_VID')
#                     # output_status("sleep for 10 seconds to wait for the voltage to settle")
#                     # sl(10)
#                     self.SVI3.minimize()
                    
#                     filepath=ir.filepath_creation(self.test_key,test_id,"Rising_edge")
#                     output_status(f"save rising edge  test:{test_id} screenshot to {filepath}")
#                     self.scope.take_screenshot(filepath)
#                     self.Output_data["PSI_Transition"]["Test Case"]["{}".format(test_id)]["measured data"]["Rising_edge"]["screenshot_path"]=filepath
#                     sl(1)

#                     #run falling edge next
#                     output_status("Starting falling edge test case for test ID: {}", test_id)
#                     output_status("clear scope screen")
#                     self.scope.clear_screen()
                    
#                     #set scope trigger 
#                     output_status("starting falling edge test case for test ID: {}", test_id)

#                     output_status("Setting scope trigger level to below {}V", rising_edge["Target_VID (mV)"]/1000)
#                     self.scope.set_trigger_level(rising_edge["Old_VID (mV)"]/1000, rising_edge["Target_VID (mV)"]/1000, slope="FALL")
#                     sl(0.1)

#                     self.SVI3.maximize()

#                     output_status("Setting SVI3 Old PSI to {}", falling_edge["Old_PSI"])
#                     self.SVI3.key_in_value('PSI','{}'.format(falling_edge["Old_PSI"]))
#                     self.SVI3.click('Set_PSI')
#                     sl(1)

#                     output_status("Setting SVI3 targt VID to {}mV", falling_edge["Target_VID (mV)"])
#                     self.SVI3.key_in_value('VID','{}mV'.format(falling_edge["Target_VID (mV)"]))
#                     self.SVI3.click('Set_VID')
#                     # output_status("sleep for 10 seconds to wait for the voltage to settle")
#                     # sl(10)
#                     self.SVI3.minimize()

                    
#                     filepath=ir.filepath_creation(self.test_key,test_id,"Falling_edge")
#                     output_status(f"save falling edge  test:{test_id} screenshot to {filepath}")
#                     self.scope.take_screenshot(filepath)
#                     self.Output_data["PSI_Transition"]["Test Case"]["{}".format(test_id)]["measured data"]["Falling_edge"]["screenshot_path"]=filepath
#                     sl(1)

#                 if test_id =="2":
#                     output_status("Starting test case ID: {} rising edge", test_id)
#                     output_status("clear scope screen")
#                     self.scope.clear_screen()
#                     #run rising edge first
#                     #set scope offset following Old VID

#                     output_status("Setting LoadSlammer current to {}A", rising_edge["IDD Set(A)"])
#                     self.loadslammer.maximize()
#                     self.loadslammer.stop()
#                     self.loadslammer.adjust_test_current(rising_edge["IDD Set(A)"])
#                     self.loadslammer.slam()
#                     self.loadslammer.minimize()


#                     output_status("Setting scope offset to {}V", rising_edge["Old_VID (mV)"]/1000)
#                     self.scope.offset(channel=1, offset=rising_edge["Old_VID (mV)"]/1000)
#                     sl(0.1)

#                     #set the old PSI and VID in SVI3
#                     self.SVI3.maximize()
#                     sl(0.1)

                    

#                     #set scope trigger 
#                     output_status("Setting scope trigger level to below {}V", rising_edge["Target_VID (mV)"]/1000)
#                     self.scope.set_trigger_level(rising_edge["Old_VID (mV)"]/1000, rising_edge["Target_VID (mV)"]/1000, slope="RISE")
#                     sl(0.1)



#                     output_status("Setting SVI3 Old PSI to {}", rising_edge["Old_PSI"])
#                     self.SVI3.key_in_value('PSI','{}'.format(rising_edge["Old_PSI"]))
#                     self.SVI3.click('Set_PSI')
#                     sl(1)

#                     output_status("Setting SVI3 Old VID to {}mV", rising_edge["Old_VID (mV)"])
#                     self.SVI3.key_in_value('VID','{}mV'.format(rising_edge["Old_VID (mV)"]))
#                     self.SVI3.click('Set_VID')
#                     sl(2)

#                     output_status("Setting SVI3 Target VID to {}mV", rising_edge["Target_VID (mV)"])
#                     self.SVI3.key_in_value('VID','{}mV'.format(rising_edge["Target_VID (mV)"]))
#                     self.SVI3.click('Set_VID')
#                     # output_status("sleep for 10 seconds to wait for the voltage to settle")
#                     # sl(10)
#                     self.SVI3.minimize()
                    
#                     filepath=ir.filepath_creation(self.test_key,test_id,"Rising_edge")
#                     output_status(f"save rising edge  test:{test_id} screenshot to {filepath}")
#                     self.scope.take_screenshot(filepath)
#                     self.Output_data["PSI_Transition"]["Test Case"]["{}".format(test_id)]["measured data"]["Rising_edge"]["screenshot_path"]=filepath
#                     sl(1)

#                     #capture for the falling edge
#                     output_status("Starting falling edge test case for test ID: {}", test_id)
#                     output_status("clear scope screen")
#                     self.scope.clear_screen()
#                     #set scope trigger 
#                     output_status("Setting scope trigger level to below {}V", rising_edge["Target_VID (mV)"]/1000)
#                     self.scope.set_trigger_level(rising_edge["Old_VID (mV)"]/1000, rising_edge["Target_VID (mV)"]/1000, slope="FALL")
#                     sl(0.1)

#                     self.SVI3.maximize()
#                     output_status("Setting SVI3 Old PSI to {}", falling_edge["Old_PSI"])
#                     self.SVI3.key_in_value('PSI','{}'.format(falling_edge["Old_PSI"]))
#                     self.SVI3.click('Set_PSI')
#                     sl(1)

#                     output_status("Setting SVI3 targt VID to {}mV", falling_edge["Target_VID (mV)"])
#                     self.SVI3.key_in_value('VID','{}mV'.format(falling_edge["Target_VID (mV)"]))
#                     self.SVI3.click('Set_VID')
#                     # output_status("sleep for 10 seconds to wait for the voltage to settle")
#                     # sl(10)
#                     output_status("Setting SVI3 New PSI to {}", falling_edge["New_PSI"])
#                     self.SVI3.key_in_value('PSI','{}'.format(falling_edge["New_PSI"]))
#                     self.SVI3.click('Set_PSI')
#                     sl(1)


#                     output_status("Setting back the PSI to PSI: {}", rising_edge["New_PSI"])
#                     self.SVI3.key_in_value('PSI','{}'.format(rising_edge["New_PSI"]))
#                     self.SVI3.click('Set_PSI')
#                     sl(1)

#                     self.SVI3.minimize()

#                     filepath=ir.filepath_creation(self.test_key,test_id,"Falling_edge")
#                     output_status(f"save falling edge  test:{test_id} screenshot to {filepath}")
#                     self.scope.take_screenshot(filepath)
#                     self.Output_data["PSI_Transition"]["Test Case"]["{}".format(test_id)]["measured data"]["Falling_edge"]["screenshot_path"]=filepath
#                     sl(1)

#                     output_status("Releasing LoadSlammer current to 0A")
#                     self.loadslammer.maximize()
#                     self.loadslammer.stop()
#                     self.loadslammer.minimize()

#         output_dir  = "Result"
#         output_file = os.path.join(output_dir, "Output_data.json")

#         # 2. Create the directory if it doesn't exist
#         if not os.path.isdir(output_dir):
#             os.makedirs(output_dir)

#         # 3. Dump (and overwrite) your JSON each run
#         with open(output_file, "w") as f:
#             json.dump(self.Output_data, f, indent=4)

#         output_status(f"Results written to {output_file}")
#         sl(1)            
    
    def clean_up(self):
        with open('C:\\Users\\HPS Penang Tester\\Documents\\python\\Load_slammer\\Result\\Output_data.json', 'r') as file:
            data = json.load(file)

        result_coordinate=self.excel_result_coordinate[self.test_key]["PSI Validation"]
        PSI_transition_data = data.get("PSI_Transition", {}).get("Test Case", {})
        
        
        #caibration data
        
        for test_case, measured_data in PSI_transition_data.items():
            for edge, values in measured_data.items():
                rising_edge = values.get("Rising_edge", {}).get("screenshot_path", "")
                falling_edge= values.get("Falling_edge", {}).get("screenshot_path", "")
                if rising_edge and falling_edge is not None:
                    # Convert column letter to number (A=1, B=2, etc.)
                    rising_edge_col_letter = result_coordinate["Test Case"]["{}".format(test_case)]["rising_edge"]["col_start"]
                    rising_col_number = ord(rising_edge_col_letter) - ord('A') + 1
                    
                    
        #votf data

        
        ir.insert_votf_images(self.worksheet, PSI_transition_data, result_coordinate)
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
        output_status("Test Completed.Result stored in {}".format(output_path))
                    
        

    
    def describe(test_key):
        # This function describes the test parameters and equipment needed for the VOTF test.
        # It returns a dictionary with the necessary information.
        if test_key == "VDDCR_CPU0" or test_key == "VDDCR_SOC":
            parameter_json = "PSI_CPU0_SOC_test_parameter.json"
            excel_result_coordinate= "PSI_CPU0_SOC_excel_result_coordinate.json"
        elif test_key == "VDDCR_CPU1" or test_key == "VDDIO":
            parameter_json = "PSI_CPU1_VDDIO_test_parameter.json"
            excel_result_coordinate= "PSI_CPU1_VDDIO_excel_coordinate.json"
        
        #SVI3 software coordinate file
        SVI3_coordinate="SVI3_coordinate.json"

        #This function will return the main excel sheet for the test
        mainsheet_path=ir.select_file(test_key)
        
        # Extract parameters, and excel 
        extraction=emc.JSON_excel_extractor(parameter_json,mainsheet_path,"PSI_Transition")
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
    LS_test_framework.execute("VDDCR_SOC", PSI_Transition )
    

    