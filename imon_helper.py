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

import math
import sys
import time
import winreg

from console_app import output_status
from test_framework_enums import ParameterType

with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, R"SOFTWARE\Intel\UPDT") as key:
    (reg_val, reg_type) = winreg.QueryValueEx(key, "InstallPath")
    sys.path.append(reg_val)

import clr

clr.AddReference("Common")

from Common.APIs import DataAPI, VectorAPI
from Common.Enumerations import SVIDBURSTTRIGGER, SVIDCMD

PROTOCOL_IDS_VR14 = [0x09, 0x0A, 0x0B, 0x0C, 0x0E]
PROTOCOL_IDS_VR13 = [0x07, 0x04, 0x08, 0x05]

vector_read_delay = 0


# evaluate VIDOMAX_H_CAPA reg (0x09)
# Extended Capability Register and MSBit of 9-bit VID+OFFSET max value [bit 0 of teg 0x09]
def eval_vidoffset_max_high_cap(static_registers):
    vid_offset_max_high_capa = static_registers["[REG] VIDOMAX_H_CAPA 0x09"]
    return vid_offset_max_high_capa


# evaluate VIDOMAX_L_CAPA reg (0x0A)
# Extended Capability Register and LSByte of 9-bit VID+OFFSET max value
def eval_vidoffset_max_low_cap(static_registers):
    vid_offset_max_low_capa = static_registers["[REG] VIDOMAX_L_CAPA 0x0A"]
    protocol_id = static_registers["[REG] Protocol 0x05"]
    vidomax_l_converted = eval_volt_setting(vid_offset_max_low_capa, protocol_id)
    return vidomax_l_converted


# full conversion result for VID +Offset value ([REG] 0x09 bit 0 and [REG] 0x0A )
def eval_vid_offset_max(static_registers):
    vid_offset_max_low_capa = static_registers["[REG] VIDOMAX_L_CAPA 0x0A"]
    protocol_id = static_registers["[REG] Protocol 0x05"]
    vidomax_h = eval_vidoffset_max_high_cap(static_registers)
    vidomax_h_masked = vidomax_h & 0x01

    if vidomax_h_masked == 0:  # if maskeed value of  reg x09 is = x00
        vid_offset_max = eval_volt_setting(
            vid_offset_max_low_capa, protocol_id
        )  # convert value of reg x0A
        return vid_offset_max
    elif vidomax_h_masked == 1:  # if masked value of  reg x09 is = x01
        vid_offset_max_extended = (
            vidomax_h << 8
        ) + vid_offset_max_low_capa  # concatinate masked reg x09 (MSB)  with reg x0A (LSB)
        vidomax_l_converted = eval_volt_setting(vid_offset_max_extended, protocol_id)
        return vidomax_l_converted


# evaluate Protocol Id
def eval_protocol(static_registers):
    protocol_id = static_registers["[REG] Protocol 0x05"]
    if protocol_id in PROTOCOL_IDS_VR14:
        return "VR_14"
    elif protocol_id in PROTOCOL_IDS_VR13:
        return "VR_13"
    else:
        return "VR"


# evaluate register Power In Max( PIN_MAX 2Eh) and calculate the Effective maximum Input Power:
def eval_pin_max(static_registers):
    # IMVP8, IMVP9, VR13 w/ HC_ACTIVE = 0 >> 2* PIN_MAX 0x2E
    # VR13 w/ HC_ACTIVE = 1 >> 2* PIN_MAX 0x2E + 4 * PIN_MAX_ADD  (VR13.HC:0x51)
    # VR14 >> 2* PIN_MAX 0x2E * 4^W_per_bit_out (VR14:50h, bits 4:2)
    #     OR
    # Just use the number from register times 2:  (2*0x2E)
    protocol_id = static_registers["[REG] Protocol 0x05"]
    pin_max_reg = static_registers["[REG] PIN_MAX 0x2E"]
    pin_max_add_reg = static_registers["[REG] PIN_MAX_ADD 0x51"]
    icc_max_add_reg = static_registers["[REG] ICC_MAX_ADD 0x50"]
    hc_mode_supported, hc_mode_active = eval_hc_mode(static_registers)
    # for VR14
    if protocol_id in PROTOCOL_IDS_VR14:
        return 2 * pin_max_reg * (2 ** ((icc_max_add_reg & 0x1C) >> 2))
    # for VR13 w/ HC_ACTIVE = 1
    elif protocol_id in PROTOCOL_IDS_VR13 and hc_mode_supported and hc_mode_active:
        return 2 * pin_max_reg + 4 * pin_max_add_reg
    else:
        return 2 * pin_max_reg


# Evaluate PIN_ALERT_TH 0x2F  and Calculate the effective Input Power alert
# This 8-bit read-write register is by default the same value Power In Max
# (address 2Eh), but can be set by the SVID master to any value lower than Power In Max (0x2E)
def eval_pin_alert_th(static_registers):
    protocol_id = static_registers["[REG] Protocol 0x05"]
    pin_alert_th = static_registers["[REG] PIN_ALERT_TH 0x2F"]
    pin_alert_th_add = static_registers["[REG] PIN_ALERT_TH_ADD 0x52"]
    icc_max_add_reg = static_registers["[REG] ICC_MAX_ADD 0x50"]
    hc_mode_supported, hc_mode_active = eval_hc_mode(static_registers)
    # for VR14
    if protocol_id in PROTOCOL_IDS_VR14:
        return 2 * pin_alert_th * (2 ** ((icc_max_add_reg & 0x1C) >> 2))
    # for VR13 w/ HC_ACTIVE = 1
    elif protocol_id in PROTOCOL_IDS_VR13 and hc_mode_supported and hc_mode_active:
        return 2 * pin_alert_th + 4 * pin_alert_th_add
    else:
        return 2 * pin_alert_th


# Evaluate DCLL register 0x23:
def eval_dcll(static_registers):
    dcll = static_registers["[REG] DC_LL 0x23"]
    return dcll * 0.1


# Evaluate SetVID Fast register 0x24:
def eval_setvid_fast(static_registers):
    set_vid_fast = static_registers["[REG] SetVID_Fast 0x24"]
    return set_vid_fast


# Evaluate AVP register 0x36:
def eval_avp(static_registers):
    avp = static_registers["[REG] DC_LL_FINE 0x36"]
    return avp * 0.001


#  Evaluate Load Line:
def eval_ll(static_registers):
    protocol_id = static_registers["[REG] Protocol 0x05"]
    # for VR14 (pg 134)
    if protocol_id in PROTOCOL_IDS_VR14:
        return eval_dcll(static_registers) + eval_avp(static_registers)
    # for VR13 w/ HC_ACTIVE = 1
    elif protocol_id in PROTOCOL_IDS_VR13:
        return eval_dcll(static_registers)


#  Evaluate Capability:
def eval_capability(static_registers):
    capability_decimal = static_registers["[REG] CAPABILITY 0x06"]
    return format(capability_decimal, "08b")


#  Evaluate vidomax_h_capa:
def eval_vidomax_h_capa(static_registers):
    vidomax_h_capa = static_registers["[REG] VIDOMAX_H_CAPA 0x09"]
    return format(vidomax_h_capa, "08b")


#  Evaluate vidomax_h_capa:
def eval_slow_sr_sel_hc(static_registers):
    slow_sr_sel = static_registers["[REG] SLOW_SR_SEL_HC 0x2A"]
    if slow_sr_sel >> 3 & 1:
        return "Fast SR/16"
    elif slow_sr_sel >> 2 & 1:
        return "Fast SR/8"
    elif slow_sr_sel >> 1 & 1:
        return "Fast SR/4"
    elif slow_sr_sel >> 0 & 1:
        return "Fast SR/2"
    else:
        return "Prior Setting"


# evaluate VBoot register 0x26:
PROTOCOL_5mV = [5, 7, 9]
PROTOCOL_10mV = [4, 10]
PROTOCOL_IMPV9 = [8, 14]


# Conversion of Vboot register 0x26:
#
def eval_vboot(static_registers):
    vboot = static_registers["[REG] VBoot 0x26"]
    protocol_id = static_registers["[REG] Protocol 0x05"]
    vboot_converted = eval_volt_setting(vboot, protocol_id)
    return vboot_converted


