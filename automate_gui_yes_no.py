import os
import tkinter as tk
from tkinter import ttk
import time
from console_app import (
    error_out_if,
    output_measurement,
    output_named_measurement,
    output_status,
    prompt,
    output_err
)

class YesNoDialog:
    def __init__(self, title, message):
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry("400x200")
        self.root.resizable(False, False)

        self.message_label = ttk.Label(self.root, text=message, wraplength=380)
        self.message_label.pack(pady=20)

        self.button_frame = ttk.Frame(self.root)
        self.button_frame.pack(pady=10)

        self.yes_button = ttk.Button(self.button_frame, text="Yes", command=self.yes)
        self.yes_button.pack(side=tk.LEFT, padx=10)

        self.no_button = ttk.Button(self.button_frame, text="No", command=self.no)
        self.no_button.pack(side=tk.LEFT, padx=10)
        

        self.result = None

    def yes(self):
        self.result = True
        self.root.destroy()
        
        return self.result

    def no(self):
        self.result = False
        self.root.destroy()

        return self.result

    def show(self):
        self.root.mainloop()
        return self.result
    
