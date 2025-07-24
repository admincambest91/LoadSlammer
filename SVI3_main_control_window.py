import time
import json
import pyautogui
from pywinauto import Application


class SVI3Controller:
    """
    A helper class to automate the SVI3 application using pywinauto for window control
    and pyautogui for coordinate-based interactions.
    Coordinates for elements (e.g., VID, QuickView) are stored in a JSON file.
    """
    def __init__(self, title: str = "SVI3", backend: str = "uia", coords_file: str = "SVI3_coordinate.json"):
        self.title = title
        self.backend = backend
        self.coords_file = coords_file
        self.app = None
        self.dlg = None
        self.coords = {}
        self.load_coords()

    def load_coords(self):
        """
        Loads coordinates from the JSON file into self.coords.
        Expected format:
        {
          "VID": {"x": 296, "y": 141},
          "QuickView": {"x": 100, "y": 50},
          ...
        }
        """
        try:
            with open(self.coords_file, 'r', encoding='utf-8') as f:
                self.coords = json.load(f)
        except FileNotFoundError:
            # Initialize empty or default structure
            self.coords = {}

    def save_coords(self, coords: dict = None):
        """
        Saves given coords dict (or self.coords) into the JSON file.

        :param coords: dict of element names to {x:int, y:int}
        """
        data = coords if coords is not None else self.coords
        with open(self.coords_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def initialize(self):
        """
        Connects to the running SVI3 app, restores and maximizes the window, and brings it to focus.
        """
        time.sleep(1)
        self.app = Application(backend=self.backend).connect(title=self.title)
        self.dlg = self.app.window(title=self.title, visible_only=False)

        self.dlg.restore()
        self.dlg.maximize()
        self.dlg.set_focus()
        time.sleep(0.5)

    def click(self, element: str):
        """
        Clicks at the coordinates for the given element name.

        :param element: key in self.coords (e.g., "VID")
        """
        x, y = self.get_coords(element)
        pyautogui.click(x, y)
        time.sleep(0.1)

    def key_in_value(self, element: str, value: str, confirm_key: str = 'enter'):
        """
        Clicks into the edit field at element coords, clears existing text,
        types a new value, and optionally confirms.

        :param element: key in self.coords (e.g., "VID")
        :param value: The string to type
        :param confirm_key: Key to press after typing
        """
        x, y = self.get_coords(element)
        pyautogui.click(x, y)
        time.sleep(0.05)

        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.05)
        pyautogui.press('backspace')

        pyautogui.write(value, interval=0.05)
        if confirm_key:
            pyautogui.press(confirm_key)
        time.sleep(0.1)

    def get_coords(self, element: str):
        """
        Returns the (x, y) coordinate list for the given element name.

        :param element: key in self.coords (e.g., "VDDIO")
        :return: [x, y]
        """
        if element not in self.coords:
            raise ValueError(f"No coordinates stored for element '{element}'")
        coord = self.coords[element]
        return [coord['x'], coord['y']]

    def minimize(self):
        """
        Minimizes the SVI3 window.
        """
        if self.dlg:
            self.dlg.minimize()
    
    def maximize(self):
        """
        Minimizes the SVI3 window.
        """
        if self.dlg:
            self.dlg.restore()
            self.dlg.maximize()
            self.dlg.set_focus()


if __name__ == '__main__':
    # Example JSON structure
    default_coords = {
        "VDDR_CPU0": {"x": 578, "y":  60},
        "VDDR_SOC" : {"x": 652, "y":  61},
        "VDDIO"    : {"x": 710, "y":  61},
        "VID"      : {"x": 296, "y": 141}
    }
    # # Save defaults to file
    # with open('svi3_coords.json', 'w', encoding='utf-8') as f:
    #     json.dump(default_coords, f, indent=2)
    # print("Default coordinates saved to svi3_coords.json")

    # Load and test get_coords
    controller = SVI3Controller()
    coords = controller.get_coords('VDDIO')
    print(f"VDDIO[0] = {coords[0]}, VDDIO[1] = {coords[1]}")

    # Initialize and interact
    controller.initialize()
    controller.click('VDDR_CPU0')
    controller.key_in_value('VID', '1.0V')
    controller.click('Set_VID')
    controller.minimize()