# SVID VID tables:
Table_5mV = {
    0: "0.000",
    1: "0.250",
    2: "0.255",
    3: "0.260",
    4: "0.265",
    5: "0.270",
    6: "0.275",
    7: "0.280",
    8: "0.285",
    9: "0.290",
    10: "0.295",
    11: "0.300",
    12: "0.305",
    13: "0.310",
    14: "0.315",
    15: "0.320",
    16: "0.325",
    17: "0.330",
    18: "0.335",
    19: "0.340",
    20: "0.345",
    21: "0.350",
    22: "0.355",
    23: "0.360",
    24: "0.365",
    25: "0.370",
    26: "0.375",
    27: "0.380",
    28: "0.385",
    29: "0.390",
    30: "0.395",
    31: "0.400",
    32: "0.405",
    33: "0.410",
    34: "0.415",
    35: "0.420",
    36: "0.425",
    37: "0.430",
    38: "0.435",
    39: "0.440",
    40: "0.445",
    41: "0.450",
    42: "0.455",
    43: "0.460",
    44: "0.465",
    45: "0.470",
    46: "0.475",
    47: "0.480",
    48: "0.485",
    49: "0.490",
    50: "0.495",
    51: "0.500",
    52: "0.505",
    53: "0.510",
    54: "0.515",
    55: "0.520",
    56: "0.525",
    57: "0.530",
    58: "0.535",
    59: "0.540",
    60: "0.545",
    61: "0.550",
    62: "0.555",
    63: "0.560",
    64: "0.565",
    65: "0.570",
    66: "0.575",
    67: "0.580",
    68: "0.585",
    69: "0.590",
    70: "0.595",
    71: "0.600",
    72: "0.605",
    73: "0.610",
    74: "0.615",
    75: "0.620",
    76: "0.625",
    77: "0.630",
    78: "0.635",
    79: "0.640",
    80: "0.645",
    81: "0.650",
    82: "0.655",
    83: "0.660",
    84: "0.665",
    85: "0.670",
    86: "0.675",
    87: "0.680",
    88: "0.685",
    89: "0.690",
    90: "0.695",
    91: "0.700",
    92: "0.705",
    93: "0.710",
    94: "0.715",
    95: "0.720",
    96: "0.725",
    97: "0.730",
    98: "0.735",
    99: "0.740",
    100: "0.745",
    101: "0.750",
    102: "0.755",
    103: "0.760",
    104: "0.765",
    105: "0.770",
    106: "0.775",
    107: "0.780",
    108: "0.785",
    109: "0.790",
    110: "0.795",
    111: "0.800",
    112: "0.805",
    113: "0.810",
    114: "0.815",
    115: "0.820",
    116: "0.825",
    117: "0.830",
    118: "0.835",
    119: "0.840",
    120: "0.845",
    121: "0.850",
    122: "0.855",
    123: "0.860",
    124: "0.865",
    125: "0.870",
    126: "0.875",
    127: "0.880",
    128: "0.885",
    129: "0.890",
    130: "0.895",
    131: "0.900",
    132: "0.905",
    133: "0.910",
    134: "0.915",
    135: "0.920",
    136: "0.925",
    137: "0.930",
    138: "0.935",
    139: "0.940",
    140: "0.945",
    141: "0.950",
    142: "0.955",
    143: "0.960",
    144: "0.965",
    145: "0.970",
    146: "0.975",
    147: "0.980",
    148: "0.985",
    149: "0.990",
    150: "0.995",
    151: "1.000",
    152: "1.005",
    153: "1.010",
    154: "1.015",
    155: "1.020",
    156: "1.025",
    157: "1.030",
    158: "1.035",
    159: "1.040",
    160: "1.045",
    161: "1.050",
    162: "1.055",
    163: "1.060",
    164: "1.065",
    165: "1.070",
    166: "1.075",
    167: "1.080",
    168: "1.085",
    169: "1.090",
    170: "1.095",
    171: "1.100",
    172: "1.105",
    173: "1.110",
    174: "1.115",
    175: "1.120",
    176: "1.125",
    177: "1.130",
    178: "1.135",
    179: "1.140",
    180: "1.145",
    181: "1.150",
    182: "1.155",
    183: "1.160",
    184: "1.165",
    185: "1.170",
    186: "1.175",
    187: "1.180",
    188: "1.185",
    189: "1.190",
    190: "1.195",
    191: "1.200",
    192: "1.205",
    193: "1.210",
    194: "1.215",
    195: "1.220",
    196: "1.225",
    197: "1.230",
    198: "1.235",
    199: "1.240",
    200: "1.245",
    201: "1.250",
    202: "1.255",
    203: "1.260",
    204: "1.265",
    205: "1.270",
    206: "1.275",
    207: "1.280",
    208: "1.285",
    209: "1.290",
    210: "1.295",
    211: "1.300",
    212: "1.305",
    213: "1.310",
    214: "1.315",
    215: "1.320",
    216: "1.325",
    217: "1.330",
    218: "1.335",
    219: "1.340",
    220: "1.345",
    221: "1.350",
    222: "1.355",
    223: "1.360",
    224: "1.365",
    225: "1.370",
    226: "1.375",
    227: "1.380",
    228: "1.385",
    229: "1.390",
    230: "1.395",
    231: "1.400",
    232: "1.405",
    233: "1.410",
    234: "1.415",
    235: "1.420",
    236: "1.425",
    237: "1.430",
    238: "1.435",
    239: "1.440",
    240: "1.445",
    241: "1.450",
    242: "1.455",
    243: "1.460",
    244: "1.465",
    245: "1.470",
    246: "1.475",
    247: "1.480",
    248: "1.485",
    249: "1.490",
    250: "1.495",
    251: "1.500",
    252: "1.505",
    253: "1.510",
    254: "1.515",
    255: "1.520",
    256: "1.525",
    257: "1.530",
    258: "1.535",
    259: "1.540",
    260: "1.545",
    261: "1.550",
    262: "1.555",
    263: "1.560",
    264: "1.565",
    265: "1.570",
    266: "1.575",
    267: "1.580",
    268: "1.585",
    269: "1.590",
    270: "1.595",
    271: "1.600",
    272: "1.605",
    273: "1.610",
    274: "1.615",
    275: "1.620",
    276: "1.625",
    277: "1.630",
    278: "1.635",
    279: "1.640",
    280: "1.645",
    281: "1.650",
    282: "1.655",
    283: "1.660",
    284: "1.665",
    285: "1.670",
    286: "1.675",
    287: "1.680",
    288: "1.685",
    289: "1.690",
    290: "1.695",
    291: "1.700",
    292: "1.705",
    293: "1.710",
    294: "1.715",
    295: "1.720",
    296: "1.725",
    297: "1.730",
    298: "1.735",
    299: "1.740",
    300: "1.745",
    301: "1.750",
    302: "1.755",
    303: "1.760",
    304: "1.765",
    305: "1.770",
    306: "1.775",
    307: "1.780",
    308: "1.785",
    309: "1.790",
    310: "1.795",
    311: "1.800",
    312: "1.805",
    313: "1.810",
    314: "1.815",
    315: "1.820",
    316: "1.825",
    317: "1.830",
    318: "1.835",
    319: "1.840",
    320: "1.845",
    321: "1.850",
    322: "1.855",
    323: "1.860",
    324: "1.865",
    325: "1.870",
    326: "1.875",
    327: "1.880",
    328: "1.885",
    329: "1.890",
    330: "1.895",
    331: "1.900",
    332: "1.905",
    333: "1.910",
    334: "1.915",
    335: "1.920",
    336: "1.925",
    337: "1.930",
    338: "1.935",
    339: "1.940",
    340: "1.945",
    341: "1.950",
    342: "1.955",
    343: "1.960",
    344: "1.965",
    345: "1.970",
    346: "1.975",
    347: "1.980",
    348: "1.985",
    349: "1.990",
    350: "1.995",
    351: "2.000",
    352: "2.005",
    353: "2.010",
    354: "2.015",
    355: "2.020",
    356: "2.025",
    357: "2.030",
    358: "2.035",
    359: "2.040",
    360: "2.045",
    361: "2.050",
    362: "2.055",
    363: "2.060",
    364: "2.065",
    365: "2.070",
    366: "2.075",
    367: "2.080",
    368: "2.085",
    369: "2.090",
    370: "2.095",
    371: "2.100",
    372: "2.105",
    373: "2.110",
    374: "2.115",
    375: "2.120",
    376: "2.125",
    377: "2.130",
    378: "2.135",
    379: "2.140",
    380: "2.145",
    381: "2.150",
    382: "2.155",
    383: "2.160",
    384: "2.165",
}

