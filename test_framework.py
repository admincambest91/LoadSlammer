

""" Common scafolding for writing tests
"""
import sys
import winreg

with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, R"SOFTWARE\Intel\UPDT") as key:
    (reg_val, reg_type) = winreg.QueryValueEx(key, "InstallPath")
    sys.path.append(reg_val)

import argparse
import json
import platform
from os import listdir
from os.path import isfile, join

import clr
import pyvisa as visa

import eqpt_chroma
import eqpt_scope
from console_app import (
    error_out_if,
    output_measurement,
    output_named_measurement,
    output_status,
    prompt,
)
from ranges import *
from test_framework_enums import HardwareType, ParameterType

clr.AddReference("Common")
from Common.APIs import DataAPI

data_api = DataAPI()


if __name__ == "__main__":
    print(
        "This file is not intended to be run directly. "
        + "Did you mean to run a specific test?"
    )


class EnumEncoder(json.JSONEncoder):
    def default(self, obj):
        if type(obj) in [HardwareType, ParameterType]:
            return str(obj.name)
        return json.JSONEncoder.default(self, obj)


def initialize(
    test_key,
    requested_equipment={},
    requested_parameters={},
    include_files=[],
    about="",
):
    arg_parser = argparse.ArgumentParser(
        description="This is a VR Reporting Application"
    )
    arg_parser.add_argument("--info", action="store_true")
    arg_parser.add_argument("--detect", action="store_true")
    arg_parser.add_argument("--input", "-i", default="setup.json")
    arg_parser.add_argument("--quiet", "-q", action="store_true")
    args = arg_parser.parse_args()

    if args.info:
        info = {
            "type": "test",
            "test_key": test_key,
            "hardware": requested_equipment,
            "parameters": requested_parameters,
            "include_files": include_files,
            "about": about,
        }
        print("@info " + json.dumps(info, cls=EnumEncoder))
    elif args.detect:
        print("Detected VISA Resources:")
        rm = visa.ResourceManager()
        print(rm.list_resources())
    else:
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

        # driver_factory = load_ivi_components()
        setup = load_setup(args.input)
        # hwcfg = []
        if setup:
            equipment = {"VRTT": "VRTT"}
            # for device in setup["Equipment"]:
            # if len(setup['Equipment'][device]) > 0:
            # hwcfg.append(setup['Equipment'][device])
            parameters = load_parameters(requested_parameters, setup["Parameters"])

            return (
                equipment,
                parameters,
            )  # hwcfg
        else:
            return load_default_equipment(), load_default_parameters(
                requested_parameters
            )
    exit()


