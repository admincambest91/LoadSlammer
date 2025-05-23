import LS_test_framework
import sys
import datetime
from Test import Test
from time import sleep as sl

parameter="C:\\Users\\HPS Penang Tester\\Documents\\python\\Load_slammer\\parameter.json"

class TestDcRegulation():
    def setup(self, equipment, parameters):
        self.parameters = parameters
        self.equipment=equipment["LoadSlammer"]
        sl(1)

        #setting up test parameter
        static_current=self.parameters["parameters"]["static_current_amps"]#A
        voltage_range=self.parameters["parameters"]["voltage_range_volts"] #V
        load_duration=self.parameters["parameters"]["load_duration_seconds"] #s
        

        try:
        # Step 1: Connect to the application
            if not self.equipment.connect_to_app(start_if_not_running=True):
                print("Failed to connect to LoadSlammer. Exiting.")

            #save current control identifier
            self.equipment.print_all_control_identifiers() 
            sl(1)
            
            #add device to LoadSlammer 
            self.equipment.click_add_device_button()
            sl(1)
            self.equipment.click_connect_button()
            sl(1)
        except Exception as e:
                print(f"\nAn unhandled error occurred during automation: {e}")
    def run(self):
        pass
    
    def clean_up(self):
        #sys.exit(1) # Exit if connection fails
        pass

    
    def describe():
        return {
            "requested_equipment": "LoadSlammer",
            "requested_parameters": parameter,
            "include_files": None,
            "about": "This test will apply a static current load to the test "
            + "target and measure various parameters.  The test will "
            + "iterate over multiple currents and VIDs to later analyze "
            + "between one another.",
        }

if __name__ == "__main__":
    LS_test_framework.execute("DC_load", TestDcRegulation)
    

    