Table_10mV = {
    0: "0.000",
    1: "0.500",
    2: "0.510",
    3: "0.520",
    4: "0.530",
    5: "0.540",
    6: "0.550",
    7: "0.560",
    8: "0.570",
    9: "0.580",
    10: "0.590",
    11: "0.600",
    12: "0.610",
    13: "0.620",
    14: "0.630",
    15: "0.640",
    16: "0.650",
    17: "0.660",
    18: "0.670",
    19: "0.680",
    20: "0.690",
    21: "0.700",
    22: "0.710",
    23: "0.720",
    24: "0.730",
    25: "0.740",
    26: "0.750",
    27: "0.760",
    28: "0.770",
    29: "0.780",
    30: "0.790",
    31: "0.800",
    32: "0.810",
    33: "0.820",
    34: "0.830",
    35: "0.840",
    36: "0.850",
    37: "0.860",
    38: "0.870",
    39: "0.880",
    40: "0.890",
    41: "0.900",
    42: "0.910",
    43: "0.920",
    44: "0.930",
    45: "0.940",
    46: "0.950",
    47: "0.960",
    48: "0.970",
    49: "0.980",
    50: "0.990",
    51: "1.000",
    52: "1.010",
    53: "1.020",
    54: "1.030",
    55: "1.040",
    56: "1.050",
    57: "1.060",
    58: "1.070",
    59: "1.080",
    60: "1.090",
    61: "1.100",
    62: "1.110",
    63: "1.120",
    64: "1.130",
    65: "1.140",
    66: "1.150",
    67: "1.160",
    68: "1.170",
    69: "1.180",
    70: "1.190",
    71: "1.200",
    72: "1.210",
    73: "1.220",
    74: "1.230",
    75: "1.240",
    76: "1.250",
    77: "1.260",
    78: "1.270",
    79: "1.280",
    80: "1.290",
    81: "1.300",
    82: "1.310",
    83: "1.320",
    84: "1.330",
    85: "1.340",
    86: "1.350",
    87: "1.360",
    88: "1.370",
    89: "1.380",
    90: "1.390",
    91: "1.400",
    92: "1.410",
    93: "1.420",
    94: "1.430",
    95: "1.440",
    96: "1.450",
    97: "1.460",
    98: "1.470",
    99: "1.480",
    100: "1.490",
    101: "1.500",
    102: "1.510",
    103: "1.520",
    104: "1.530",
    105: "1.540",
    106: "1.550",
    107: "1.560",
    108: "1.570",
    109: "1.580",
    110: "1.590",
    111: "1.600",
    112: "1.610",
    113: "1.620",
    114: "1.630",
    115: "1.640",
    116: "1.650",
    117: "1.660",
    118: "1.670",
    119: "1.680",
    120: "1.690",
    121: "1.700",
    122: "1.710",
    123: "1.720",
    124: "1.730",
    125: "1.740",
    126: "1.750",
    127: "1.760",
    128: "1.770",
    129: "1.780",
    130: "1.790",
    131: "1.800",
    132: "1.810",
    133: "1.820",
    134: "1.830",
    135: "1.840",
    136: "1.850",
    137: "1.860",
    138: "1.870",
    139: "1.880",
    140: "1.890",
    141: "1.900",
    142: "1.910",
    143: "1.920",
    144: "1.930",
    145: "1.940",
    146: "1.950",
    147: "1.960",
    148: "1.970",
    149: "1.980",
    150: "1.990",
    151: "2.000",
    152: "2.010",
    153: "2.020",
    154: "2.030",
    155: "2.040",
    156: "2.050",
    157: "2.060",
    158: "2.070",
    159: "2.080",
    160: "2.090",
    161: "2.100",
    162: "2.110",
    163: "2.120",
    164: "2.130",
    165: "2.140",
    166: "2.150",
    167: "2.160",
    168: "2.170",
    169: "2.180",
    170: "2.190",
    171: "2.200",
    172: "2.210",
    173: "2.220",
    174: "2.230",
    175: "2.240",
    176: "2.250",
    177: "2.260",
    178: "2.270",
    179: "2.280",
    180: "2.290",
    181: "2.300",
    182: "2.310",
    183: "2.320",
    184: "2.330",
    185: "2.340",
    186: "2.350",
    187: "2.360",
    188: "2.370",
    189: "2.380",
    190: "2.390",
    191: "2.400",
    192: "2.410",
    193: "2.420",
    194: "2.430",
    195: "2.440",
    196: "2.450",
    197: "2.460",
    198: "2.470",
    199: "2.480",
    200: "2.490",
    201: "2.500",
    202: "2.510",
    203: "2.520",
    204: "2.530",
    205: "2.540",
    206: "2.550",
    207: "2.560",
    208: "2.570",
    209: "2.580",
    210: "2.590",
    211: "2.600",
    212: "2.610",
    213: "2.620",
    214: "2.630",
    215: "2.640",
    216: "2.650",
    217: "2.660",
    218: "2.670",
    219: "2.680",
    220: "2.690",
    221: "2.700",
    222: "2.710",
    223: "2.720",
    224: "2.730",
    225: "2.740",
    226: "2.750",
    227: "2.760",
    228: "2.770",
    229: "2.780",
    230: "2.790",
    231: "2.800",
    232: "2.810",
    233: "2.820",
    234: "2.830",
    235: "2.840",
    236: "2.850",
    237: "2.860",
    238: "2.870",
    239: "2.880",
    240: "2.890",
    241: "2.900",
    242: "2.910",
    243: "2.920",
    244: "2.930",
    245: "2.940",
    246: "2.950",
    247: "2.960",
    248: "2.970",
    249: "2.980",
    250: "2.990",
    251: "3.000",
    252: "3.010",
    253: "3.020",
    254: "3.030",
    255: "3.040",
    256: "3.050",
    257: "3.060",
    258: "3.070",
    259: "3.080",
    260: "3.090",
    261: "3.100",
    262: "3.110",
    263: "3.120",
    264: "3.130",
    265: "3.140",
    266: "3.150",
    267: "3.160",
    268: "3.170",
    269: "3.180",
    270: "3.190",
    271: "3.200",
    272: "3.210",
    273: "3.220",
    274: "3.230",
    275: "3.240",
    276: "3.250",
    277: "3.260",
    278: "3.270",
    279: "3.280",
    280: "3.290",
    281: "3.300",
    282: "3.310",
    283: "3.320",
    284: "3.330",
    285: "3.340",
    286: "3.350",
    287: "3.360",
    288: "3.370",
    289: "3.380",
    290: "3.390",
    291: "3.400",
    292: "3.410",
    293: "3.420",
    294: "3.430",
    295: "3.440",
    296: "3.450",
    297: "3.460",
    298: "3.470",
    299: "3.480",
    300: "3.490",
    301: "3.500",
    302: "3.510",
    303: "3.520",
    304: "3.530",
    305: "3.540",
    306: "3.550",
    307: "3.560",
    308: "3.570",
    309: "3.580",
    310: "3.590",
    311: "3.600",
    312: "3.610",
    313: "3.620",
    314: "3.630",
    315: "3.640",
    316: "3.650",
    317: "3.660",
    318: "3.670",
    319: "3.680",
    320: "3.690",
    321: "3.700",
    322: "3.710",
    323: "3.720",
    324: "3.730",
    325: "3.740",
    326: "3.750",
    327: "3.760",
    328: "3.770",
    329: "3.780",
    330: "3.790",
    331: "3.800",
    332: "3.810",
    333: "3.820",
    334: "3.830",
    335: "3.840",
    336: "3.850",
    337: "3.860",
    338: "3.870",
    339: "3.880",
    340: "3.890",
    341: "3.900",
    342: "3.910",
    343: "3.920",
    344: "3.930",
    345: "3.940",
    346: "3.950",
    347: "3.960",
    348: "3.970",
    349: "3.980",
    350: "3.990",
    351: "4.000",
    352: "4.010",
    353: "4.020",
    354: "4.030",
    355: "4.040",
    356: "4.050",
    357: "4.060",
    358: "4.070",
    359: "4.080",
    360: "4.090",
    361: "4.100",
    362: "4.110",
    363: "4.120",
    364: "4.130",
    365: "4.140",
    366: "4.150",
    367: "4.160",
    368: "4.170",
    369: "4.180",
    370: "4.190",
    371: "4.200",
    372: "4.210",
    373: "4.220",
    374: "4.230",
    375: "4.240",
    376: "4.250",
    377: "4.260",
    378: "4.270",
    379: "4.280",
    380: "4.290",
    381: "4.300",
    382: "4.310",
    383: "4.320",
    384: "4.330",
}


Table_IMPV9 = {
    0: "0.000",
    1: "0.200",
    2: "0.210",
    3: "0.220",
    4: "0.230",
    5: "0.240",
    6: "0.250",
    7: "0.260",
    8: "0.270",
    9: "0.280",
    10: "0.290",
    11: "0.300",
    12: "0.310",
    13: "0.320",
    14: "0.330",
    15: "0.340",
    16: "0.350",
    17: "0.360",
    18: "0.370",
    19: "0.380",
    20: "0.390",
    21: "0.400",
    22: "0.410",
    23: "0.420",
    24: "0.430",
    25: "0.440",
    26: "0.450",
    27: "0.460",
    28: "0.470",
    29: "0.480",
    30: "0.490",
    31: "0.500",
    32: "0.510",
    33: "0.520",
    34: "0.530",
    35: "0.540",
    36: "0.550",
    37: "0.560",
    38: "0.570",
    39: "0.580",
    40: "0.590",
    41: "0.600",
    42: "0.610",
    43: "0.620",
    44: "0.630",
    45: "0.640",
    46: "0.650",
    47: "0.660",
    48: "0.670",
    49: "0.680",
    50: "0.690",
    51: "0.700",
    52: "0.710",
    53: "0.720",
    54: "0.730",
    55: "0.740",
    56: "0.750",
    57: "0.760",
    58: "0.770",
    59: "0.780",
    60: "0.790",
    61: "0.800",
    62: "0.810",
    63: "0.820",
    64: "0.830",
    65: "0.840",
    66: "0.850",
    67: "0.860",
    68: "0.870",
    69: "0.880",
    70: "0.890",
    71: "0.900",
    72: "0.910",
    73: "0.920",
    74: "0.930",
    75: "0.940",
    76: "0.950",
    77: "0.960",
    78: "0.970",
    79: "0.980",
    80: "0.990",
    81: "1.000",
    82: "1.010",
    83: "1.020",
    84: "1.030",
    85: "1.040",
    86: "1.050",
    87: "1.060",
    88: "1.070",
    89: "1.080",
    90: "1.090",
    91: "1.100",
    92: "1.110",
    93: "1.120",
    94: "1.130",
    95: "1.140",
    96: "1.150",
    97: "1.160",
    98: "1.170",
    99: "1.180",
    100: "1.190",
    101: "1.200",
    102: "1.210",
    103: "1.220",
    104: "1.230",
    105: "1.240",
    106: "1.250",
    107: "1.260",
    108: "1.270",
    109: "1.280",
    110: "1.290",
    111: "1.300",
    112: "1.310",
    113: "1.320",
    114: "1.330",
    115: "1.340",
    116: "1.350",
    117: "1.360",
    118: "1.370",
    119: "1.380",
    120: "1.390",
    121: "1.400",
    122: "1.410",
    123: "1.420",
    124: "1.430",
    125: "1.440",
    126: "1.450",
    127: "1.460",
    128: "1.470",
    129: "1.480",
    130: "1.490",
    131: "1.500",
    132: "1.510",
    133: "1.520",
    134: "1.530",
    135: "1.540",
    136: "1.550",
    137: "1.560",
    138: "1.570",
    139: "1.580",
    140: "1.590",
    141: "1.600",
    142: "1.610",
    143: "1.620",
    144: "1.630",
    145: "1.640",
    146: "1.650",
    147: "1.660",
    148: "1.670",
    149: "1.680",
    150: "1.690",
    151: "1.700",
    152: "1.710",
    153: "1.720",
    154: "1.730",
    155: "1.740",
    156: "1.750",
    157: "1.760",
    158: "1.770",
    159: "1.780",
    160: "1.790",
    161: "1.800",
    162: "1.810",
    163: "1.820",
    164: "1.830",
    165: "1.840",
    166: "1.850",
    167: "1.860",
    168: "1.870",
    169: "1.880",
    170: "1.890",
    171: "1.900",
    172: "1.910",
    173: "1.920",
    174: "1.930",
    175: "1.940",
    176: "1.950",
    177: "1.960",
    178: "1.970",
    179: "1.980",
    180: "1.990",
    181: "2.000",
    182: "2.010",
    183: "2.020",
    184: "2.030",
    185: "2.040",
    186: "2.050",
    187: "2.060",
    188: "2.070",
    189: "2.080",
    190: "2.090",
    191: "2.100",
    192: "2.110",
    193: "2.120",
    194: "2.130",
    195: "2.140",
    196: "2.150",
    197: "2.160",
    198: "2.170",
    199: "2.180",
    200: "2.190",
    201: "2.200",
    202: "2.210",
    203: "2.220",
    204: "2.230",
    205: "2.240",
    206: "2.250",
    207: "2.260",
    208: "2.270",
    209: "2.280",
    210: "2.290",
    211: "2.300",
    212: "2.310",
    213: "2.320",
    214: "2.330",
    215: "2.340",
    216: "2.350",
    217: "2.360",
    218: "2.370",
    219: "2.380",
    220: "2.390",
    221: "2.400",
    222: "2.410",
    223: "2.420",
    224: "2.430",
    225: "2.440",
    226: "2.450",
    227: "2.460",
    228: "2.470",
    229: "2.480",
    230: "2.490",
    231: "2.500",
    232: "2.510",
    233: "2.520",
    234: "2.530",
    235: "2.540",
    236: "2.550",
    237: "2.560",
    238: "2.570",
    239: "2.580",
    240: "2.590",
    241: "2.600",
    242: "2.610",
    243: "2.620",
    244: "2.630",
    245: "2.640",
    246: "2.650",
    247: "2.660",
    248: "2.670",
    249: "2.680",
    250: "2.690",
    251: "2.700",
    252: "2.710",
    253: "2.720",
    254: "2.730",
    255: "2.740",
    256: "2.750",
    257: "2.760",
    258: "2.770",
    259: "2.780",
    260: "2.790",
    261: "2.800",
    262: "2.810",
    263: "2.820",
    264: "2.830",
    265: "2.840",
    266: "2.850",
    267: "2.860",
    268: "2.870",
    269: "2.880",
    270: "2.890",
    271: "2.900",
    272: "2.910",
    273: "2.920",
    274: "2.930",
    275: "2.940",
    276: "2.950",
    277: "2.960",
    278: "2.970",
    279: "2.980",
    280: "2.990",
    281: "3.000",
    282: "3.010",
    283: "3.020",
    284: "3.030",
    285: "3.040",
    286: "3.050",
    287: "3.060",
    288: "3.070",
    289: "3.080",
    290: "3.090",
    291: "3.100",
    292: "3.110",
    293: "3.120",
    294: "3.130",
    295: "3.140",
    296: "3.150",
    297: "3.160",
    298: "3.170",
    299: "3.180",
    300: "3.190",
    301: "3.200",
    302: "3.210",
    303: "3.220",
    304: "3.230",
    305: "3.240",
    306: "3.250",
    307: "3.260",
    308: "3.270",
    309: "3.280",
    310: "3.290",
    311: "3.300",
    312: "3.310",
    313: "3.320",
    314: "3.330",
    315: "3.340",
    316: "3.350",
    317: "3.360",
    318: "3.370",
    319: "3.380",
    320: "3.390",
    321: "3.400",
    322: "3.410",
    323: "3.420",
    324: "3.430",
    325: "3.440",
    326: "3.450",
    327: "3.460",
    328: "3.470",
    329: "3.480",
    330: "3.490",
    331: "3.500",
    332: "3.510",
    333: "3.520",
    334: "3.530",
    335: "3.540",
    336: "3.550",
    337: "3.560",
    338: "3.570",
    339: "3.580",
    340: "3.590",
    341: "3.600",
    342: "3.610",
    343: "3.620",
    344: "3.630",
    345: "3.640",
    346: "3.650",
    347: "3.660",
    348: "3.670",
    349: "3.680",
    350: "3.690",
    351: "3.700",
    352: "3.710",
    353: "3.720",
    354: "3.730",
    355: "3.740",
    356: "3.750",
    357: "3.760",
    358: "3.770",
    359: "3.780",
    360: "3.790",
    361: "3.800",
    362: "3.810",
    363: "3.820",
    364: "3.830",
    365: "3.840",
    366: "3.850",
    367: "3.860",
    368: "3.870",
    369: "3.880",
    370: "3.890",
    371: "3.900",
    372: "3.910",
    373: "3.920",
    374: "3.930",
    375: "3.940",
    376: "3.950",
    377: "3.960",
    378: "3.970",
    379: "3.980",
    380: "3.990",
    381: "4.000",
    382: "4.010",
    383: "4.020",
    384: "4.030",
}