def stand_alone_initialize(
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
    # NOOOOOO SETUP ARGHHH
    # setup = load_setup(args.input)
    default_parameters = {}
    for key, param in requested_parameters.items():
        default_parameters[key] = param["Default"]
    return  (), default_parameters


def load_ivi_components():
    pass


def load_parameters(requested_parameters, parameters_data):
    parameters = {}
    parameter_type_descriminator = "ParameterType"
    for param in requested_parameters:
        if "ParameterType" not in requested_parameters[param].keys():
            if "ParameterTypeString" in requested_parameters[param]:
                requested_parameters[param]["ParameterType"] = requested_parameters[
                    param
                ]["ParameterTypeString"]
    for param in requested_parameters:
        if param not in parameters_data:
            raise Exception("Requested parameter not provided by setup.json: " + param)
        parameters[param] = parameters_data[param]
        if (
            "ParameterType" not in requested_parameters[param]
            or requested_parameters[param]["ParameterType"] == ParameterType.STRING
        ):
            parameters[param] = (
                str(parameters[param]) if parameters[param] is not None else None
            )
        elif requested_parameters[param]["ParameterType"] == ParameterType.EVALUATE:
            try:
                parameters[param] = (
                    None if parameters[param] is None else eval(parameters[param])
                )

            except Exception:
                raise Exception(
                    'The "{}" parameter, whose value is '.format(param)
                    + "interpreted as a Python evaluated statement (Python "
                    + "code), was provided with the value of "
                    + '"{}" and Python failed to '.format(parameters[param])
                    + "evaluate this statement without error. Please recheck "
                    + "this value's syntax to be valid Python code and run "
                    + "the test again."
                )
        elif requested_parameters[param]["ParameterType"] == ParameterType.FLOAT:
            parameters[param] = round(float(parameters[param]), 5)
        elif requested_parameters[param]["ParameterType"] == ParameterType.INTEGER:
            parameters[param] = int(parameters[param])
        elif requested_parameters[param]["ParameterType"] == ParameterType.ENUM:
            error_out_if(
                parameters[param] not in requested_parameters[param]["Options"],
                "Parameter '{}': '{}' is not valid of choices {}".format(
                    param,
                    str(parameters[param]),
                    str(requested_parameters[param]["Options"]),
                ),
            )
        if "Minimum" in requested_parameters[param]:
            error_out_if(
                float(parameters[param])
                < float(requested_parameters[param]["Minimum"]),
                "Parameter '{}': {} is not within the minimum {}".format(
                    param, parameters[param], requested_parameters[param]["Minimum"]
                ),
            )
        if "Maximum" in requested_parameters[param]:
            error_out_if(
                float(parameters[param])
                < float(requested_parameters[param]["Maximum"]),
                "Parameter '{}': {} is not within the maximum {}".format(
                    param, parameters[param], requested_parameters[param]["Maximum"]
                ),
            )
    return parameters


def load_default_parameters(default_parameters):
    parameters = {}
    for param_name, value in default_parameters.items():
        parameters[param_name] = value["Default"]
    return parameters


def load_default_equipment():
    equipment = {}
    # Running stand alone
    try:
        equipment["VRTT"] = "VRTT"
    except Exception as e:
        prompt(
            "Failed to communicate with VRTT.  Is the VRTT "
            + "hardware powered on, connected, and is PDX running?",
            is_error=True,
        )

    return equipment


def load_equipment(driver_factory, equipment_data, reset: bool):
    equipment = {}
    if any(equipment_data):
        if "VRTT" in equipment_data:
            for tool_name in equipment_data["VRTT"]:
                try:
                    equipment[tool_name] = "VRTT"
                except Exception as e:
                    prompt(
                        "Failed to communicate with VRTT.  Is the VRTT "
                        + "hardware powered on, connected, and is PDX running?",
                        is_error=True,
                    )
                    exit()

        if HardwareType.CHROMA.name in equipment_data:
            for tool_name in equipment_data[HardwareType.CHROMA.name]:
                toolDetails = equipment_data[HardwareType.CHROMA.name][tool_name]
                myTool = eqpt_chroma.chroma(
                    toolDetails["IOResourceDescriptor"], toolDetails["Channel"]
                )
                equipment[tool_name] = myTool

    return equipment


def load_setup(filepath):
    setup = {}
    if filepath == "default":
        return
    else:
        try:
            with open(filepath, "r") as setupFile:
                setup = json.load(setupFile)
        except IOError:
            print("Warning: Input file cannot be read", file=sys.stderr)
    return setup


def execute(test_key, test_definition):
    output_status("Initializing...")

    equipment, parameters = initialize(test_key, **test_definition.describe())  # hwcfg

    required_methods = ["setup", "run", "clean_up", "describe"]
    error_out_if(
        not all([p in dir(test_definition) for p in required_methods]),
        "Test definition does not include required methods: {}".format(
            str(required_methods)
        ),
    )

    test_run = test_definition()
    try:
        output_status("Setting Up...")
        test_run.setup(equipment, parameters)  # , hwcfg)
        output_status("Executing Test...")

        data_api = DataAPI()
        output_measurement({"VRTT Model": "VRTT"})
        output_named_measurement({"VRTT Product ID": data_api.GetProductID()})
        output_named_measurement({"VRTT Vendor ID": data_api.GetVendorID()})
        output_named_measurement({"VRTT Platforms": data_api.GetPlatforms()})
        output_named_measurement({"VRTT Host Revision": data_api.GetHostRevision()})
        output_named_measurement({"VRTT Serial": data_api.GetSerialNumber()})
        output_named_measurement({"VRTT Firmware Rev": data_api.GetFirmwareRevision()})
        output_named_measurement({"VRTT IBID": data_api.GetIBID()})
        output_named_measurement({"VRTT FPGA Rev": data_api.GetFPGARevision()})
        output_named_measurement(
            {"VRTT Calibration Date": data_api.GetCalibrationDate()}
        )
        output_named_measurement({"VRTT HW Model": data_api.GetPhysicalHardwareId()})
        if "VRTT" in equipment:
            output_measurement({"VRTT Model": equipment["VRTT"]})
        test_run.run()
    except:
        test_run.setup(equipment, parameters)
        if "VRTT" in equipment:
            output_measurement({"VRTT Model": equipment["VRTT"]})
            output_status("entered expection...")
        test_run.run()

    finally:
        output_status("Cleaning Up...")
        test_run.clean_up()


def stand_alone_execute(test_key, test_definition):
    output_status("Initializing...")

    equipment, parameters = stand_alone_initialize(
        test_key, **test_definition.describe()
    )

    required_methods = ["setup", "run", "clean_up", "describe"]
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


def cool_down(parameters):
    pass
