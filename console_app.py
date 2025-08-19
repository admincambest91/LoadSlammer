
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
