import tkinter as tk
from tkinter import ttk
import threading
import queue

class NotificationWindow:
    def __init__(self):
        self.root = None
        self.message_queue = queue.Queue()
        self.notification_window = None
        self.label = None
        
        # Initialize Tkinter in a separate thread
        self.init_thread = threading.Thread(target=self._initialize_tk)
        self.init_thread.daemon = True
        self.init_thread.start()

    def _initialize_tk(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.create_persistent_notification()
        self.check_messages()
        self.root.mainloop()
    
    def create_persistent_notification(self):
        if not self.root:
            return
        self.notification_window = tk.Toplevel(self.root)
        self.notification_window.withdraw()
        self.notification_window.attributes('-topmost', True)
        self.notification_window.overrideredirect(True)
        
        # Create styled frame
        style = ttk.Style()
        style.configure('Notification.TFrame', background='#f0f0f0')
        frame = ttk.Frame(self.notification_window, style='Notification.TFrame', padding=10)
        frame.pack(fill='both', expand=True)
        
        # Create message label that we'll update later
        self.label = ttk.Label(frame, text="", wraplength=300)
        self.label.pack(padx=5, pady=5)
        
        # Position window at bottom right
        self.position_window()
        
    def position_window(self):
        if not self.notification_window:
            return
        self.notification_window.update_idletasks()
        screen_width = self.notification_window.winfo_screenwidth()
        screen_height = self.notification_window.winfo_screenheight()
        window_width = self.notification_window.winfo_width()
        window_height = self.notification_window.winfo_height()
        
        x = screen_width - window_width - 20
        y = screen_height - window_height - 40
        
        self.notification_window.geometry(f'+{x}+{y}')
        self.notification_window.deiconify()
            
    def check_messages(self):
        if not self.root:
            return
        try:
            while not self.message_queue.empty():
                message = self.message_queue.get_nowait()
                self.update_notification(message)
        finally:
            if self.root:
                self.root.after(100, self.check_messages)
    
    def update_notification(self, message):
        if self.label:
            self.label.configure(text=message)
            self.position_window()  # Reposition in case message size changed

    def show_notification(self, message):
        self.message_queue.put(message)