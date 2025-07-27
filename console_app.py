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

import builtins
import sys
import json
from enum import Enum


def output(message):
    return builtins.print(message, flush=True, file=sys.stdout)


def output_err(message):
    return builtins.print(message, flush=True, file=sys.stderr)


# Unused
def output_axes(x_axis, y_axis):
    return output("@axes " + x_axis + ", " + y_axis)


def output_status(newStatus, *args, **kargs):
    return output("@status {}".format(newStatus.format(*args, **kargs)))


def output_progress(progress):
    return output("@progress " + str(progress))


def output_measurement(measurement_collection):
    return output("@measurement " + json.dumps(measurement_collection))


def output_named_measurement(measurement_collection):
    return output("@namedmeasurement " + json.dumps(measurement_collection))


def prompt(message, is_error=False):
    m = "@prompt {} ==> [PRESS ENTER TO PROCEED]".format(message)
    if is_error is True:
        output_err(m)
    else:
        output(m)
    input()


def error_out(message):
    output_err("@error " + message)
    exit()


def error_out_if(condition, message):
    if condition:
        error_out(message)
