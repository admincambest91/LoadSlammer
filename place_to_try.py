import openpyxl
import json
import sys
from openpyxl.cell.cell import MergedCell

CPU0_SOC_mainsheet="C:\\Users\\HPS Penang Tester\\Documents\\python\Load_slammer\\LoadSlammer_Testplan\\SP5_CPU_SVI3_VDDCRCPU0_VDDCRSOC_Analysis_V0_2.xlsm"

def get_merged_cell_value(sheet, row, col):
    cell = sheet.cell(row=row, column=col)
    if not isinstance(cell, MergedCell):
        return cell.value
    for merged_range in sheet.merged_cells.ranges:
        if cell.coordinate in merged_range:
            top_left = sheet.cell(row=merged_range.min_row, column=merged_range.min_col)
            return top_left.value
    return None

def extract_votf_data(excel_path: str,
                      sheet_name: str = "VOTF_Timing",
                      json_path: str = "votf_data.json") -> None:
    """
    Reads the specified VOTF worksheet and writes out a JSON file where each
    Test Case is a key mapping to its PSI Mode, IDD Set, Old VID, and Target VID.
    Handles merged Test Case cells by carrying forward the last non-empty value.

    :param excel_path: Path to the input Excel (.xlsx/.xlsm) file
    :param sheet_name: Name of the worksheet to process (default: "VOTF")
    :param json_path: Path to output JSON file (default: "votf_data.json")
    """
    # Load workbook and worksheet
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    if sheet_name not in wb.sheetnames:
        raise ValueError(f"Worksheet '{sheet_name}' not found in {excel_path}")
    ws = wb[sheet_name]

    # Locate header row (where first cell == 'Test Case')
    header_row = None
    for row in ws.iter_rows(min_row=1, max_row=20):
        if row[0].value and str(row[0].value).strip() == "Test Case":
            header_row = row[0].row
            break
    if header_row is None:
        raise ValueError("Header row with 'Test Case' not found.")

    data = {}
    current_tc = None
    # Iterate rows below header; values_only=True returns plain Python types
    for row in ws.iter_rows(min_row=header_row+1,
                            min_col=1, max_col=5,
                            values_only=True):
        tc, psi_mode, idd_set, old_vid, target_vid = row
        
        # If this row has a new Test Case value, remember it
        # if tc is None:
        #     cell = ws.cell(row=tc.row, column=tc.column)
        #     if isinstance(cell,MergedCell):
        #         current_tc=get_merged_cell_value(ws,tc.row,tc.column)
        # else:
        #     cell = ws.cell(row=tc.row, column=tc.column)
        #     if isinstance(cell,MergedCell):
        #         current_tc=get_merged_cell_value(ws,tc.row,tc.column)
            
        
        data[current_tc] = {
            "PSI Mode":       psi_mode,
            "IDD Set (A)":    idd_set,
            "Old VID (mV)":   old_vid,
            "Target VID (mV)": target_vid
        }
    # Write JSON output
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"Extracted {len(data)} test cases to {json_path}")


if __name__ == '__main__':
    args = sys.argv[1:]
    excel_file = args[0] if len(args) > 0 else CPU0_SOC_mainsheet
    sheet = args[1] if len(args) > 1 else 'VOTF_Timing'
    out_json = args[2] if len(args) > 2 else 'votf_data.json'
    extract_votf_data(excel_file, sheet, out_json)
