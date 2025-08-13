
import platform
from console_app import (
    error_out_if,
    output_measurement,
    output_named_measurement,
    output_status,
    prompt,
)
import json
import LS_main_control_window
import SVI3_main_control_window
import VISA_MSO46B
import dialog_box_main_control_window
import general_function 
#import dialog_box_main_control_window_no_scope

def initialize(
    test_key,
    requested_equipment={},
    requested_parameters={},
    SVI3_coordinate=None,
    excel_result_coordinate=None,
    workbook= None,
    worksheet=None,
    include_files=[],
    about="",
):
    if platform.architecture()[0] != "64bit":
        prompt(
            "Warning: Detected this is {} python which may not work. ".format(
                platform.architecture()[0]
            )
            + "Recommend using the 64 bit version available from python.org. "
            + "If multiple versions are installed, ensure the Python path "
            + "property is appropriately set in the VR Test Runner "
            + "configuration.",
        )
    if not platform.python_version().startswith("3."):
        prompt(
            "Warning: Detected this is version {} python which may not work."
            + "Recommend using the 3.6+ bit version available from "
            + "python.org. "
            + "If multiple versions are installed, ensure the Python path "
            + "property is appropriately set in the VR Test Runner "
            + "configuration.",
            platform.python_version(),
        )

    driver_factory = load_ivi_components()
    
    excel_path=include_files if include_files else None
    raw_file_name=general_function.extract_sp5_name(excel_path) if excel_path else None
    parameters = {}
    parameters["raw_file_name"] = raw_file_name
    with open(SVI3_coordinate, 'r') as f:
        SVI3_location = json.load(f)
    with open(excel_result_coordinate, 'r') as f:
        excel_result_data = json.load(f)
    #all_test_definitions = json.load(f)
    parameters.update(requested_parameters[test_key])

    #hardware= LoadSlammerController(backend="uia", timeout=20)
    
    return  load_default_equipment(test_key),parameters,workbook,worksheet,SVI3_location,excel_result_data,test_key


def load_ivi_components():
    pass

def load_default_equipment(test_key):
    equipment = {}
    # Running stand alone
    try:
        equipment["LoadSlammer"] = LS_main_control_window.LoadSlammerController()
        equipment["SVI3"]=SVI3_main_control_window.SVI3Controller()
        mgr = VISA_MSO46B.InstrumentManager()
        inst = mgr.discover()               # inst is a pyvisa resource with .write()/.query()
        if inst is None:
            raise RuntimeError("No MSO46B found on any VISA resource")
        equipment["MSO46B"] = VISA_MSO46B.TektronixMSO46B(inst)       # ← now you’re passing the real instrument
        
        #will use this function later
        equipment["GUI"] = dialog_box_main_control_window.ScopePromptUI(equipment["SVI3"],equipment["MSO46B"],test_key)
        #equipment["GUI"] = dialog_box_main_control_window_no_scope.ScopePromptUI(equipment["SVI3"],test_key)



    except Exception as e:
        prompt(
            "Failed to initialized LoadSlammer and SVI3 Apps ",
            is_error=True,
        )

    return equipment

def execute(test_key, test_definition):
    output_status("Initializing...")


    # Initialize the test environment
    equipment,parameters,workbook,worksheet,SVI3_coordinate,excel_result_coordinate,test_key = initialize(
        test_key, **test_definition.describe(test_key)
    )

    required_methods = ["setup", "run", "clean_up", "describe"]
    #inspect.isabstract(test_definition)
    error_out_if(
        not all([p in dir(test_definition) for p in required_methods]),
        "Test definition does not include required methods: {}".format(
            str(required_methods)
        ),
    )

    test_run = test_definition()
    try:
        output_status("Setting Up...")
        test_run.setup(equipment, parameters,workbook,worksheet,SVI3_coordinate,excel_result_coordinate,test_key)
        output_status("Executing Test...")

        if "VRTT" in equipment:
            output_measurement({"VRTT Model": equipment["VRTT"]})
        test_run.run()
    finally:
        output_status("Cleaning Up...")
        test_run.clean_up()


if __name__ == "__main__":
    print(
        "This file is not intended to be run directly. "
        + "Did you mean to run a specific test?"
    )