# Evaluate and Covert VRtemp register 0x17:
def eval_VRtemp(dynamic_registers, static_registers):
    VR_temp = dynamic_registers["[REG] VR TEMP 0x17"]
    if eval_VRtemp_support(static_registers):
        return VR_temp
    else:
        return "  "


# Evaluate VID_Setting 0x31:
def eval_vid_setting(dynamic_registers, static_registers):
    vid_setting = dynamic_registers["[REG] VID_SETTING 0x31"]
    protocol_id = static_registers["[REG] Protocol 0x05"]
    vid_converted = eval_volt_setting(vid_setting, protocol_id)
    return vid_converted


# Map the votage reg reading to an SVID table
def eval_volt_setting(vid_reg_value, protocol_reg_value):
    table = {}
    vid_converted = "0"
    if protocol_reg_value in PROTOCOL_5mV:
        table = Table_5mV
    elif protocol_reg_value in PROTOCOL_10mV:
        table = Table_10mV
    elif protocol_reg_value in PROTOCOL_IMPV9:
        table = Table_IMPV9
    else:
        table = {}
    for key, value in table.items():
        if vid_reg_value == key:
            vid_converted = table[vid_reg_value]
    return vid_converted


# ---------------------Evaluate Input Power-------------------------------------
# Evaluates pin_h register 0x1B: Normal Precision
def eval_pin_h(dynamic_registers, static_registers):
    pin_h = dynamic_registers["[REG] PIN_H 0x1B"]
    pin_max = eval_pin_max(static_registers)
    W_per_bit = static_registers["[REG] ICC_MAX_ADD 0x50"]
    if eval_pin_h_support(static_registers):
        return pin_max * ((pin_h)) / (2**8)
    else:
        return " "


# Evaluates pin_l register 0x76:  when high precition is supported
def eval_pin_l(dynamic_registers, static_registers):
    hp_support, _ = eval_hp_mode(static_registers)
    pin_max = eval_pin_max(static_registers)
    if eval_pin_h_support(static_registers) and hp_support:
        if pin_l is None:
            pin_l = dynamic_registers["[REG] PIN_L 0x76"]
        return pin_max * ((pin_l) / (2**16))
    else:
        return " "


# Evaluates Input Power Telemetry (using reg pin_h and pin_l) :
def eval_pin(static_registers, dynamic_registers, pin_h=None, pin_l=None):
    if not eval_pin_h_support(static_registers):
        return -1
    pin_max = eval_pin_max(static_registers)
    if pin_h is None:
        pin_h = dynamic_registers["[REG] PIN_H 0x1B"]
    hp_support, _ = eval_hp_mode(static_registers)
    if hp_support:
        if pin_l is None:
            pin_l = dynamic_registers["[REG] PIN_L 0x76"]
        # In HP mode, between 1-8 more bits of precision can be used
        # We are guaranteed that unused bits will be 0, so the following
        # formula will work for all these cases
        return pin_max * (((pin_h << 8) + pin_l) / (2**16))
    else:
        return pin_max * (pin_h / (2**8))


# -------------------Evaluate Output Power-------------------------------------------


# Evaluates pout_h register 0x18:
def eval_pout_h(dynamic_registers, static_registers):
    pout_h = dynamic_registers["[REG] POUT_H 0x18"]
    protocol_id = static_registers["[REG] Protocol 0x05"]
    W_per_bit = static_registers["[REG] ICC_MAX_ADD 0x50"]
    N = W_per_bit & 0x1C
    if eval_pout_h_support(static_registers):
        if protocol_id in PROTOCOL_IDS_VR14:
            pout_h = pout_h * (2 ** (N >> 2))
        # for VR13 w/ HC_ACTIVE = 1
        elif protocol_id in PROTOCOL_IDS_VR13:
            pout_h = pout_h
        else:
            pout_h = 0
    else:
        pout_h = 0
    return pout_h


# Evaluates pout_l register 0x73 when high precision is supported:
def eval_pout_l(dynamic_registers, static_registers, pout_l=None):
    hp_support, _ = eval_hp_mode(static_registers)
    W_per_bit = static_registers["[REG] ICC_MAX_ADD 0x50"]
    N = W_per_bit & 0x1C
    if pout_l is None:
        pout_l = dynamic_registers["[REG] POUT_L 0x73"]
    if eval_pout_h_support(static_registers) and hp_support:
        return (pout_l / (2**8)) * (2 ** (N >> 2))
    else:
        return " "


# ----------------Evaluate  Vout ( regs 0x16 - 0x72)-------------------
# evaluate vout_fullscale_h reg 0x0D
def eval_vout_fullscale_h(dynamic_registers):
    vout_fullscale_h = dynamic_registers["[REG] VOUT_FULLSCALE_H 0x0D"]
    vout_fs_h = (vout_fullscale_h << 8) * 0.001
    return vout_fs_h


# evaluate vout_fullscale_l reg 0x0E
def eval_vout_fullscale_l(dynamic_registers, vout_fullscale_l=None):
    if vout_fullscale_l is None:
        vout_fullscale_l = dynamic_registers["[REG] VOUT_FULLSCALE_L 0x0E"]
    vout_fs_l = vout_fullscale_l * 0.001
    return vout_fs_l


def eval_vout_fullscale(dynamic_registers):
    vout_fs = eval_vout_fullscale_h(dynamic_registers) + eval_vout_fullscale_l(
        dynamic_registers, vout_fullscale_l=None
    )
    return vout_fs


# evaluates vout_h register 0x16:
def eval_vout_h(dynamic_registers, static_registers):
    vout_h = dynamic_registers["[REG] VOUT_H 0x16"]
    fsov = eval_vout_fullscale(dynamic_registers)
    if eval_vout_h_support(static_registers):
        vout_h = fsov * (vout_h / 2**8)
        return vout_h
    else:
        return "  "


