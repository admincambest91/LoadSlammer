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

import argparse
import datetime
import html
import json
import os
import sys
import uuid
import winreg
from itertools import chain

import data_tools

with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, R"SOFTWARE\Intel\UPDT") as key:
    (reg_val, reg_type) = winreg.QueryValueEx(key, "InstallPath")
    sys.path.append(reg_val)
from jinja2 import Environment, Template

from test_framework_enums import HardwareType, ParameterType


class EnumEncoder(json.JSONEncoder):
    def default(self, obj):
        if type(obj) in [HardwareType, ParameterType]:
            return str(obj.name)
        return json.JSONEncoder.default(self, obj)


def escapejs(val):
    # .replace('\r\n', '\\n').replace('\n', '\\n')
    return html.escape(str(val))


def add_properties(report, runs, input_file):
    tab = report.add_tab_right("Properties")

    if not isinstance(runs, list):
        runs = [runs]

    i = 1
    for capture in runs:
        Parameters_Dict = {
            param["Key"]: {
                "Value": (
                    param["Value"]
                    if not isinstance(param["Value"], type(float))
                    else "{:.6f}".format(param["Value"])
                ),
                "Units": param["RequestedParameter"]["Units"],
                "Description": param["RequestedParameter"]["Description"],
            }
            for param in capture["TargetProgramRun"]["Parameters"]
        }

        tab.add_text_block(
            "#{} - {}".format(i, capture["TargetProgramRun"]["Title"]),
            "",
        )
        i += 1

        table_properties = []
        table_properties.append(
            {
                "Property": "Report Generated",
                "Value": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        if "TimeStamp" in capture.keys():
            period_idx = capture["TimeStamp"].find(".")
            table_properties.append(
                {
                    "Property": "Data Captured",
                    "Value": capture["TimeStamp"][:period_idx],
                }
            )
        if "NamedMeasurements" in capture.keys():
            if "VRTT Calibration Date" in capture["NamedMeasurements"].keys():
                cap_date = capture["NamedMeasurements"]["VRTT Calibration Date"]
                cal_date = datetime.date.fromisoformat(
                    "-".join([cap_date[6:], cap_date[3:5], cap_date[0:2]])
                )
                table_properties.append(
                    {
                        "Property": "VRTT Calibration Date",
                        "Value": cal_date,
                    }
                )
            if "VRTT HW Model" in capture["NamedMeasurements"].keys():
                table_properties.append(
                    {
                        "Property": "VRTT HW Model",
                        "Value": capture["NamedMeasurements"]["VRTT HW Model"],
                    }
                )
            if "VRTT Platforms" in capture["NamedMeasurements"].keys():
                table_properties.append(
                    {
                        "Property": "VRTT Platforms",
                        "Value": capture["NamedMeasurements"]["VRTT Platforms"],
                    }
                )
            if "VRTT Serial" in capture["NamedMeasurements"].keys():
                table_properties.append(
                    {
                        "Property": "VRTT Serial",
                        "Value": capture["NamedMeasurements"]["VRTT Serial"],
                    }
                )
            if "VRTT IBID" in capture["NamedMeasurements"].keys():
                table_properties.append(
                    {
                        "Property": "VRTT Interposer ID",
                        "Value": capture["NamedMeasurements"]["VRTT IBID"],
                    }
                )
            if "VRTT Host Revision" in capture["NamedMeasurements"].keys():
                table_properties.append(
                    {
                        "Property": "VRTT Host Revision",
                        "Value": capture["NamedMeasurements"]["VRTT Host Revision"],
                    }
                )
            if "VRTT FPGA Rev" in capture["NamedMeasurements"].keys():
                table_properties.append(
                    {
                        "Property": "VRTT FPGA Rev",
                        "Value": capture["NamedMeasurements"]["VRTT FPGA Rev"],
                    }
                )
        tab.add_table(
            "General",
            table_properties,
            order=["Property", "Value"],
        )

        parameters = [
            {
                "Parameter": k,
                "Value": v["Value"],
                "Units": v["Units"],
                "Description": v["Description"],
            }
            for k, v in Parameters_Dict.items()
        ]
        tab.add_table(
            "Input Parameters",
            parameters,
            parameters,
            order=["Parameter", "Value", "Units", "Description"],
        )

        hardware_data = []
        for h in capture["TargetProgramRun"]["Hardware"]:
            hardware = {
                "Selected Equipment Address": h["SelectedToolResourceDescription"],
                "Selected Equipment Descriptor": h["SelectedToolDescription"],
                "Channel": h["Channel"],
            }
            if "$ref" in h["RequestedHardware"].keys():
                hardware_name = json_refs[h["RequestedHardware"]["$ref"]]["Name"]
            else:
                hardware_name = h["RequestedHardware"]["Name"]
            hardware["Name"] = hardware_name
            hardware_data.append(hardware)

        tab.add_table("Equipment", hardware_data, order=["Name"])

    program_code = ""
    if "$ref" in capture["TargetProgramRun"]["TargetProgram"].keys():
        program_code = json_refs[capture["TargetProgramRun"]["TargetProgram"]["$ref"]][
            "Program"
        ]["Code"]
    else:
        program_code = capture["TargetProgramRun"]["TargetProgram"]["Program"]["Code"]
    tab.add_code_block(
        "Test Code",
        program_code,
        "py",
        False,
    )
    tab.add_code_block("Raw Data", json.dumps(input_file, indent=4), "json", False)


def render_html(report, filepath):
    file = open(filepath, "w", encoding="utf-8")
    file.write(report.render())
    file.close()
    # from xhtml2pdf import pisa             # import python module

    ## open output file for writing (truncated binary)
    # result_file = open(filepath+".pdf", "w+b")

    ## convert HTML to PDF
    # pisa_status = pisa.CreatePDF(
    #        report.render(),                # the HTML to convert
    #        dest=result_file)           # file handle to recieve result

    ## close output file
    # result_file.close()                 # close output file

    ## return True on success and False on errors
    # return pisa_status.err


def generate_single(name, generate_contents, data, input_file, output_file):
    report = Report(name)
    generate_contents(report, data)
    if data != "test only":
        add_properties(report, data, input_file)
    render_html(report, output_file)
    return report


json_refs = {}


def parse_system_text_json(incoming):
    if "$id" in incoming.keys():
        json_refs[incoming["$id"]] = incoming

    if "$ref" in incoming.keys():
        incoming = json_refs[incoming["$ref"]]

    if "$values" in incoming.keys():
        return incoming["$values"]
    else:
        return incoming


def generate(
    generate_contents,
    name,
    test_key=None,
    parameters={},
    include_files=[],
    supports_multiple=False,
    data_file="data.json",
):
    arg_parser = argparse.ArgumentParser(
        description="This is a VR Reporting Application"
    )
    arg_parser.add_argument("--info", action="store_true")
    arg_parser.add_argument("--input", "-i", default=data_file)
    arg_parser.add_argument("--output", "-o", default="Report.html")
    arg_parser.add_argument("--debug", "-d", action="store_true")

    args = arg_parser.parse_args()

    if args.info:
        include_files += [
            "report_framework_base.html",
            "report_framework_chart.html",
            "report_framework_table.html",
        ]
        print(
            "@info "
            + json.dumps(
                {
                    "test_key": test_key,
                    "type": "report",
                    "parameters": parameters,
                    "include_files": include_files,
                    "supports_multiple": supports_multiple,
                },
                cls=EnumEncoder,
            )
        )
        exit()
    runs = None
    try:
        if data_file is not None:
            with open(args.input, "r", encoding="utf-8") as input_file:
                json_decode = json.load(input_file, object_hook=parse_system_text_json)
                if data_file.endswith("data.json"):
                    runs = []

                    for r in json_decode["Runs"]:
                        if (
                            "$ref" not in r.keys()
                            and "$ref"
                            not in r["TargetProgramRun"]["TargetProgram"].keys()
                        ):
                            if (
                                r["TargetProgramRun"]["TargetProgram"]["Program"][
                                    "TestKey"
                                ]
                                == test_key
                            ):
                                runs.append(r)
                        else:
                            if (
                                json_refs[
                                    r["TargetProgramRun"]["TargetProgram"]["$ref"]
                                ]["Program"]["TestKey"]
                                == test_key
                            ):
                                runs.append(r)
                else:
                    runs = json_decode["Runs"]
    except Exception:
        print("Error loading data file")

    files = []
    if supports_multiple:
        generate_single(name, generate_contents, runs, json_decode, args.output)
        files.append("Report.html")
    else:
        i = 1
        if runs is not None:
            for run in runs:
                path_parts = os.path.splitext(args.output)
                if len(runs) > 1:
                    filename = "{}_{}{}".format(path_parts[0], i, path_parts[1])
                else:
                    filename = args.output
                generate_single(name, generate_contents, run, json_decode, filename)
                files.append(filename)
                i += 1
        else:
            filename = args.output
            generate_single(
                name, generate_contents, "test only", "json_decode", filename
            )
            files.append(os.path.abspath(filename))

    print(files)


class TextBlock(object):
    template = """
        <h2>{{ title }}</h2>
        <p class="lead">{{ text }}</p>
    """

    def __init__(self, title, text):
        self.title = title
        self.text = text

    def render(self):
        return Template(TextBlock.template).render(text=self.text, title=self.title)


class CodeBlock(object):
    template = """
        <p class="text-center">
            {% if download_button != None %}
                {{ download_button.render() }}
            {% endif %}
            {% if show_code %}
                <pre class="mb-4"><code>{{ code }}</code></pre>
            {% endif %}
        </p>
    """

    def __init__(self, title, code, file_type, show_code):
        self.title = title
        self.code = code
        self.file_type = file_type
        self.id = uuid.uuid1()
        self.show_code = show_code

    def render(self):
        env = Environment()
        template = env.from_string(CodeBlock.template)
        return template.render(
            code=self.code,
            title=self.title,
            file_type=self.file_type,
            id=self.id,
            show_code=self.show_code,
            download_button=Download(
                self.title, self.code, True, True, file_type=self.file_type
            ),
        )


class Chart(object):
    def __init__(self, tab, title, x_axis_label, y_axis_label, export_data=None):
        with open("report_framework_chart.html", "r", encoding="utf-8") as t_file:
            self.template = t_file.read()

        self.parent_tab = tab
        self.id = uuid.uuid1()
        self.title = title
        self.chart_data = []
        self.chart_options = {"legend": {"orientation": "h", "y": "-.5"}}
        self.counts = {}
        self.export_data = export_data

        if x_axis_label is not None:
            self.add_scatter_axis(x_axis_label, "x")
        if y_axis_label is not None:
            self.add_scatter_axis(y_axis_label, "y")

    def add_scatter_axis(
        self, label, axis, position=None, range_slider=False, zoomable=True, range=None
    ):
        if axis not in self.counts:
            self.counts[axis] = 0

        name = "{}axis{}".format(
            axis, self.counts[axis] + 1 if self.counts[axis] > 0 else ""
        )
        self.chart_options[name] = {"title": label}
        if self.counts[axis] > 0:
            self.chart_options[name]["overlaying"] = axis
        if position is not None:
            self.chart_options[name]["side"] = position
        if range_slider:
            self.chart_options[name]["rangeslider"] = {}
        self.chart_options[name]["fixedrange"] = "false" if zoomable else "true"

        self.counts[axis] += 1

        return name[:1] + name[5:]

    def add_surface(self, x_data, y_data, z_data):
        new_series = {"x": x_data, "y": y_data, "z": z_data, "type": "surface"}
        self.chart_options["scene"]["aspectmode"] = "cube"
        # Determine if log or linear for x axis
        step_sizes = []
        for idxx, x in enumerate(x_data[1:]):
            if x - x_data[idxx] not in step_sizes:
                step_sizes.append(x - x_data[idxx])
        if len(step_sizes) >= 2:
            self.chart_options["scene"]["xaxis"]["type"] = "log"

        # Determine if log or linear for y axis
        step_sizes = []
        for idxy, y in enumerate(y_data[1:]):
            if y - y_data[idxy] not in step_sizes:
                step_sizes.append(y - y_data[idxy])
        if len(step_sizes) >= 2:
            self.chart_options["scene"]["yaxis"]["type"] = "log"
        self.chart_data.append(new_series)

    def add_surface_axis(self, label, axis):
        if axis not in self.counts:
            self.counts[axis] = 0

        name = "{}axis{}".format(
            axis, self.counts[axis] + 1 if self.counts[axis] > 0 else ""
        )
        if "scene" not in self.chart_options:
            self.chart_options["scene"] = {}

        self.chart_options["scene"][name] = {"title": label}

    def set_range(self, range=[0, 100]):
        if range is not None:
            self.chart_options["xaxis"]["range"] = range

    def add_scatter(
        self,
        title,
        data,
        dashed=False,
        show_points=True,
        axis=None,
        axis_id=None,
        point_style=None,
        point_radius=None,
        show_line=True,
        line_shape="linear",
        optimize=None,
        visible=True,
        color=None,
        point_line_width=None,
        dash_style="dashdot",
    ):
        if not isinstance(title, str):
            raise ValueError("Title must be a string")
        if not all(["x" in _ and "y" in _ for _ in data]):
            raise ValueError("All data values need to have an x and y property")

        if optimize is None:
            optimize = False

        if optimize:
            new_data = []
            point = None
            value = None
            value_last = None
            for point_next in data:
                value_next = point_next["y"]
                if value_last != value or value != value_next:
                    if point is not None:
                        new_data.append(point)
                value_last = value
                value = value_next
                point = point_next
            new_data.append(point)
            data = new_data

        new_series = {
            "x": [i["x"] for i in data],
            "y": [i["y"] for i in data],
            "type": "scatter",
            "name": title,
            "line": {"shape": line_shape},
            "visible": "true" if visible else "legendonly",
        }

        if show_points and show_line:
            new_series["mode"] = "lines+markers"
        elif show_points:
            new_series["mode"] = "markers"
        else:
            new_series["mode"] = "lines"

        if dashed:
            new_series["line"]["dash"] = dash_style

        if color:
            new_series["line"]["color"] = color

        if axis is not None and axis_id is not None:
            new_series[axis + "axis"] = axis_id

        if point_radius is not None or point_style is not None:
            new_series["marker"] = {}
        if point_style is not None:
            new_series["marker"]["symbol"] = point_style
        if point_radius is not None:
            new_series["marker"]["size"] = point_radius
        if point_line_width is not None:
            new_series["marker"]["line"] = {}
            new_series["marker"]["line"]["width"] = point_line_width
            new_series["marker"]["line"]["color"] = "black" if color is None else color

        self.chart_data.append(new_series)

    def render(self):
        if self.export_data is None:
            if "yaxis2" in self.chart_options.keys():
                # scatter with 2 y axes
                self.export_data = [
                    {
                        self.chart_options["xaxis"]["title"]
                        + series["name"]: series["x"],
                        self.chart_options["yaxis"]["title"]
                        + series["name"]: series["y"],
                        self.chart_options["yaxis2"]["title"]
                        + series["name"]: series["y"],
                    }
                    for series in self.chart_data
                ]
                # scatter with one y axis
            elif "yaxis" in self.chart_options.keys():
                self.export_data = []
                for series in self.chart_data:
                    for x_idx, x_value in enumerate(series["x"]):
                        self.export_data.append(
                            {
                                "SeriesY": self.chart_options["yaxis"]["title"]
                                + series["name"],
                                "SeriesX": self.chart_options["xaxis"]["title"]
                                + series["name"],
                                "X": x_value,
                                "Y": series["y"][x_idx],
                            }
                        )
            # Surface graph
            elif "scene" in self.chart_options.keys():
                self.export_data = []
                for idx, series in enumerate(self.chart_data):
                    for yval in series["y"]:
                        self.export_data.append({"Series {}".format(idx): str(yval)})
                    for row_idx, row in enumerate(self.export_data[1:], 0):
                        for col_idx, xval in enumerate(series["x"]):
                            row[str(xval)] = series["z"][row_idx][col_idx]

        return Template(self.template).render(
            title=self.title,
            chart_data=self.chart_data,
            chart_options=self.chart_options,
            id=self.id,
            parent_tab=self.parent_tab,
            filename=self.title or "data",
            download_button=(
                None
                if self.export_data is None
                else Download(
                    self.title,
                    self.export_data,
                    file_type="csv",
                    filename=self.title,
                    inside_other_element=True,
                )
            ),
        )


class Table(object):
    def __init__(
        self,
        title,
        presentation_data=None,
        export_data=None,
        groups=[],
        order=[],
        footer=None,
    ):
        with open("report_framework_table.html", "r", encoding="utf-8") as t_file:
            self.template = t_file.read()

        self.data = presentation_data
        self.export_data = export_data
        self.title = title
        self.groups = groups
        self.order = order
        self.footer = footer

    def render(self):
        if self.data is not None:
            if data_tools.has_dict_children(self.data):
                non_group_titles = [i for i in self.order if i not in self.groups]
                for i in next(iter(self.data)):
                    if i not in self.groups and i not in non_group_titles:
                        non_group_titles.append(i)
            else:
                non_group_titles = list(set(self.data) - set(self.groups))
        else:
            non_group_titles = []

        env = Environment()
        env.filters["has_dict_children"] = data_tools.has_dict_children
        env.filters["is_yesno_column"] = data_tools.is_yesno_column
        env.filters["is_dict"] = data_tools.is_dict
        env.filters["count_offspring"] = data_tools.count_offspring
        template = env.from_string(self.template)
        return template.render(
            title=self.title,
            data=data_tools.group_by_keys(self.data, self.groups),
            titles=list(self.groups) + non_group_titles,
            non_group_titles=non_group_titles,
            filename=self.title or "data",
            download_button=(
                None
                if self.export_data is None
                else Download(
                    self.title,
                    self.export_data,
                    file_type="csv",
                    filename=self.title,
                    inside_other_element=True,
                )
            ),
            footer=self.footer,
        )

    @staticmethod
    def filter_to(data, keys):
        if not isinstance(data, list):
            raise ValueError("Data value must be a list type")
        for item in data:
            if not isinstance(item, dict):
                raise ValueError("Data list must contain only dict types")
            for key in item:
                if not isinstance(key, str):
                    raise ValueError("List -> Dict -> Keys must be of str type")
        if not isinstance(keys, list):
            raise ValueError("Keys must be a list type")
        for item in keys:
            if not isinstance(item, str):
                raise ValueError("All keys to filter by must be str type")

        to_remove = set(data) - set(keys)
        for item in to_remove:
            data.pop(item, None)


class Download(object):
    template = """
        <p class="text-center mb-{% if bottom_margin %}4{% else %}0{% endif %}">
            <button id="b-download-{{ id }}" type="button"
            class="btn btn-lg btn-outline-dark
            {% if export_data == None %}d-none{% endif %}">
                <i class="fas fa-file-download"></i>
                <b>{{ title }}</b>
            </button>
        </p>
        <script>
            $('#b-download-{{ id }}').click(
                function () {
                    var data = {{ export_data | tojson }};
                    {% if raw_data %}
                        performDownload('data:text/csv;charset=utf-8,' + data, '{{ filename }}');
                    {% else %}
                        JSONToCSVConvertor(data, '{{ filename }}', true);
                    {% endif %}
                }
            )
        </script>
    """

    def __init__(
        self,
        title,
        export_data,
        inside_other_element=False,
        raw_data=False,
        file_type="json",
        filename="data",
    ):
        self.title = title
        self.id = uuid.uuid1()
        self.inside_other_element = inside_other_element
        self.raw_data = raw_data
        self.export_data = export_data
        self.file_type = file_type
        self.filename = filename + "." + file_type

    def render(self):
        env = Environment()
        env.filters["escapejs"] = escapejs
        template = env.from_string(self.template)
        return template.render(
            title=self.title,
            export_data=self.export_data,
            filename=self.filename,
            id=self.id,
            bottom_margin=(not self.inside_other_element),
            raw_data=self.raw_data,
        )


class Tab(object):
    template = """
        <h1 class="display-4 mt-2 mb-4">{{ title }}</h1>
        {% for content in contents %}
            {{ content.render() }}
        {% endfor %}
    """

    def __init__(self, title):
        self.title = title
        self.id = uuid.uuid1()
        self.contents = list()

    def add_download(self, title, export_data):
        self.contents.append(Download(title, export_data, False))

    def add_table(
        self, title, presentation_data=None, export_data=None, groups=[], order=[]
    ):
        table = Table(title, presentation_data, export_data, groups, order)
        self.contents.append(table)
        return table

    def add_chart(self, title, x_axis_label=None, y_axis_label=None, export_data=None):
        chart = Chart(self, title, x_axis_label, y_axis_label, export_data)
        self.contents.append(chart)
        return chart

    def add_text_block(self, title, text):
        text_block = TextBlock(title, text)
        self.contents.append(text_block)
        return text_block

    def add_code_block(self, title, code, file_type, show_code=True):
        code_block = CodeBlock(title, code, file_type, show_code)
        self.contents.append(code_block)
        return code_block

    def render(self):
        return Template(Tab.template).render(title=self.title, contents=self.contents)


class Report(object):
    def __init__(self, title):
        with open("report_framework_base.html", "r", encoding="utf-8") as t_file:
            self.template = t_file.read()

        self.tabs_left = {None: []}
        self.tabs_right = {None: []}
        self.title = title

    def add_tab_left(self, title, group=None):
        new_tab = Tab(title)
        if group not in self.tabs_left:
            self.tabs_left[group] = []
        self.tabs_left[group].append(new_tab)
        return new_tab

    def add_tab_right(self, title, group=None):
        new_tab = Tab(title)
        if group not in self.tabs_right:
            self.tabs_right[group] = []
        self.tabs_right[group].append(new_tab)
        return new_tab

    def render(self):
        tabs_left = {None: []}
        tabs_right = {None: []}

        for key, tab_list in self.tabs_left.items():
            if key is not None and len(tab_list) == 1:
                tab = tab_list[0]
                tab.title = key + " " + tab.title
                tabs_left[None].append(tab)
            else:
                tabs_left[key] = tab_list

        for key, tab_list in self.tabs_right.items():
            if key is not None and len(tab_list) == 1:
                tab = tab_list[0]
                tab.title = key + " " + tab.title
                tabs_right[None].append(tab)
            else:
                tabs_right[key] = tab_list

        tabs_left_grouped = {k: v for k, v in tabs_left.items() if k is not None}
        tabs_right_grouped = {k: v for k, v in tabs_right.items() if k is not None}

        tabs = []
        for group in chain(tabs_left.values(), tabs_right.values()):
            tabs.extend(group)

        return Template(self.template).render(
            title=self.title,
            tabs_left=tabs_left[None],
            tabs_left_grouped=tabs_left_grouped,
            tabs_right=tabs_right[None],
            tabs_right_grouped=tabs_right_grouped,
            tabs=tabs,
        )
