import openpyxl
from time import sleep
from openpyxl.cell.cell import MergedCell
import json

CPU0_SOC_mainsheet="C:\\Users\\HPS Penang Tester\\Documents\\python\Load_slammer\\LoadSlammer_Testplan\\SP5_CPU_SVI3_VDDCRCPU0_VDDCRSOC_Analysis_V0_2.xlsm"
#CPU1_VDDIO_mainsheet="C:\\Users\\HPS Penang Tester\\Documents\\python\\Load_slammer\\LoadSlammer_Testplan\\SP5_CPU_SVI3_VDDCRCPU1_VDDIO_ Analysis_V0_2.xlsm"


class JSON_excel_extractor:
    def __init__(self, JSON_file,excel_path: str, sheet_name: str = "VOTF_Timing"):
        self.excel_path = excel_path
        self.sheet_name = sheet_name
        self.json=JSON_file
        self.workbook = None
        self.sheet = None

    def load_workbook(self):
        print(f"Loading workbook: {self.excel_path}")
        self.workbook = openpyxl.load_workbook(self.excel_path, data_only=True)
        self.sheet = self.workbook[self.sheet_name]
        print(f"Workbook loaded, using sheet: {self.sheet_name}")
        return self.workbook, self.sheet

    def load_json_file(self):
        with open(self.json, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    

if __name__ == "__main__":
    extractor=JSON_excel_extractor("CPU0_SOC_votf_parameter.json",CPU0_SOC_mainsheet)
    json_data=extractor.load_json_file()
    wb,sheet=extractor.load_workbook()
    sleep(1)
