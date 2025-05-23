# INTEL CONFIDENTIAL
#
# Copyright (C) 2022-2024 Intel Corporation
#
# This software and the related documents are Intel copyrighted materials, and your use
# of them is governed by the express license under which they were provided to you
# ("License"). Unless the License provides otherwise, you may not use, modify, copy,
# publish, distribute, disclose or transmit this software or the related documents
# without Intel's prior written permission.
#
# This software and the related documents are provided as is, with no express or implied
# warranties, other than those that are expressly stated in the License.

# import the master Test module
import test_framework
from console_app import (
    error_out,
    output_status,
    output_progress,
    prompt,
    output_axes,
    output_measurement,
    output_named_measurement,
    output_err,
)

import imon_helper
import sys
import time
import res_test_type_params
from test_framework_enums import ParameterType
from test_framework_enums import HardwareType
from Test import Test
import datetime

import clr

clr.AddReference("Common")
from Common.APIs import (
    GeneratorAPI,
    DisplayAPI,
    DataAPI,
    MeasurementAPI,
)
from Common.Enumerations import ScoplessChannel, HorizontalScale, Transition


class TestIMVPDcRegulation(Test):
    def setup(self, equipment, parameters):
        self.parameters = parameters
        # VRTT handles
        self.generator_api = GeneratorAPI()
        self.display_api = DisplayAPI()
        self.data_api = DataAPI()
        self.measurement_api = MeasurementAPI()
        # Use EPOD TODO
        # self.capture_efficiency = True #TODO detect EPODs
        # output_status("Utilizing EPOD for Efficiency Measurements!")
        #     except Exception:
        #         output_status(
        #             "There was no EPOD, Vshunt DMM, or Vin "
        #             + "DMM Detected. Efficiency measurements "
        #             + "will be skipped."
        #         )
        #         self.capture_efficiency = False

        self.display_api.SetHorizontalScale(HorizontalScale.Scale10us)
        self.platform_rails = {r.Name: r for r in list(self.generator_api.GetRails())}
        # Get the rail information fail if can't communicate with VRTT software
        self.test_rail = None
        for r in self.platform_rails:
            if r == self.parameters["Test Rail"]:
                self.test_rail = self.platform_rails[r]
        if self.test_rail is None:
            output_err(
                "Analysis failed because the test rail could not be found. Please check the rail name."
            )
        else:
            output_named_measurement({"vr_address": self.test_rail.VRAddress})
            output_named_measurement({"svid_bus": self.test_rail.SVIDBus})
        # ps_state to current list lookup dictionary
        iccmax = imon_helper.eval_iout_max(
            imon_helper.read_static_registers_vectors(
                output_status,
                self.parameters,
                self.test_rail.VRAddress,
                self.test_rail.SVIDBus,
            )
        )
        ps0_current_percents = [0, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        ps0_test_currents = [
            percent / 100 * parameters["PS0 TDC Current"]
            for percent in ps0_current_percents
        ]

        ps1_current_percents = [
            0,
            12.50,
            20,
            30,
            40,
            50,
            60,
            70,
            80,
            90,
            100,
        ]  # Percent of TDC to use for test and analysis points. If less than PS1 Max ICC. And test 2A always.
        ps1_test_currents = [
            percent / 100 * parameters["PS0 TDC Current"]
            for percent in ps1_current_percents
            if percent / 100 * parameters["PS0 TDC Current"]
            < parameters["PS1 Max Current"]
        ]
        ps1_test_currents.insert(0, 2)  # Add 2A to the current values
        self.ps_state_to_current_list = {
            0: ps0_test_currents,
            1: ps1_test_currents,
            2: [0, 1, 2, 3, 4, 5],
            3: [0, 0.5, 1, 1.5, 2],
        }
        # ps_state to voltage lookup dictionary
        self.ps_state_to_voltage = {
            0: self.parameters["VID 1"],
            1: self.parameters["VID 2"],
            2: self.parameters["VID 2"],
            3: self.parameters["VID 3"],
        }

    def run(self):
        # Enable Scope Traces
        self.display_api.Ch1_2Rail(self.parameters["Test Rail"])
        self.display_api.SetChannel(ScoplessChannel.Ch1, True)
        self.display_api.SetChannel(ScoplessChannel.Ch2, True)
        # Add Measurements
        self.measurement_api.MeasureCurrentMean(self.parameters["Test Rail"])
        self.measurement_api.MeasureVoltageMinMax(self.parameters["Test Rail"])
        self.measurement_api.MeasureVoltageMean(self.parameters["Test Rail"])

        # Set trigger to DAC1 to track the current levels before switching to vector burst trigger
        self.data_api.SetTrigger(4, 0, 0, 0, 0, False)

        # Assign the rail to tab 1 at 0A
        self.generator_api.Generator1SVSC(self.parameters["Test Rail"], 0, False)

        time.sleep(2)
        total_test_currents = 0
        for a in self.ps_state_to_current_list:
            total_test_currents = total_test_currents + len(
                self.ps_state_to_current_list[a]
            )
        test_current_progress = 0
        # Sweep through power states
        for ps_state in [0, 1, 2, 3]:
            # Result container for outputing named measurements at the end
            ps_results = {}

            # Read static registers
            ps_results["static_registers"] = imon_helper.read_static_registers_vectors(
                output_status,
                self.parameters,
                self.test_rail.VRAddress,
                self.test_rail.SVIDBus,
            )
            # Capture the test currents
            ps_results["test_currents"] = self.ps_state_to_current_list[ps_state]

            if ps_state == 0:
                # Capture the average voltage at 0 Amps
                for voltage_key in ["VID 1", "VID 2", "VID 3"]:
                    self.generator_api.SetVoltageForRail(
                        self.parameters["Test Rail"],
                        self.parameters[voltage_key],
                        Transition.Fast,
                    )
                    time.sleep(1)
                    # Set power state
                    self.generator_api.SetPS_SVSC(
                        self.parameters["Test Rail"], False, ps_state
                    )
                    time.sleep(2)
                    rail_voltage_current = self.data_api.GetVoltageCurrent(
                        self.parameters["Test Rail"]
                    )
                    if rail_voltage_current != None:
                        voltage_wave = list(rail_voltage_current.Voltage)
                        ps_results[
                            "{}_no_current_mean".format(voltage_key.replace(" ", "_"))
                        ] = sum(voltage_wave) / len(voltage_wave)
                    else:
                        ps_results[
                            "{}_no_current_mean".format(voltage_key.replace(" ", "_"))
                        ] = 0

            # Set voltage (use ps state to voltage lookup)
            self.generator_api.SetVoltageForRail(
                self.parameters["Test Rail"],
                self.ps_state_to_voltage[ps_state],
                Transition.Fast,
            )
            time.sleep(0.5)
            # Set power state
            self.generator_api.SetPS_SVSC(self.parameters["Test Rail"], False, ps_state)
            time.sleep(1)
            # Setup a results dict for the ps state

            # Sweep currents
            for idx, current in enumerate(self.ps_state_to_current_list[ps_state]):
                test_current_progress = test_current_progress + 1
                output_progress(test_current_progress / total_test_currents * 100)
                current_step_results = {}
                output_status(
                    "Testing PS{} at {:.3}V, {}A".format(
                        ps_state, self.ps_state_to_voltage[ps_state], current
                    )
                )
                if current > 0:
                    self.generator_api.Generator1SVSC(
                        self.parameters["Test Rail"], current, True
                    )
                    time.sleep(1)
                    self.generator_api.SetTrackingEnabled(
                        self.parameters["Test Rail"], True
                    )
                else:
                    self.generator_api.Generator1SVSC(
                        self.parameters["Test Rail"], current, False
                    )
                    self.generator_api.SetTrackingEnabled(
                        self.parameters["Test Rail"], False
                    )
                time.sleep(3)
                current_step_results["dynamic_registers"] = (
                    imon_helper.read_dynamic_registers_vectors(
                        self.parameters,
                        vr_address=self.test_rail.VRAddress,
                        svid_bus=self.test_rail.SVIDBus,
                    )
                )
                # Capture set values for voltage and current
                current_step_results["set_voltage"] = self.ps_state_to_voltage[ps_state]
                current_step_results["set_current"] = current
                output_status(
                    "IMON Reg: 0x{}".format(
                        current_step_results["dynamic_registers"]["[REG] IOUT_H 0x15"]
                    )
                )
                # Capture the average voltage and current
                rail_voltage_current = self.data_api.GetVoltageCurrent(
                    self.parameters["Test Rail"]
                )
                if rail_voltage_current != None:
                    voltage_wave = list(rail_voltage_current.Voltage)
                    current_wave = list(rail_voltage_current.Current)
                    current_step_results["measured_current"] = sum(current_wave) / len(
                        current_wave
                    )
                    current_step_results["measured_voltage"] = sum(voltage_wave) / len(
                        voltage_wave
                    )
                    current_step_results["measured_voltage_max"] = max(voltage_wave)
                    current_step_results["measured_voltage_min"] = min(voltage_wave)
                else:
                    current_step_results["measured_current"] = 0
                    current_step_results["measured_voltage"] = 0
                    current_step_results["measured_voltage_max"] = 0
                    current_step_results["measured_voltage_min"] = 0

                # Turn off load before switching to PS0
                self.generator_api.Generator1SVSC(
                    self.parameters["Test Rail"], current, False
                )
                time.sleep(0.5)
                self.generator_api.SetPS_SVSC(
                    self.parameters["Test Rail"], False, 0
                )  # Set power state 0
                time.sleep(0.5)
                self.generator_api.Generator1SVSC(
                    self.parameters["Test Rail"], current, True
                )  # Enable load
                # Enable Tracking
                self.generator_api.SetTrackingEnabled(
                    self.parameters["Test Rail"], True
                )
                time.sleep(3)  # Wait for the current to settle
                rail_voltage_current = self.data_api.GetVoltageCurrent(
                    self.parameters["Test Rail"]
                )
                if rail_voltage_current != None:
                    voltage_wave = list(rail_voltage_current.Voltage)
                    current_step_results["PS0_Voltage"] = sum(voltage_wave) / len(
                        voltage_wave
                    )
                else:
                    current_step_results["PS0_Voltage"] = 0

                ps_results[str(current)] = current_step_results
                self.generator_api.Generator1SVSC(
                    self.parameters["Test Rail"], current, False
                )
                # TODO output progress percent
                # i = i + 1
                # output_progress(
                #     round(
                #         100.0
                #         * i
                #         / (
                #             len(self.parameters["Test Currents"])
                #             * len(self.parameters["Test VID List"])
                #         )
                #     )
                # )
                # TODO get epod data
                # if self.capture_efficiency:
                #     if not self.vshunt or not self.vin:
                #         _, v_drop, v_in, _ = self.target_rail.EfficiencyPod(
                #             float(), float(), float()
                #         )
                #         current_step_results["Measured Iin"] = v_drop / 0.001
                #         current_step_results["Measured Vin"] = v_in

                #     if self.vshunt:
                #         measure_v_shunt = float(self.vshunt.Measurement.Read(1000))
                #         current_step_results["Measured Iin"] = measure_v_shunt / (
                #             self.parameters["Shunt Resistance"] / 1000
                #         )

                #     if self.vin:
                #         current_step_results["Measured Vin"] = float(self.vin.Measurement.Read(1000))
                #         # else handled with EPod above

                #     try:
                #         current_step_results["efficiency"] = (
                #             float(current_step_results["Measured Iout"]) * float(current_step_results["Measured Vout"])
                #         ) / (float(current_step_results["Measured Iin"]) * float(current_step_results["Measured Vin"]))
                #     except ZeroDivisionError:
                #         current_step_results["efficiency"] = 0

            post_run = {}
            # Count of received Svid parity error
            ps_results["post_run"] = imon_helper.read_static_registers_vectors(
                output_status,
                self.parameters,
                self.test_rail.VRAddress,
                self.test_rail.SVIDBus,
            )

            output_named_measurement({"PS{} Data".format(ps_state): ps_results})

        if current_step_results["measured_voltage"] < 0.1:
            prompt(
                "Warning: Rail Down - The target rail was measured at "
                + "{:.3f}V when the VID setpoint was {:.3f}V. ".format(
                    current_step_results["measured_voltage"],
                    self.ps_state_to_voltage[ps_state],
                )
                + "Please reset the rail and click to retry the test case. "
                + "Timestamp: {}".format(datetime.datetime.now(tz=time.timezone.utc))
            )

    def clean_up(self):
        self.generator_api.SetPS_SVSC(self.parameters["Test Rail"], False, 0)
        self.generator_api.Generator1SVSC(self.parameters["Test Rail"], 0, False)
        output_named_measurement({"test": "data"})

    def describe():
        equipment = {}
        res_test_type_params.add_equipment_vrtt(equipment)

        parameters = {
            # Test parameters
            "Test Rail": {
                "Description": "Rail Name for VRTT to test",
                "Group": "Test Parameters",
                "Default": "VCCCORE",
            },
            "PS0 TDC Current": {
                "Description": "Maximum current to test in PS0. All other test currents will be calculated automatically",
                "Units": "A",
                "Default": 50,
                "Group": "Combined PS DC Regulation",
                "ParameterType": ParameterType.FLOAT,
            },
            "PS1 Max Current": {
                "Description": "Maximum current to test in PS1. All other test currents will be calculated automatically",
                "Units": "A",
                "Default": 20,
                "Group": "Combined PS DC Regulation",
                "ParameterType": ParameterType.FLOAT,
            },
            "PS2 Max Current": {
                "Description": "Maximum current to test in PS2. All other test currents will be calculated automatically",
                "Units": "A",
                "Default": 5,
                "Group": "Combined PS DC Regulation",
                "ParameterType": ParameterType.FLOAT,
            },
            "PS3 Max Current": {
                "Description": "Maximum current to test in PS3. All other test currents will be calculated automatically",
                "Units": "A",
                "Default": 2,
                "Group": "Combined PS DC Regulation",
                "ParameterType": ParameterType.FLOAT,
            },
            "VID 1": {
                "Description": "VID 1 value from the platform test plan",
                "Units": "V",
                "Default": 0.9,
                "Group": "Combined PS DC Regulation",
                "ParameterType": ParameterType.FLOAT,
            },
            "VID 2": {
                "Description": "VID 2 value from the platform test plan",
                "Units": "V",
                "Default": 0.6,
                "Group": "Combined PS DC Regulation",
                "ParameterType": ParameterType.FLOAT,
            },
            "VID 3": {
                "Description": "VID 3 value from the platform test plan",
                "Units": "V",
                "Default": 0.3,
                "Group": "Combined PS DC Regulation",
                "ParameterType": ParameterType.FLOAT,
            },
            # Analysis parameters
            "R_DC_LL_Max_PS0": {
                "Description": "Maximum acceptable load line for PS0",
                "Units": "Ohms",
                "Default": 1.2,
                "Group": "IMVP Analysis",
                "ParameterType": ParameterType.FLOAT,
            },
            "R_DC_LL_Min_PS0": {
                "Description": "Minimum acceptable load line for PS0",
                "Units": "Ohms",
                "Default": 1.0,
                "Group": "IMVP Analysis",
                "ParameterType": ParameterType.FLOAT,
            },
            "R_DC_LL_Max_PS1": {
                "Description": "Maximum acceptable load line PS1",
                "Units": "Ohms",
                "Default": 1.85,
                "Group": "IMVP Analysis",
                "ParameterType": ParameterType.FLOAT,
            },
            "R_DC_LL_Min_PS1": {
                "Description": "Minimum acceptable load line for PS1",
                "Units": "Ohms",
                "Default": 0.35,
                "Group": "IMVP Analysis",
                "ParameterType": ParameterType.FLOAT,
            },
            "R_DC_LL_Max_PS2": {
                "Description": "Maximum acceptable load line for PS2",
                "Units": "Ohms",
                "Default": 4.1,
                "Group": "IMVP Analysis",
                "ParameterType": ParameterType.FLOAT,
            },
            "R_DC_LL_Min_PS2": {
                "Description": "Minimum acceptable load line for PS2",
                "Units": "Ohms",
                "Default": -1.9,
                "Group": "IMVP Analysis",
                "ParameterType": ParameterType.FLOAT,
            },
            "RDC_LL": {
                "Description": "Designed RDC Load Line",
                "Units": "Ohms",
                "Default": 1.1,
                "Group": "IMVP Analysis",
                "ParameterType": ParameterType.FLOAT,
            },
            "+ PS0 Ripple": {
                "Description": "Maximum ripple voltage positive or negative.",
                "Units": "mV",
                "Default": 10,
                "Group": "IMVP Analysis",
                "ParameterType": ParameterType.FLOAT,
            },
            "- PS0 Ripple": {
                "Description": "Maximum ripple voltage positive or negative.",
                "Units": "mV",
                "Default": 10,
                "Group": "IMVP Analysis",
                "ParameterType": ParameterType.FLOAT,
            },
            "+ PS1 Ripple": {
                "Description": "Maximum ripple voltage positive or negative.",
                "Units": "mV",
                "Default": 15,
                "Group": "IMVP Analysis",
                "ParameterType": ParameterType.FLOAT,
            },
            "- PS1 Ripple": {
                "Description": "Maximum ripple voltage positive or negative.",
                "Units": "mV",
                "Default": 15,
                "Group": "IMVP Analysis",
                "ParameterType": ParameterType.FLOAT,
            },
            "+ PS2 Ripple": {
                "Description": "Maximum positive ripple voltage.",
                "Units": "mV",
                "Default": 30,
                "Group": "IMVP Analysis",
                "ParameterType": ParameterType.FLOAT,
            },
            "- PS2 Ripple": {
                "Description": "Maximum negative ripple voltage.",
                "Units": "mV",
                "Default": 10,
                "Group": "IMVP Analysis",
                "ParameterType": ParameterType.FLOAT,
            },
            "+ PS3 Ripple": {
                "Description": "Maximum positive ripple voltage.",
                "Units": "mV",
                "Default": 30,
                "Group": "IMVP Analysis",
                "ParameterType": ParameterType.FLOAT,
            },
            "- PS3 Ripple": {
                "Description": "Maximum negative ripple voltage.",
                "Units": "mV",
                "Default": 10,
                "Group": "IMVP Analysis",
                "ParameterType": ParameterType.FLOAT,
            },
            "V_TOB_IMIN": {
                "Description": "Maximum voltage tolerance from set VID with no load",
                "Units": "mV",
                "Default": 5,
                "Group": "IMVP Analysis",
                "ParameterType": ParameterType.FLOAT,
            },
            "Phase Count": {
                "Description": "Number of VR Phases",
                "Default": 6,
                "Group": "IMVP Analysis",
                "ParameterType": ParameterType.INTEGER,
                "Minimum": 1,
            },
            "DCR Tolerance": {
                "Description": "DCR tolerance of output inductor and thermistor tolerance",
                "Default": 7,
                "Group": "IMVP Analysis",
                "Units": "%",
                "ParameterType": ParameterType.INTEGER,
                "Options": [7, 5],
            },
            "Efficiency Target": {
                "Description": "Target Efficiency",
                "Units": "%",
                "Default": 85.0,
                "Group": "IMVP Analysis",
                "ParameterType": ParameterType.FLOAT,
            },
            # Add when/if spec has MOSFET numbers
            # "IMON Topology": {
            #     "Description": "Target Platform Supported Topology",
            #     "Default": "MOSFET",
            #     "Group": "Analysis Parameters",
            #     "ParameterType": ParameterType.ENUM,
            #     "Options": ["MOSFET", "DCR"],
            # },
        }

        include_files = [
            "imon_helper.py",
            "eqpt_chroma.py",
            "eqpt_power_supply.py",
        ]

        return {
            "requested_equipment": equipment,
            "requested_parameters": parameters,
            "include_files": include_files,
            "about": "This test will apply a static current load to the test "
            + "target and measure various parameters.  The test will "
            + "iterate over multiple currents and VIDs to later analyze "
            + "between one another.",
        }


if __name__ == "__main__":
    if "--debug" in sys.argv:
        test_framework.stand_alone_execute("imvp_dc_reg", TestIMVPDcRegulation)
    else:
        test_framework.execute("imvp_dc_reg", TestIMVPDcRegulation)
