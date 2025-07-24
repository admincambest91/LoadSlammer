from time import sleep
from pywinauto import Application, Desktop
from pywinauto.findwindows import ElementNotFoundError
from pywinauto.keyboard import send_keys
import sys
import os

# Configurable constants
LOADSLAMMER_EXE_PATH = r"C:\Program Files (x86)\LoadSlammer GUI\Blaster\LoadSlammerGUI.exe"
LOADSLAMMER_TITLE = "LoadSlammer"
CONTROL_IDENTIFIER_FILE = r"C:\Users\HPS Penang Tester\Documents\python\Load_slammer\LS_control_identifier.txt"

class LoadSlammerController:
    def __init__(self, backend="uia", timeout=15):
        self.app = None
        self.main_window = None
        self.backend = backend
        self.timeout = timeout
        print(f"LoadSlammerController initialized with backend: {self.backend}, timeout: {self.timeout}s")

    def connect_to_app(self, start_if_not_running=True):
        try:
            print(f"Attempting to connect to existing {LOADSLAMMER_TITLE} application...")
            self.app = Application(backend=self.backend).connect(title_re=f".*{LOADSLAMMER_TITLE}.*", timeout=self.timeout)
            print("Successfully connected to existing LoadSlammer application.")
        except ElementNotFoundError:
            if start_if_not_running:
                print(f"{LOADSLAMMER_TITLE} not found. Attempting to start it...")
                try:
                    self.app = Application(backend=self.backend).start(LOADSLAMMER_EXE_PATH)
                    self.app.connect(title_re=f".*{LOADSLAMMER_TITLE}.*", timeout=self.timeout)
                    print("Successfully started and connected to LoadSlammer application.")
                except Exception as e:
                    print(f"Failed to start LoadSlammer application: {e}")
                    return False
            else:
                print(f"'{LOADSLAMMER_TITLE}' not found and 'start_if_not_running' is False.")
                return False
        except Exception as e:
            print(f"Unexpected error: {e}")
            return False

        try:
            self.main_window = Desktop(backend=self.backend).window(title_re=f".*{LOADSLAMMER_TITLE}.*")
            self.main_window.wait("visible", timeout=5)
            self.main_window.set_focus()

            if not self.main_window.is_maximized():
                self.main_window.maximize()
                print("Main window maximized.")
            else:
                print("Main window already maximized.")
            return True
        except Exception as e:
            print(f"Could not get or maximize the main window: {e}")
            return False

    def maximize(self):
        if self.main_window:
            self.main_window.restore()
            self.main_window.maximize()
            self.main_window.set_focus()

    def minimize(self):
        if self.main_window:
            self.main_window.minimize()

    def print_all_control_identifiers(self, filename=CONTROL_IDENTIFIER_FILE):
        if self.main_window:
            print(f"Saving control identifiers to: {os.path.abspath(filename)}")
            self.main_window.print_control_identifiers(filename=filename)
        else:
            print("No main window connected to print identifiers.")

    def _get_child_control(self, **kwargs):
        if not self.main_window:
            print("Error: Main window not connected. Cannot find child control.")
            return None
        try:
            return self.main_window.child_window(**kwargs).wrapper_object()
        except ElementNotFoundError as e:
            print(f"Control not found: {kwargs} — {e}")
            return None
        except Exception as e:
            print(f"Error getting control {kwargs}: {e}")
            return None

    def slam(self):
        print("Turning on current...")
        slam = self._get_child_control(title="Slam", control_type="Button")
        if slam:
            slam.click_input()
            sleep(1.5)
            return True
        return False

    def stop(self):
        print("Turning off current...")
        stop = self._get_child_control(title="Stop", control_type="Button")
        if stop:
            stop.click_input()
            return True
        return False

    def change_rail(self, rail_name):
        print(f"Changing to test rail: {rail_name}")
        try:
            open_btn = self._get_child_control(best_match="OpenButton2", control_type="Button")
            if open_btn:
                open_btn.click_input()

            rail_item = self._get_child_control(title=rail_name, control_type="ListItem")
            if rail_item:
                rail_item.click_input()

            print(f"Rail set to {rail_name}")
            return True
        except Exception as e:
            print(f"Could not set rail: {e}")
            return False

    def adjust_test_current(self, current):
        print(f"Setting test current to {current}A")
        tdc_row = self._get_child_control(title="TDC", control_type="DataItem")
        if tdc_row:
            tdc_row.click_input()
            send_keys('^a{BACKSPACE}')
            send_keys(str(current))
            send_keys('{ENTER}')
            return True
        return False

    def close_app(self):
        if self.main_window:
            print("Attempting to close LoadSlammer application...")
            # self.main_window.close()  # Optional: uncomment to force close
            self.app.wait_process_finish(self.timeout)
            print("LoadSlammer application closed.")
        else:
            print("No LoadSlammer application to close.")

# --- Main Script ---
if __name__ == "__main__":
    print("Starting LoadSlammer automation script...")

    loadslammer_app = LoadSlammerController()

    try:
        if not loadslammer_app.connect_to_app(start_if_not_running=True):
            sys.exit("❌ Failed to connect to LoadSlammer.")

        if not loadslammer_app.change_rail("VDDCR_CPU0"):
            loadslammer_app.close_app()
            sys.exit("❌ Failed to change rail.")

        if not loadslammer_app.adjust_test_current(5):
            loadslammer_app.close_app()
            sys.exit("❌ Failed to set test current.")

        if not loadslammer_app.slam():
            loadslammer_app.close_app()
            sys.exit("❌ Failed to slam (start current).")

        if not loadslammer_app.stop():
            loadslammer_app.close_app()
            sys.exit("❌ Failed to stop current.")

        print("✅ LoadSlammer automation sequence completed successfully!")

    except Exception as e:
        print(f"\n❗Unhandled error: {e}")
    finally:
        loadslammer_app.close_app()
        print("Automation script finished.")