# evaluates vin_l register 0x72:
def eval_vout_l(dynamic_registers, static_registers):
    vout_l = dynamic_registers["[REG] VIN_L 0x72"]
    fsov = eval_vout_fullscale(dynamic_registers)
    hp_support, _ = eval_hp_mode(static_registers)
    if eval_vout_h_support(static_registers) and hp_support:
        vout_l = fsov * (vout_l / 2**16)
        return vout_l
    else:
        return "  "


# ------------------------- Evaluate Vin (regs 0x1A and 0x75)--------------------------
# evaluate vin_fullscale_h reg 0x0B
def eval_vin_fullscale_h(dynamic_registers):
    vin_fullscale_h = dynamic_registers["[REG] VIN_FULLSCALE_H 0x0B"]
    vin_fs_h = (vin_fullscale_h << 8) * 0.01
    return vin_fs_h


# evaluate vin_fullscale_h reg 0x0C
def eval_vin_fullscale_l(dynamic_registers, vin_fullscale_l=None):
    if vin_fullscale_l is None:
        vin_fullscale_l = dynamic_registers["[REG] VIN_FULLSCALE_L 0x0C"]
    vin_fs_l = vin_fullscale_l * 0.01
    return vin_fs_l


# evaluate Full scale Vin ( regs 0x0B - 0x0C)


def eval_vin_fullscale(dynamic_registers):
    vin_fs = eval_vin_fullscale_h(dynamic_registers) + eval_vin_fullscale_l(
        dynamic_registers, vin_fullscale_l=None
    )
    return vin_fs


# evaluates vin_h register 0x1A:
def eval_vin_h(dynamic_registers, static_registers):
    vin_h = dynamic_registers["[REG] VIN_H 0x1A"]
    fsiv = eval_vin_fullscale(dynamic_registers)
    if eval_vin_h_support(static_registers):
        vin_h = fsiv * (vin_h / 2**8)
        return vin_h
    else:
        return "  "


# evaluates vin_l register 0x75:
def eval_vin_l(dynamic_registers, static_registers):
    vin_l = dynamic_registers["[REG] VIN_L 0x75"]
    fsiv = eval_vin_fullscale(dynamic_registers)
    hp_support, _ = eval_hp_mode(static_registers)
    if eval_vin_h_support(static_registers) and hp_support:
        vin_l = fsiv * (vin_l / 2**16)
        return vin_l
    else:
        return "  "


# -----------------Evaluate Iin  value ( reg 0x19 - reg 0x74)---------------------
#   evaluate Full Scale Input Current:
def full_scale_input_current(static_registers):
    protocol_id = static_registers["[REG] Protocol 0x05"]
    IccInMax = static_registers["[REG] ICCIN_MAX 0x20"]
    Iin_Full_Scale = 0
    A_per_bit = a_per_bit_in(static_registers)
    if protocol_id in PROTOCOL_IDS_VR14:
        if eval_IccInMax_Utilized_support(static_registers) == True:
            Iin_Full_Scale = IccInMax * A_per_bit
        elif eval_IccInMax_Utilized_support(static_registers) == False:
            Iin_Full_Scale = A_per_bit * (2**8)
    elif protocol_id in PROTOCOL_IDS_VR13:
        Iin_Full_Scale = 2**8
    return Iin_Full_Scale


# evaluate A-per_bit_in[2:0] from Register 50h its[7:5]:
def a_per_bit_in(static_registers):
    A_per_bit_in = (static_registers["[REG] ICC_MAX_ADD 0x50"] & 0xE0) >> 5
    if A_per_bit_in <= 2:
        A_per_bit = 2**A_per_bit_in
    else:
        A_per_bit = 2 ** (2 - A_per_bit_in)
    return A_per_bit


# evaluates iin_h register 0x19 (normal precision):
def eval_iin_h(dynamic_registers, static_registers):
    iin = dynamic_registers["[REG] IIN_H 0x19"]
    if eval_iin_h_support(static_registers):
        Iin_full = full_scale_input_current(static_registers)
        iin_h = Iin_full * iin / 2**8
        return iin_h
    else:
        return "not supported"


# evaluates iin_l register 0x74 (high precision):
def eval_iin_l(dynamic_registers, static_registers):
    iin = dynamic_registers["[REG] IIN_L 0x74"]
    hp_support, _ = eval_hp_mode(static_registers)
    Iin_full = full_scale_input_current(static_registers)
    if eval_iin_h_support(static_registers) and hp_support:
        iin_l = Iin_full * iin / 2**16
        return iin_l


# evaluates total INPUT Current(reg19 & reg 74):
def Iin_total(dynamic_registers, static_registers):
    protocol_id = static_registers["[REG] Protocol 0x05"]
    if eval_iin_h_support(static_registers):
        if protocol_id in PROTOCOL_IDS_VR14:
            Iin_total = eval_iin_h(dynamic_registers, static_registers) + eval_iin_l(
                dynamic_registers, static_registers
            )

        elif protocol_id in PROTOCOL_IDS_VR13:
            Iin_total = eval_iin_h(dynamic_registers, static_registers)
        return Iin_total
    else:
        return " "


def add_imon_parameters(parameters):
    parameters.update(
        {
            "Load Line Resistance": {
                "Description": "Load Line resistance",
                "Units": "mOhms",
                "Default": 0.9,
                "Group": "Analysis Parameters",
                "ParameterType": ParameterType.FLOAT,
            },
            "Phase Count": {
                "Description": "Number of VR Phases",
                "Default": 6,
                "Group": "Analysis Parameters",
                "ParameterType": ParameterType.INTEGER,
                "Minimum": 1,
            },
            "Positive Voltage Tolerance": {
                "Description": "Tolerance above LL specification",
                "Units": "mV",
                "Default": 22.0,
                "Group": "Analysis Parameters",
                "ParameterType": ParameterType.FLOAT,
            },
            "Negative Voltage Tolerance": {
                "Description": "Tolerance below LL specification",
                "Units": "mV",
                "Default": 22.0,
                "Group": "Analysis Parameters",
                "ParameterType": ParameterType.FLOAT,
            },
            "HVM Positive Tolerance Margin": {
                "Description": "Decreasing tolerance below Total Positive Voltage Tolerance specification for HVM",
                "Units": "mV",
                "Default": 7.0,
                "Group": "Analysis Parameters",
                "ParameterType": ParameterType.FLOAT,
            },
            "HVM Negative Tolerance Margin": {
                "Description": "Decreasing tolerance above Total Positive Voltage Tolerance specification for HVM",
                "Units": "mV",
                "Default": 7.0,
                "Group": "Analysis Parameters",
                "ParameterType": ParameterType.FLOAT,
            },
            "IMON Topology": {
                "Description": "Target Platform Supported Topology",
                "Default": "MOSFET",
                "Group": "Analysis Parameters",
                "ParameterType": ParameterType.ENUM,
                "Options": ["MOSFET", "DCR"],
            },
            "DCR and NTC Tolerance": {
                "Description": "DCR tolerance of output inductor and thermistor tolerance "
                + "(used only in DCR mode for IMON Topology)",
                "Default": "7% DCR / 3% NTC",
                "Group": "Analysis Parameters",
                "ParameterType": ParameterType.ENUM,
                "Options": ["7% DCR / 3% NTC", "5% DCR / 1% NTC"],
            },
            "Test Rail": {
                "Description": "Rail Name for VRTT to test",
                "Group": "Test Parameters",
                "Default": "VCCIN",
            },
        }
    )


def eval_vr_version(static_registers):
    protocol_id = static_registers["[REG] Protocol 0x05"]

    if protocol_id in PROTOCOL_IDS_VR13:
        return 13
    elif protocol_id in PROTOCOL_IDS_VR14:
        return 14
    return -1


# high current support
def eval_hc_mode(static_registers):
    protocol_id = static_registers["[REG] Protocol 0x05"]
    # VR 14 Support by design
    if protocol_id in PROTOCOL_IDS_VR14:
        return True, True
    # only supported in VR13
    if protocol_id in PROTOCOL_IDS_VR13:
        support = static_registers["[REG] SLOW_SR_SEL_HC 0x2A"] & 0x80 == 0x80
        active = static_registers["[REG] SLOW_SR_SEL_HC 0x2A"] & 0x40 == 0x40
        return support, active
    return False, False


# high precision telemetry
def eval_hp_mode(static_registers):
    protocol_id = static_registers["[REG] Protocol 0x05"]
    # only supported in VR14
    if protocol_id not in PROTOCOL_IDS_VR14:
        return False, 8
    support = static_registers["[REG] VIDOMAX_H_CAPA 0x09"] & 0x08 == 0x08
    telemetry_bits = static_registers["[REG] EXP_ACCURACY 0x70"] & 0x0F
    return support, telemetry_bits


# evaluate ICCMax (reg 0x21):
def eval_iout_max(static_registers):
    # IMVP8, IMVP9, VR13 w/ HC_ACTIVE = 0 >> IccMax (0x21)
    # VR13 w/ HC_ACTIVE = 1 >> IccMax (0x21) + 2 * IccMaxAdd (VR13.HC:50h)
    # VR14 >> IccMax(21h) * 2^A_per_bit_out (VR14:50h, bits 1:0)
    #     OR
    # Just use the number from register 0x21
    protocol_id = static_registers["[REG] Protocol 0x05"]
    icc_max_reg = static_registers["[REG] ICCMAX 0x21"]
    icc_max_add_reg = static_registers["[REG] ICC_MAX_ADD 0x50"]
    hc_mode_supported, hc_mode_active = eval_hc_mode(static_registers)
    # for VR14
    if protocol_id in PROTOCOL_IDS_VR14:
        return icc_max_reg * (2 ** (icc_max_add_reg & 0x03))
    # for VR13 w/ HC_ACTIVE = 1
    elif protocol_id in PROTOCOL_IDS_VR13 and hc_mode_supported and hc_mode_active:
        return icc_max_reg + 2 * icc_max_add_reg
    else:
        return icc_max_reg


# Evaluation for register support capability REG[0x06]:


def eval_iout_h_support(static_registers):
    return static_registers["[REG] CAPABILITY 0x06"] & 0x01 == 0x01


