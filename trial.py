
from time import sleep
from pywinauto import Application
from pywinauto.findwindows import ElementNotFoundError
import pywinauto
import json
import sys
import io
import json
import re


file_name = "C:\\Users\\HPS Penang Tester\\Documents\\python\\control_identifier.txt"


#main       
try:
    current_parent_for_debug=None
    # 1. Connect to the LoadSlammer application
    # Use backend="uia" for more modern applications
    ##code below open the software directly from cold start
    #app=Application(backend='uia').start(r"C:\Program Files (x86)\LoadSlammer\LoadSlammer.exe").connect(title="LoadSlammer", timeout=15)
    
    #code below connect to LoadSlammer app that already open. use this to reduce overhead time
    app = Application(backend="uia").connect(title="LoadSlammer", timeout=15)
    print("Successfully connected to LoadSlammer application.")
    
    
    #magic lookup
    #dlg_spec=app.LoadSlammer
    #easiest way to go to the top window
    dlg=app.top_window()
    sleep(1)
    dlg.maximize()
    sleep(1)
    #dlg.print_control_identifiers(filename=file_name)
    sleep(1)
    add_device=dlg.child_window(title="addToolStripButton",control_type="Button").wrapper_object()
    sleep(1)
    dlg.maximize()
    add_device.click_input()
    sleep(1)
    #dlg.print_control_identifiers(filename=file_name)
    #identifier=save_identifier(dlg.print_control_identifiers())
    #select_device_dialog = app.window(title="Select Device").wrapper_object()
    #also can use below method,magic. .window connect to the top parent
    sleep(1)
    connect=dlg.child_window(title="Connect",auto_id="bConnect",control_type="Button").wrapper_object()
    sleep(1)
    connect.click_input()
    sleep(1)
    #dlg_spec=app.window(title="LoadSlammer")


    

except ElementNotFoundError as e:
    print(f"Error: Could not find an element in the hierarchy. Details: {e}")
    # You can add more specific print statements here to identify which step failed
    # e.g., print(f"Failed at: {e.original_exception.control_id} or {e.original_exception.class_name}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")



# LS_test_framework.py
# This file contains the core test execution framework.

import sys
import json
import inspect # For checking abstract classes
import os # For file path handling
from Test import Test # Import the Test ABC

# --- Utility Functions (from your original code) ---
def output_err(message):
    sys.stderr.write(f"ERROR: {message}\n") # Use sys.stderr.write for more control
    sys.stderr.flush()
    sys.exit(1) # Exit the script on error

def error_out(message):
    output_err(message)

def error_out_if(condition, message):
    if condition:
        error_out(message)

def load_default_parameters_from_json(json_file_path):
    """
    Loads test parameters from a JSON file and extracts their default values.
    """
    all_test_configs = {}
    try:
        if not os.path.exists(json_file_path):
            error_out(f"JSON parameter file not found at '{json_file_path}'")
            return {} # This return might not be reached due to error_out

        with open(json_file_path, 'r', encoding='utf-8') as f:
            all_test_configs = json.load(f)

    except json.JSONDecodeError as e:
        error_out(f"Error decoding JSON from '{json_file_path}': {e}")
        return {}
    except Exception as e:
        error_out(f"An unexpected error occurred while reading '{json_file_path}': {e}")
        return {}

    default_parameters = {}
    for test_name, test_details in all_test_configs.items():
        if "parameters" in test_details and isinstance(test_details["parameters"], dict):
            for param_name, param_attributes in test_details["parameters"].items():
                if "Default" in param_attributes:
                    default_parameters[param_name] = param_attributes["Default"]
                else:
                    print(f"Warning: Parameter '{param_name}' in test '{test_name}' has no 'Default' value.")
    return default_parameters

