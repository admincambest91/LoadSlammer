from time import sleep
from pywinauto import Application
from pywinauto.findwindows import ElementNotFoundError
import sys
import io
import json
import re
import os # Import os for path handling

# Define constants for better readability and easier modification
# It's good practice to keep paths or configuration outside the main class
# or load them from a config file.
LOADSLAMMER_EXE_PATH = r"C:\Program Files (x86)\LoadSlammer\LoadSlammer.exe"
LOADSLAMMER_TITLE = "LoadSlammer"
CONTROL_IDENTIFIER_FILE = "C:\\Users\\HPS Penang Tester\\Documents\\python\\control_identifier.txt"

# ---

class LoadSlammerController:
    """
    A class to encapsulate interactions with the LoadSlammer application
    for test automation purposes.
    """

    def __init__(self, backend="uia", timeout=15):
        """
        Initializes the LoadSlammerController.
        Args:
            backend (str): The pywinauto backend to use ('uia' or 'win32').
            timeout (int): The maximum time to wait for the application to connect.
        """
        self.app = None  # pywinauto Application object
        self.main_window = None  # pywinauto main window object (dlg)
        self.backend = backend
        self.timeout = timeout
        print("LoadSlammerController initialized with backend: {}, timeout: {}s".format(self.backend,self.timeout))
    
    
    def connect_to_app(self, start_if_not_running=True):
        """
        Connects to the LoadSlammer application.
        Args:
            start_if_not_running (bool): If True, attempts to start the app
                                         if it's not already running.
        Returns:
            bool: True if connection is successful, False otherwise.
        """
        try:
            # Try to connect to an already running instance
            print("Attempting to connect to existing {} application...".format(LOADSLAMMER_TITLE))

            self.app = Application(backend=self.backend).connect(
                title=LOADSLAMMER_TITLE, timeout=self.timeout
            )
            print("Successfully connected to existing LoadSlammer application.")

        except ElementNotFoundError:
            if start_if_not_running:
                print("{} not found. Attempting to start it...".format(LOADSLAMMER_TITLE))
                try:
                    self.app = Application(backend=self.backend).start(
                        LOADSLAMMER_EXE_PATH, timeout=self.timeout
                    ).connect(title=LOADSLAMMER_TITLE, timeout=self.timeout)
                    print("Successfully started and connected to LoadSlammer application.")
                except Exception as e:
                    print("Failed to start LoadSlammer application: {}".format(e))
                    return False
            else:
                print(f"'{LOADSLAMMER_TITLE}' not found and 'start_if_not_running' is False.")
                return False
        except Exception as e:
            print(f"An unexpected error occurred during connection: {e}")
            return False

        # Once connected/started, get the main window
        try:
            self.main_window = self.app.top_window()
            self.main_window.wait('ready', timeout=5) # Wait for the window to be ready
            self.main_window.maximize()
            print("LoadSlammer main window found and maximized.")
            return True
        except Exception as e:
            print("Could not get or maximize the main window: {}".format(e))
            return False

    def print_all_control_identifiers(self, filename=CONTROL_IDENTIFIER_FILE):
        """
        Prints all control identifiers of the main window to a specified file.
        This is useful for debugging and identifying controls.
        Args:
            filename (str): The path to the file where identifiers will be saved.
        """
        if self.main_window:
            print("Saving control identifiers to: {}".format(os.path.abspath(filename)))
            self.main_window.print_control_identifiers(filename=filename)
        else:
            print("No main window connected to print identifiers.")

    def _get_child_control(self, **kwargs):
        """
        Internal helper method to get a child control safely.
        Args:
            **kwargs: Keyword arguments to pass to child_window (e.g., title, control_type).
        Returns:
            pywinauto.base_wrapper.BaseWrapper or None: The wrapper object of the control, or None if not found.
        """
        if not self.main_window:
            print("Error: Main window not connected. Cannot find child control.")
            return None
        try:
            # Use **kwargs to dynamically pass arguments like title, control_type, auto_id
            control = self.main_window.child_window(**kwargs).wrapper_object() 
            return control
        except ElementNotFoundError as e:
            print("Error: Could not find child control with criteria {}. Details: {}".format(kwargs,e))
            return None
        except Exception as e:
            print("An unexpected error occurred while finding control {}: {}".format(kwargs,e))
            return None

    def click_add_device_button(self):
        """Clicks the 'Add Device' button."""
        print("Attempting to click 'Add Device' button...")
        add_device_button = self._get_child_control(
            title="addToolStripButton",
            control_type="Button"
        )
        if add_device_button:
            add_device_button.click_input()
            print("'Add Device' button clicked.")
            sleep(1) # Small delay for UI to react
            return True
        return False

    def click_connect_button(self):
        """Clicks the 'Connect' button in the 'Select Device' dialog (or main window)."""
        print("Attempting to click 'Connect' button...")
        # Assuming the "Connect" button appears in the main window after clicking 'Add Device'
        # or it's a direct child of the main window. If it's a new dialog, you'd need
        # to connect to that new dialog first.
        connect_button = self._get_child_control(
            title="Connect",
            auto_id="bConnect",
            control_type="Button"
        )
        if connect_button:
            connect_button.click_input()
            print("'Connect' button clicked.")
            sleep(1) # Small delay for UI to react
            return True
        return False

    def close_app(self):
        """Closes the LoadSlammer application."""
        if self.main_window:
            print("Attempting to close LoadSlammer application.")
            self.main_window.close()
            self.app.wait_process_finish(self.timeout) # Wait for the process to terminate
            print("LoadSlammer application closed.")
        else:
            print("No LoadSlammer application to close.")

# ---
# Main Execution / Test Automation Flow (example of how to use the class)
# ---

if __name__ == "__main__":
    print("Starting LoadSlammer automation script...")

    # Instantiate your controller
    loadslammer_app = LoadSlammerController()

    try:
        # Step 1: Connect to the application
        if not loadslammer_app.connect_to_app(start_if_not_running=True):
            print("Failed to connect to LoadSlammer. Exiting.")
            sys.exit(1) # Exit if connection fails

        # Optional: Print identifiers for debugging
        # loadslammer_app.print_all_control_identifiers()

        # Step 2: Perform actions
        if not loadslammer_app.click_add_device_button():
            print("Failed to click 'Add Device' button. Aborting test.")
            # Optionally add more cleanup or error handling here
            loadslammer_app.close_app()
            sys.exit(1)

        # Step 3: Click connect (assuming it appears after add_device click)
        if not loadslammer_app.click_connect_button():
            print("Failed to click 'Connect' button. Aborting test.")
            loadslammer_app.close_app()
            sys.exit(1)

        print("\nLoadSlammer automation sequence completed successfully!")

    except Exception as e:
        print(f"\nAn unhandled error occurred during automation: {e}")
    finally:
        # Step 4: Ensure the application is closed
        loadslammer_app.close_app()
        print("Automation script finished.")