def eval_vout_h_support(static_registers):
    return static_registers["[REG] CAPABILITY 0x06"] & 0x02 == 0x02


def eval_pout_h_support(static_registers):
    return static_registers["[REG] CAPABILITY 0x06"] & 0x04 == 0x04


def eval_iin_h_support(static_registers):
    return static_registers["[REG] CAPABILITY 0x06"] & 0x08 == 0x08


def eval_vin_h_support(static_registers):
    return static_registers["[REG] CAPABILITY 0x06"] & 0x10 == 0x10


def eval_pin_h_support(static_registers):
    return static_registers["[REG] CAPABILITY 0x06"] & 0x20 == 0x20


def eval_VRtemp_support(static_registers):
    return static_registers["[REG] CAPABILITY 0x06"] & 0x40 == 0x40


def eval_imon_iout_support(static_registers):
    return static_registers["[REG] CAPABILITY 0x06"] & 0x80 == 0x80


def eval_IccInMax_Utilized_support(static_registers):
    return static_registers["[REG] VIDOMAX_H_CAPA 0x09"] & 0x04 == 0x04


# evaluates iin_h register 0x19 (normal precision):
def eval_iin_h(dynamic_registers, static_registers):
    iin = dynamic_registers["[REG] IIN_H 0x19"]
    Iin_full = full_scale_input_current(static_registers)
    eval_iin_h_support(static_registers)
    if eval_iin_h_support(static_registers):
        iin_h = Iin_full * iin / 2**8
        return iin_h
    else:
        return "  "


########################## I Out #####################################
# evaluates iout_h register 0x15:
def eval_iout_h(dynamic_registers, static_registers, iout_h=None):
    iout_max = eval_iout_max(static_registers)
    if iout_h is None:
        iout_h = dynamic_registers["[REG] IOUT_H 0x15"]
    if eval_iout_h_support(static_registers):
        return iout_max * (iout_h / (2**8))
    else:
        return 0


# Evaluates iout_l register 0x71 (high precision):
def eval_iout_l(dynamic_registers, static_registers, iout_l=None):
    if iout_l is None:
        iout_l = dynamic_registers["[REG] IOUT_L 0x74"]
    hp_support, _ = eval_hp_mode(static_registers)
    iout_max = eval_iout_max(static_registers)
    if eval_iin_h_support(static_registers) and hp_support:
        return iout_max * (iout_l / 2**16)


# Calculates imon value (using reg iout_h and iout_l):
def eval_imon_iout(static_registers, dynamic_registers, iout_h=None, iout_l=None):
    if not eval_imon_iout_support(static_registers):
        return -1
    iout_max = eval_iout_max(static_registers)
    if iout_h is None:
        iout_h = dynamic_registers["[REG] IOUT_H 0x15"]
    hp_support, _ = eval_hp_mode(static_registers)
    if hp_support:
        if iout_l is None:
            iout_l = dynamic_registers["[REG] IOUT_L 0x71"]
        # In HP mode, between 1-8 more bits of precision can be used
        # We are guaranteed that unused bits will be 0, so the following
        # formula will work for all these cases
        return iout_max * (((iout_h << 8) + iout_l) / (2**16))
    else:
        return iout_max * (iout_h / (2**8))


def get_vout_tolerance(vid_setpoint, current, load_line_resistance, tol_neg, tol_pos):
    vout = vid_setpoint - (current * load_line_resistance)
    return vout - tol_neg, vout + tol_pos


def get_imon_iout_tolerances(parameters, static_registers, dynamic_registers=None):
    # Spec defines 6 and UP
    phaseCount = min(int(parameters["Phase Count"]["Value"]), 6)
    tol_type = parameters["DCR and NTC Tolerance"]["Value"]
    topology = parameters["IMON Topology"]["Value"]
    icc_max = eval_iout_max(static_registers)
    hp_support, hp_tele_bits = eval_hp_mode(static_registers)

    IMONAccMOSFETSensing = {
        # Phase Count {
        #   VR Load: (Integers = LSB | floats = percent) }
        # }
        6: {
            0: 0,
            5: 5,
            10: 4,
            20: 0.065,
            30: 0.045,
            40: 0.04,
            50: 0.035,
            60: 0.03,
            70: 0.03,
            80: 0.03,
            90: 0.03,
            100: 0.03,
        },
        5: {
            0: 0,
            5: 5,
            10: 4,
            20: 0.075,
            30: 0.055,
            40: 0.045,
            50: 0.04,
            60: 0.035,
            70: 0.035,
            80: 0.035,
            90: 0.035,
            100: 0.035,
        },
        4: {
            0: 0,
            5: 5,
            10: 4,
            20: 0.08,
            30: 0.06,
            40: 0.05,
            50: 0.045,
            60: 0.04,
            70: 0.04,
            80: 0.04,
            90: 0.04,
            100: 0.04,
        },
        3: {
            0: 0,
            5: 5,
            10: 4,
            20: 0.085,
            30: 0.065,
            40: 0.055,
            50: 0.05,
            60: 0.045,
            70: 0.045,
            80: 0.045,
            90: 0.045,
            100: 0.045,
        },
        2: {
            0: 0,
            5: 5,
            10: 4,
            20: 0.09,
            30: 0.075,
            40: 0.065,
            50: 0.06,
            60: 0.055,
            70: 0.055,
            80: 0.055,
            90: 0.055,
            100: 0.055,
        },
        1: {
            0: 0,
            5: 5,
            10: 4,
            20: 0.095,
            30: 0.08,
            40: 0.07,
            50: 0.065,
            60: 0.06,
            70: 0.06,
            80: 0.06,
            90: 0.06,
            100: 0.06,
        },
    }

    IMONAccDCR0p07NTC0p03Sensing = {
        # Phase Count {
        #   VR Load: (Integers = LSB | floats = percent) }
        # }
        6: {
            0: 0,
            5: 12,
            10: 12,
            20: 0.075,
            30: 0.055,
            40: 0.05,
            50: 0.045,
            60: 0.04,
            70: 0.04,
            80: 0.04,
            90: 0.04,
            100: 0.04,
        },
        5: {
            0: 0,
            5: 12,
            10: 12,
            20: 0.085,
            30: 0.065,
            40: 0.055,
            50: 0.05,
            60: 0.045,
            70: 0.045,
            80: 0.045,
            90: 0.045,
            100: 0.045,
        },
        4: {
            0: 0,
            5: 12,
            10: 12,
            20: 0.095,
            30: 0.07,
            40: 0.06,
            50: 0.055,
            60: 0.05,
            70: 0.05,
            80: 0.05,
            90: 0.05,
            100: 0.05,
        },
        3: {
            0: 0,
            5: 12,
            10: 12,
            20: 0.1,
            30: 0.085,
            40: 0.065,
            50: 0.06,
            60: 0.055,
            70: 0.055,
            80: 0.055,
            90: 0.055,
            100: 0.055,
        },
        2: {
            0: 0,
            5: 12,
            10: 12,
            20: 0.11,
            30: 0.095,
            40: 0.075,
            50: 0.07,
            60: 0.065,
            70: 0.065,
            80: 0.065,
            90: 0.065,
            100: 0.065,
        },
        1: {
            0: 0,
            5: 12,
            10: 12,
            20: 0.095,
            30: 0.08,
            40: 0.07,
            50: 0.065,
            60: 0.06,
            70: 0.06,
            80: 0.06,
            90: 0.06,
            100: 0.06,
        },
    }

    IMONAccDCR0p05NTC0p01Sensing = {
        # Phase Count {
        #   VR Load: (Integers = LSB | floats = percent) }
        # }
        6: {
            0: 0,
            5: 12,
            10: 12,
            20: 0.065,
            30: 0.045,
            40: 0.04,
            50: 0.035,
            60: 0.03,
            70: 0.03,
            80: 0.03,
            90: 0.03,
            100: 0.03,
        },
        5: {
            0: 0,
            5: 12,
            10: 12,
            20: 0.075,
            30: 0.055,
            40: 0.045,
            50: 0.04,
            60: 0.035,
            70: 0.035,
            80: 0.035,
            90: 0.035,
            100: 0.035,
        },
        4: {
            0: 0,
            5: 12,
            10: 12,
            20: 0.075,
            30: 0.06,
            40: 0.05,
            50: 0.045,
            60: 0.04,
            70: 0.04,
            80: 0.04,
            90: 0.04,
            100: 0.04,
        },
        3: {
            0: 0,
            5: 12,
            10: 12,
            20: 0.1,
            30: 0.08,
            40: 0.065,
            50: 0.055,
            60: 0.05,
            70: 0.045,
            80: 0.045,
            90: 0.045,
            100: 0.045,
        },
        2: {
            0: 0,
            5: 12,
            10: 12,
            20: 0.09,
            30: 0.075,
            40: 0.065,
            50: 0.06,
            60: 0.055,
            70: 0.055,
            80: 0.055,
            90: 0.055,
            100: 0.055,
        },
        1: {
            0: 0,
            5: 12,
            10: 12,
            20: 0.095,
            30: 0.08,
            40: 0.07,
            50: 0.065,
            60: 0.06,
            70: 0.06,
            80: 0.06,
            90: 0.06,
            100: 0.06,
        },
    }

    spec_tol = None
    if topology == "MOSFET":  # MOSFET SENSING
        return IMONAccMOSFETSensing[phaseCount]
    else:
        if tol_type == "7% DCR / 3% NTC":
            return IMONAccDCR0p07NTC0p03Sensing[phaseCount]
        elif tol_type == "5% DCR / 1% NTC":
            return IMONAccDCR0p05NTC0p01Sensing[phaseCount]


