
import platform
from console_app import (
    error_out_if,
    output_measurement,
    output_named_measurement,
    output_status,
    prompt,
)
import json
import main_control_window
import inspect

def initialize(
    test_key,
    requested_equipment={},
    requested_parameters={},
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
    
    parameters = {}
    with open('parameter.json', 'r') as f:
        data_dict = json.load(f)
#     all_test_definitions = json.load(f)
    parameters=data_dict[test_key]
    #hardware= LoadSlammerController(backend="uia", timeout=20)
    
    return  load_default_equipment(),parameters


def load_ivi_components():
    pass

def load_default_equipment():
    equipment = {}
    # Running stand alone
    try:
        equipment["LoadSlammer"] = main_control_window.LoadSlammerController()
    except Exception as e:
        prompt(
            "Failed to initialized LoadSlammer Apps ",
            is_error=True,
        )

    return equipment

def execute(test_key, test_definition):
    output_status("Initializing...")

    equipment,parameters = initialize(
        test_key, **test_definition.describe()
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
        test_run.setup(equipment, parameters)
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