# --- Core Framework Execution Logic ---
def execute(test_key, test_definition_class):
    """
    Executes a given test definition.
    Args:
        test_key (str): The identifier for the test.
        test_definition_class (class): The test class (e.g., TestDcRegulation) to execute.
    """
    print(f"LS_test_framework: Starting execution for test key '{test_key}'")

    # --- Step 1: Validate the Test Definition Class ---
    # This is the robust check for abstract methods
    error_out_if(
        inspect.isabstract(test_definition_class),
        f"Test definition class '{test_definition_class.__name__}' is abstract. "
        f"It must implement all required abstract methods. Missing: {test_definition_class.__abstractmethods__}"
    )

    # --- Step 2: Get Test Metadata and Parameters ---
    try:
        # Call the class method 'describe' to get test metadata
        test_metadata = test_definition_class.describe()
        print(f"LS_test_framework: Test metadata loaded: {test_metadata.get('test_name', 'N/A')}")
    except AttributeError as e:
        # This can happen if 'describe' wasn't correctly implemented as a classmethod
        error_out(f"Test definition '{test_definition_class.__name__}' is missing or has an invalid 'describe' class method: {e}")
    except Exception as e:
        error_out(f"Error describing test '{test_definition_class.__name__}': {e}")

    # Load parameters from the specified file in the metadata
    requested_parameters_file = test_metadata.get("requested_parameters_file")
    if not requested_parameters_file:
        error_out("Test metadata 'requested_parameters_file' is missing for test: "
                  f"'{test_metadata.get('test_name', test_key)}'")

    test_parameters = load_default_parameters_from_json(requested_parameters_file)
    if not test_parameters:
        error_out(f"Failed to load default parameters from {requested_parameters_file}")
    print(f"LS_test_framework: Loaded default parameters: {test_parameters}")


    # --- Step 3: Initialize Equipment (Simulated) ---
    from main_control_window import LoadSlammerController # Import your controller
    equipment = {}
    try:
        load_slammer_controller = LoadSlammerController()
        if not load_slammer_controller.connect_to_app(start_if_not_running=True):
            error_out("Failed to connect to LoadSlammer application.")
        equipment["LoadSlammer"] = load_slammer_controller
        print("LS_test_framework: Equipment 'LoadSlammer' initialized.")
    except Exception as e:
        error_out(f"Failed to initialize LoadSlammer controller: {e}")

    # --- Step 4: Instantiate Test and Run Lifecycle ---
    test_instance = None # Initialize to None for finally block
    try:
        test_instance = test_definition_class() # Instantiate the concrete test class
        print(f"LS_test_framework: Instantiated test '{test_definition_class.__name__}'")

        test_instance.setup(equipment, test_parameters)
        print(f"LS_test_framework: Calling run for '{test_definition_class.__name__}'")
        test_instance.run()
        print(f"LS_test_framework: '{test_definition_class.__name__}' run completed.")

    except Exception as e:
        # Catch any errors during setup or run
        error_out(f"Error during test execution for '{test_definition_class.__name__}': {e}")
    finally:
        # --- Step 5: Clean Up (Guaranteed to run) ---
        if test_instance:
            try:
                print(f"LS_test_framework: Calling clean_up for '{test_definition_class.__name__}'")
                test_instance.clean_up()
                print(f"LS_test_framework: '{test_definition_class.__name__}' clean_up completed.")
            except Exception as e:
                output_err(f"Error during clean_up for '{test_definition_class.__name__}': {e}") # Don't exit, just report cleanup error
        if "LoadSlammer" in equipment and equipment["LoadSlammer"]:
            equipment["LoadSlammer"].close_app()
            print("LS_test_framework: LoadSlammer app closed.")

    print(f"LS_test_framework: Finished execution for test key '{test_key}'")

# This `if __name__ == "__main__":` block is for running the framework itself.
if __name__ == "__main__":
    print("Running LS_test_framework.py in standalone mode.")

    # --- Simulate parameter.json for testing ---
    # Create a dummy parameter.json file
    param_dir = "C:\\Users\\HPS Penang Tester\\Documents\\python\\Load_slammer"
    param_file = os.path.join(param_dir, "parameter.json")
    os.makedirs(param_dir, exist_ok=True)
    dummy_json_content = {
      "DC_load": {
        "description": "Tests the DC load characteristics of the device.",
        "parameters": {
          "Static Current Points": {
            "Description": "List of static current values (in Amps) to test.",
            "Units": "A",
            "Default": [0.0, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0],
            "Group": "DC Load Parameters",
            "ParameterType": "LIST_FLOAT"
          },
          "Test Voltage": {
            "Description": "The nominal voltage (in Volts) at which to apply the load.",
            "Units": "V",
            "Default": 1.0,
            "Group": "DC Load Parameters",
            "ParameterType": "FLOAT"
          }
        }
      }
    }
    with open(param_file, 'w', encoding='utf-8') as f:
        json.dump(dummy_json_content, f, indent=2)
    print(f"Dummy parameter.json created at: {param_file}")


    # Import your test definition
    from LS_Test_DC_Load import TestDcRegulation

    # --- Test Case 1: All methods implemented (should pass) ---
    print("\n--- TEST CASE 1: All methods implemented (should pass) ---")
    try:
        execute("DC_load_test", TestDcRegulation)
    except SystemExit: # Catch the sys.exit(1) from error_out
        print("Test Case 1 failed (expected to pass).")
    except Exception as e:
        print(f"Test Case 1 failed with unexpected error: {e}")


    # --- Test Case 2: clean_up is missing (should trigger error_out_if) ---
    print("\n--- TEST CASE 2: 'clean_up' method missing (should trigger error_out_if) ---")
    # Dynamically "remove" clean_up for this test case demonstration
    original_clean_up = None
    if hasattr(TestDcRegulation, 'clean_up'):
        original_clean_up = TestDcRegulation.clean_up
        delattr(TestDcRegulation, 'clean_up') # Remove it from the class for this test

    try:
        execute("DC_load_test_missing_cleanup", TestDcRegulation)
    except SystemExit:
        print("Test Case 2 failed as expected (missing clean_up).")
    except Exception as e:
        print(f"Test Case 2 failed with unexpected error: {e}")
    finally:
        # Restore clean_up for any subsequent tests or proper cleanup
        if original_clean_up:
            TestDcRegulation.clean_up = original_clean_up


    # --- Clean up dummy file ---
    # os.remove(param_file)
    # print(f"Cleaned up dummy file: {param_file}")