def eval_imon_iout_tolerance(
    measured_iout, parameters, static_registers, dynamic_registers
):
    # Spec defines 6 and UP
    phaseCount = min(int(parameters["Phase Count"]["Value"]), 6)
    tol_type = parameters["DCR and NTC Tolerance"]["Value"]
    topology = parameters["IMON Topology"]["Value"]
    icc_max = eval_iout_max(static_registers)
    hp_support, hp_tele_bits = eval_hp_mode(static_registers)

    IMONAccMOSFETSensing = {
        # Phase Count {
        #   VR Load: (Integers = LSB | floats = percent) }
        # }
        6: {
            5: 5,
            10: 4,
            20: 0.065,
            30: 0.045,
            40: 0.04,
            50: 0.035,
            60: 0.03,
            70: 0.03,
            80: 0.03,
            90: 0.03,
            100: 0.03,
        },
        5: {
            5: 5,
            10: 4,
            20: 0.075,
            30: 0.055,
            40: 0.045,
            50: 0.04,
            60: 0.035,
            70: 0.035,
            80: 0.035,
            90: 0.035,
            100: 0.035,
        },
        4: {
            5: 5,
            10: 4,
            20: 0.08,
            30: 0.06,
            40: 0.05,
            50: 0.045,
            60: 0.04,
            70: 0.04,
            80: 0.04,
            90: 0.04,
            100: 0.04,
        },
        3: {
            5: 5,
            10: 4,
            20: 0.085,
            30: 0.065,
            40: 0.055,
            50: 0.05,
            60: 0.045,
            70: 0.045,
            80: 0.045,
            90: 0.045,
            100: 0.045,
        },
        2: {
            5: 5,
            10: 4,
            20: 0.09,
            30: 0.075,
            40: 0.065,
            50: 0.06,
            60: 0.055,
            70: 0.055,
            80: 0.055,
            90: 0.055,
            100: 0.055,
        },
        1: {
            5: 5,
            10: 4,
            20: 0.095,
            30: 0.08,
            40: 0.07,
            50: 0.065,
            60: 0.06,
            70: 0.06,
            80: 0.06,
            90: 0.06,
            100: 0.06,
        },
    }

    IMONAccDCR0p07NTC0p03Sensing = {
        # Phase Count {
        #   VR Load: (Integers = LSB | floats = percent) }
        # }
        6: {
            5: 12,
            10: 12,
            20: 0.075,
            30: 0.055,
            40: 0.05,
            50: 0.045,
            60: 0.04,
            70: 0.04,
            80: 0.04,
            90: 0.04,
            100: 0.04,
        },
        5: {
            5: 12,
            10: 12,
            20: 0.085,
            30: 0.065,
            40: 0.055,
            50: 0.05,
            60: 0.045,
            70: 0.045,
            80: 0.045,
            90: 0.045,
            100: 0.045,
        },
        4: {
            5: 12,
            10: 12,
            20: 0.095,
            30: 0.07,
            40: 0.06,
            50: 0.055,
            60: 0.05,
            70: 0.05,
            80: 0.05,
            90: 0.05,
            100: 0.05,
        },
        3: {
            5: 12,
            10: 12,
            20: 0.1,
            30: 0.085,
            40: 0.065,
            50: 0.06,
            60: 0.055,
            70: 0.055,
            80: 0.055,
            90: 0.055,
            100: 0.055,
        },
        2: {
            5: 12,
            10: 12,
            20: 0.11,
            30: 0.095,
            40: 0.075,
            50: 0.07,
            60: 0.065,
            70: 0.065,
            80: 0.065,
            90: 0.065,
            100: 0.065,
        },
        1: {
            5: 12,
            10: 12,
            20: 0.095,
            30: 0.08,
            40: 0.07,
            50: 0.065,
            60: 0.06,
            70: 0.06,
            80: 0.06,
            90: 0.06,
            100: 0.06,
        },
    }

    IMONAccDCR0p05NTC0p01Sensing = {
        # Phase Count {
        #   VR Load: (Integers = LSB | floats = percent) }
        # }
        6: {
            5: 12,
            10: 12,
            20: 0.065,
            30: 0.045,
            40: 0.04,
            50: 0.035,
            60: 0.03,
            70: 0.03,
            80: 0.03,
            90: 0.03,
            100: 0.03,
        },
        5: {
            5: 12,
            10: 12,
            20: 0.075,
            30: 0.055,
            40: 0.045,
            50: 0.04,
            60: 0.035,
            70: 0.035,
            80: 0.035,
            90: 0.035,
            100: 0.035,
        },
        4: {
            5: 12,
            10: 12,
            20: 0.075,
            30: 0.06,
            40: 0.05,
            50: 0.045,
            60: 0.04,
            70: 0.04,
            80: 0.04,
            90: 0.04,
            100: 0.04,
        },
        3: {
            5: 12,
            10: 12,
            20: 0.1,
            30: 0.08,
            40: 0.065,
            50: 0.055,
            60: 0.05,
            70: 0.045,
            80: 0.045,
            90: 0.045,
            100: 0.045,
        },
        2: {
            5: 12,
            10: 12,
            20: 0.09,
            30: 0.075,
            40: 0.065,
            50: 0.06,
            60: 0.055,
            70: 0.055,
            80: 0.055,
            90: 0.055,
            100: 0.055,
        },
        1: {
            5: 12,
            10: 12,
            20: 0.095,
            30: 0.08,
            40: 0.07,
            50: 0.065,
            60: 0.06,
            70: 0.06,
            80: 0.06,
            90: 0.06,
            100: 0.06,
        },
    }

    spec_tol = None
    if topology == "MOSFET":  # MOSFET SENSING
        spec_tol = IMONAccMOSFETSensing[phaseCount][100]
        for vrLoad in IMONAccMOSFETSensing[phaseCount]:
            if measured_iout < vrLoad / 100 * icc_max:
                spec_tol = IMONAccMOSFETSensing[phaseCount][vrLoad]
    else:
        if tol_type == "7% DCR / 3% NTC":
            spec_tol = IMONAccDCR0p07NTC0p03Sensing[phaseCount][100]
            for vrLoad in IMONAccDCR0p07NTC0p03Sensing[phaseCount]:
                if measured_iout < vrLoad / 100 * icc_max:
                    spec_tol = IMONAccDCR0p07NTC0p03Sensing[phaseCount][vrLoad]
        elif tol_type == "5% DCR / 1% NTC":
            spec_tol = IMONAccDCR0p05NTC0p01Sensing[phaseCount][100]
            for vrLoad in IMONAccDCR0p05NTC0p01Sensing[phaseCount]:
                if measured_iout < vrLoad / 100 * icc_max:
                    spec_tol = IMONAccDCR0p05NTC0p01Sensing[phaseCount][vrLoad]

    # if spec is Least Significant Bit defined (stored as an int)
    # returning the multiple of the LSB (5 * LSB Value)
    if isinstance(spec_tol, int):
        return spec_tol * icc_max / 255
    # if spec is percent of desired iout (stored as a float)
    elif isinstance(spec_tol, float):
        return spec_tol * measured_iout
    else:
        return 0


static_registers = {
    "Protocol": 0x05,
    "ICCMAX": 0x21,
    "ICC_MAX_ADD": 0x50,
    "ICCIN_MAX": 0x20,
    "VBoot": 0x26,
    "VIDmax": 0x30,
    "CAPABILITY": 0x06,
    "EXP_ACCURACY": 0x70,
    "ALLCALL_ACT": 0x0F,  # read and record All-Call Response Register 0x0F
    "DC_LL": 0x23,
    "DC_LL_FINE": 0x36,
    "PIN_MAX": 0x2E,
    "PIN_ALERT_TH": 0x2F,
    "PIN_MAX_ADD": 0x51,
    "PIN_ALERT_TH_ADD": 0x52,
    "SLOW_SR_SEL_HC": 0x2A,
    # Custom VID Table for VID Step Voltage 0x07 and 0x08 regs
    # Contains Integer number of mV per VID step if configued as VR 14 with
    # custom VID table
    "StepSize": 0x07,
    # Contains integer number of VID steps added to VID>00 to produce final
    # voltage if configured as VR14 with custom VID table
    "BiasVIDTable": 0x08,
    # VR14-IMVP9 extended capability register for VR14/IMVP9 0x09 & 0x0A --
    # may need to be put in if clause based on ProtocolID register since
    # specified only for VR14/IMVP9
    # Extended Capability Register and MSBit of 9-bit VID+OFFSET max value
    "VIDOMAX_H_CAPA": 0x09,
    # Extended Capability Register and LSByte of 9-bit VID+OFFSET max value
    "VIDOMAX_L_CAPA": 0x0A,
    "Power State": 0x32,
    "High-Current Capability": 0x50,
    "WP_SLEW_0": 0x57,
    "WP_SLEW_1": 0x58,
    "WP_SLEW_2": 0x59,
    "WP_SLEW_TT": 0x5B,
    "WP0": 0x3A,
    "WP1": 0x3B,
    "WP2": 0x3C,
    "WP3": 0x3D,
    "PSYS_CR_LVL_H": 0x4A,
    "PSYS_W2_LVL_H": 0x4B,
    "PSYS_W1_LVL_H": 0x4C,
    "PSYSC_DBC_SET": 0x4F,
    "PSYSC_DBC_CLR": 0x49,
    "PSYS_CR_LVL_L": 0x77,
    "PSYS_W2_LVL_L": 0x78,
    "PSYS_W1_LVL_L": 0x79,
    "LASTREAD": 0x14,
    "STATUS1": 0x10,  # conveys alert# causes and VR status
    # "IOUT_L": 0x71,
    "SetVID_Fast": 0x24,
}
static_registers_to_status = ["Protocol", "ICCMAX", "ICCMAX_ADD", "VBoot"]
dynamic_registers = {
    "VR TEMP": 0x17,  # Bit6: Temperature ADC
    "PIN_H": 0x1B,
    "PIN_L": 0x76,
    "VIN_FULLSCALE_H": 0x0B,  # upper 8 bits of VIN full-scale
    "VIN_FULLSCALE_L": 0x0C,  # lower 8 bits of VIN full-scale
    "VIN_H": 0x1A,
    "VIN_L": 0x75,
    # Declaring and Reading ICC_MAX variable -- can be measured differently
    # depending on the Protocol  and register 0x2A - slow selector
    # and HC_Mode Control
    "SLOW_SR_SEL_HC": 0x2A,
    "IIN_H": 0x19,
    "IIN_L": 0x74,
    "POUT_H": 0x18,
    "POUT_L": 0x73,
    "VOUT_FULLSCALE_H": 0x0D,  # upper 8 bits of Vout full-scale
    "VOUT_FULLSCALE_L": 0x0E,  # lower 8 bits of Vout full-scale
    "VOUT_H": 0x16,
    "VOUT_L": 0x72,
    "IOUT_H": 0x15,
    "IOUT_L": 0x71,
    "STATUS1": 0x10,  # conveys alert# causes and VR status
    "STATUS2": 0x11,  # conveys SVID bus error flags
    # Temperature Zone - might need to be included in loop of test to measure
    # the VR temperature at different currents
    "TEMPERATURE_ZONE": 0x12,  # conveys alert# causes and VR status
    # PMIC GLOBAL Status -- if VR is PMIC clause may need to be supported for
    # this or maybe XX and just read the register regardless?
    "PMIC_GLOBAL_ST": 0x13,  # Indicates VR_SETTLED for across full die
    "LASTREAD": 0x14,  # Contains last value read by Get family command
    "STATUS2_LASTREAD": 0x1C,  # Copy of last read of Status Register
    "VID_SETTING": 0x31,
    "PS": 0x32,
}


def read_registers(registers, update_function=None, update_condition=None):
    data = dict()
    data_api = DataAPI()
    rail_data = None
    for register in registers:
        if rail_data is not None:
            svid_command = 0x7  # Get Reg
            data_api.SetSvidCmdWrite(
                rail_data.VRAddress,
                svid_command,
                register,
                rail_data.SVIDBus,
            )
            # time.sleep(1)
        val = data_api.GetSvidData()
        if val is not None:
            val = val.SVRData
        else:
            val = -1

        key = "[REG] {} 0x{:02X}".format(register, registers[register])

        data[key] = val

        if update_function is not None:
            if update_condition is None or update_condition(register):
                update_function("{} => VALUE 0x{:02X} ({})".format(key, val, val))

    return data


def read_registers_vectors(
    registers,
    update_function=None,
    update_condition=None,
    vr_address=None,
    svid_bus=1,
    delay=0.5,
):
    vector_api = VectorAPI()
    data_api = DataAPI()
    return_data = dict()
    registers_list = list(registers)
    batches = math.ceil(len(registers_list) / 15)
    if vr_address is not None:
        for i in range(batches):
            if delay is not None:
                time.sleep(delay)
            vector_api.ResetVectors()
            vector_api.VectorTriggerSettingsInternal(0, False)
            for idx, register in enumerate(registers_list[i * 15 : (i + 1) * 15]):
                vector_api.CreateSimpleVector(
                    idx, vr_address, SVIDCMD.GETREG, registers[register], 2
                )
            vector_api.LoadAllVectors(0, svid_bus)  # (repeats, SVID Bus)
            vector_api.ExecuteVectors(SVIDBURSTTRIGGER.INTERNAL)
            # vector_api.ReadVectorResponses()
            vResult = data_api.GetVectorDataOnce()
            for index, register in enumerate(registers_list[i * 15 : (i + 1) * 15]):
                if register is not None:
                    key = "[REG] {} 0x{:02X}".format(register, registers[register])
                    return_data[key] = vResult.DataResp[index]

                    if update_function is not None:
                        if update_condition is None or update_condition(register):
                            update_function(
                                "{} => VALUE 0x{:02X} ({})".format(
                                    key, return_data[key], return_data[key]
                                )
                            )
            vector_api.ResetVectors()
    return return_data


def read_static_registers(status_function, parameters):
    output_status("Reading {} Static Registers...", len(static_registers))
    return read_registers(
        static_registers,
        status_function,
        lambda reg: reg in static_registers_to_status,
    )


def read_static_registers_vectors(
    status_function, parameters, vr_address, svid_bus, delay=None
):
    output_status("Reading {} Static Registers...", len(static_registers))
    return read_registers_vectors(
        static_registers,
        status_function,
        lambda reg: reg in static_registers_to_status,
        vr_address,
        svid_bus,
    )


def read_dynamic_registers(parameters):
    return read_registers_vectors(dynamic_registers)


def read_dynamic_registers_vectors(parameters, vr_address=None, svid_bus=1, delay=None):
    return read_registers_vectors(
        dynamic_registers, vr_address=vr_address, svid_bus=svid_bus
    )


def get_register_reads(measurements):
    return {r: v for r, v in measurements.items() if r.startswith("[REG]")}


# convert static registers values for SVID Telemetry
def reg_conversion(addr, static_registers):
    if addr == "0x05":
        conv_val = eval_protocol(static_registers)

    elif addr == "0x21":
        conv_val = "{} A ".format(eval_iout_max(static_registers))
    elif addr == "0x2E":
        conv_val = "{} W ".format(eval_pin_max(static_registers))
    # elif addr == '0x09':
    # conv_val = "{} mV ".format(imon_helper.eval_vidoffset_max_high_cap(static_registers))
    elif addr == "0x0A":
        conv_val = "{} V ".format(eval_vidoffset_max_low_cap(static_registers))
    elif addr == "0x26":
        conv_val = "{} V ".format(eval_vboot(static_registers))
    elif addr == "0x23":
        conv_val = "{:.3f} mOhm ".format(eval_dcll(static_registers))
    elif addr == "0x36":
        conv_val = "{:.3f} mOhm ".format(eval_avp(static_registers))
    elif addr == "0x31":
        conv_val = "{} V".format(eval_vid_setting(dynamic_registers, static_registers))
    # elif addr == '0x2F':
    # conv_val = "{} W ".format(imon_helper.eval_pin_alert_th(static_registers))
    elif addr == "0x24":
        conv_val = "{:.1f} mV/us ".format(eval_setvid_fast(static_registers))
    elif addr == "0x06":
        conv_val = "[7:0]: 0b{}".format(eval_capability(static_registers))
    elif addr == "0x09":
        conv_val = "[7:0]: 0b{}".format(eval_vidomax_h_capa(static_registers))
    elif addr == "0x2A":
        conv_val = "Set Slow SR to: {}".format(eval_slow_sr_sel_hc(static_registers))

    else:
        conv_val = " "
    return conv_val


# convert dynamic registers values for SVID Telemetry.
def dynamic_reg_conversion(addr, iout, dynamic_registers, static_registers):
    for k, v in iout.items():
        if addr == "0x17":
            conv_val = (
                "{} {}".format(eval_VRtemp(dynamic_registers, static_registers), "C")
                if eval_VRtemp_support(static_registers) == 1
                else "N/A"
            )
        elif addr == "0x31":
            conv_val = "{} V".format(
                eval_vid_setting(dynamic_registers, static_registers)
            )
        elif addr == "0x1B":
            conv_val = (
                "{:.2f} {} ".format(
                    eval_pin_h(dynamic_registers, static_registers), "W"
                )
                if eval_pin_h_support(static_registers) == 1
                else "N/A"
            )
        elif addr == "0x76":
            conv_val = (
                "{} {}".format(eval_pin_l(dynamic_registers, static_registers), "W")
                if eval_hp_mode(static_registers) == 1
                else "N/A"
            )
        elif addr == "0x1A":
            conv_val = (
                "{:.2f} {} ".format(
                    eval_vin_h(dynamic_registers, static_registers), "V"
                )
                if eval_vin_h_support(static_registers) == 1
                else "N/A"
            )
        elif addr == "0x75":
            conv_val = (
                "{} {}".format(eval_vin_l(dynamic_registers, static_registers), "V")
                if eval_hp_mode(static_registers) == 1
                else "N/A"
            )
        elif addr == "0x16":
            conv_val = (
                "{:.2f} {} ".format(
                    eval_vout_h(dynamic_registers, static_registers), "V"
                )
                if eval_vout_h_support(static_registers) == 1
                else "N/A"
            )
        elif addr == "0x72":
            conv_val = (
                "{} {}".format(eval_vout_l(dynamic_registers, static_registers), "V")
                if eval_hp_mode(static_registers) == 1
                else "N/A"
            )

        elif addr == "0x0B":
            conv_val = "{} {} ".format(eval_vin_fullscale_h(dynamic_registers), "V")
        elif addr == "0x0C":
            conv_val = "{} {}".format(eval_vin_fullscale_l(dynamic_registers), "V")
        elif addr == "0x0D":
            conv_val = "{} {} ".format(eval_vout_fullscale_h(dynamic_registers), "V")
        elif addr == "0x0E":
            conv_val = "{} {}".format(eval_vout_fullscale_l(dynamic_registers), "V")

        elif addr == "0x19":
            conv_val = (
                "{:.2f} A ".format(eval_iin_h(dynamic_registers, static_registers))
                if eval_iin_h_support(static_registers)
                else "N/A"
            )
        elif addr == "0x74":
            conv_val = (
                "{:.2f} {}".format(eval_iin_l(dynamic_registers, static_registers), "A")
                if eval_hp_mode(static_registers) == 1
                else "N/A"
            )
        elif addr == "0x15":
            conv_val = "{:.2f} A ".format(
                eval_iout_h(dynamic_registers, static_registers)
            )
        elif addr == "0x71":
            conv_val = (
                "{} {}".format(eval_iout_l(dynamic_registers, static_registers), "A")
                if eval_hp_mode(static_registers) == 1
                else "N/A"
            )
        elif addr == "0x18":
            conv_val = (
                "{:.2f} {} ".format(
                    eval_pout_h(dynamic_registers, static_registers), "W"
                )
                if eval_pout_h_support(static_registers) == 1
                else "N/A"
            )
        elif addr == "0x73":
            conv_val = (
                "{} {}".format(eval_pout_l(dynamic_registers, static_registers), "W")
                if eval_hp_mode(static_registers) == 1
                else "N/A"
            )
        # elif addr == '0x15':
        # conv_val = "{} ".format(eval_iout_h(dynamic_registers, static_registers))
        else:
            conv_val = "  "
        return conv_val
