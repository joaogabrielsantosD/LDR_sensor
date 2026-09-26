import os
import serial
import time
import csv
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime

SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 9600
LOGS_FOLDER = 'logs'

class SerialApplication:
    def __init__(self, root):
        self.root = root
        self.root.title("Serial Monitor with Tkinter")
        self.root.geometry("650x550")

        self.connection = None
        self.is_running = False
        
        # Lock to prevent simultaneous writes or conflicts when changing active log files
        self.file_lock = threading.Lock()
        
        # Logs directory setup
        self.logs_folder = LOGS_FOLDER
        if not os.path.exists(self.logs_folder):
            os.makedirs(self.logs_folder)

        # Default counter and initial filename
        self.file_counter = 0
        self.current_filename = f"data_serial{self.file_counter}.csv"

        self._create_ui()
        self._start_serial()

    def _create_ui(self):
        # Log File Management Frame
        file_frame = ttk.LabelFrame(self.root, text="Log File Manager")
        file_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(file_frame, text="Current File:").grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.filename_entry = ttk.Entry(file_frame, width=25)
        self.filename_entry.grid(row=0, column=1, padx=5, pady=5)
        self.filename_entry.insert(0, self.current_filename)

        apply_name_btn = ttk.Button(file_frame, text="Apply New Name", command=self.change_filename)
        apply_name_btn.grid(row=0, column=2, padx=5, pady=5)

        next_log_btn = ttk.Button(file_frame, text="Create Next Log (Auto)", command=self.create_next_log)
        next_log_btn.grid(row=0, column=3, padx=5, pady=5)

        # Send Data Frame
        send_frame = ttk.LabelFrame(self.root, text="Send Data (adds \\n automatically)")
        send_frame.pack(fill="x", padx=10, pady=5)

        self.send_entry = ttk.Entry(send_frame)
        self.send_entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        self.send_entry.bind("<Return>", lambda event: self.send_data())

        send_btn = ttk.Button(send_frame, text="Send", command=self.send_data)
        send_btn.pack(side="right", padx=5, pady=5)

        # Received Data / Log View Frame
        data_frame = ttk.LabelFrame(self.root, text="Received Data")
        data_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.text_area = scrolledtext.ScrolledText(data_frame, state='disabled', wrap='word')
        self.text_area.pack(fill="both", expand=True, padx=5, pady=5)

    def _ensure_csv_header(self, full_path):
        """Creates the CSV file in the logs folder with a header if it does not exist."""
        if not os.path.exists(full_path):
            with open(full_path, mode='w', newline='', encoding='utf-8') as file:
                csv.writer(file).writerow(['timestamp', 'data'])

    def change_filename(self):
        """Manually sets the target .csv filename."""
        new_name = self.filename_entry.get().strip()
        if not new_name:
            messagebox.showwarning("Warning", "Filename cannot be empty.")
            return

        if not new_name.endswith('.csv'):
            new_name += '.csv'

        with self.file_lock:
            self.current_filename = new_name
            full_path = os.path.join(self.logs_folder, self.current_filename)
            self._ensure_csv_header(full_path)

        self.log_message(f"[SYSTEM] Destination file changed to: {full_path}\n")

    def create_next_log(self):
        """Increments counter and automatically switches to data_serialX.csv."""
        self.file_counter += 1
        new_name = f"data_serial{self.file_counter}.csv"

        self.filename_entry.delete(0, tk.END)
        self.filename_entry.insert(0, new_name)
        
        self.change_filename()

    def _start_serial(self):
        try:
            self.connection = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            time.sleep(2)
            self.log_message(f"[SYSTEM] Connected to {SERIAL_PORT} at {BAUD_RATE} baud.\n")

            # Ensure initial file exists in logs folder
            initial_path = os.path.join(self.logs_folder, self.current_filename)
            self._ensure_csv_header(initial_path)

            # Start reading thread
            self.is_running = True
            self.read_thread = threading.Thread(target=self._read_serial, daemon=True)
            self.read_thread.start()

        except serial.SerialException as e:
            messagebox.showerror("Serial Error", f"Could not open port {SERIAL_PORT}:\n{e}")

    def send_data(self):
        """Sends typed text over serial with '\\n' attached at the end."""
        data = self.send_entry.get()
        if data and self.connection and self.connection.is_open:
            message = (data + '\n').encode('utf-8')
            self.connection.write(message)
            
            self.log_message(f"[SENT] {data}\n")
            self.send_entry.delete(0, tk.END)

    def _read_serial(self):
        """Background thread reading incoming data and writing to active CSV file."""
        while self.is_running and self.connection and self.connection.is_open:
            try:
                if self.connection.in_waiting > 0:
                    line = self.connection.readline().decode('utf-8', errors='replace').rstrip()
                    if line:
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                        # Save to active CSV inside /logs folder
                        with self.file_lock:
                            file_path = os.path.join(self.logs_folder, self.current_filename)
                            with open(file_path, mode='a', newline='', encoding='utf-8') as file:
                                csv.writer(file).writerow([timestamp, line])

                        self.log_message(f"[{timestamp}] {line}\n")
            except Exception as e:
                self.log_message(f"[READ ERROR] {e}\n")
                break

    def log_message(self, message):
        """Appends output message to the text console widget."""
        self.text_area.config(state='normal')
        self.text_area.insert(tk.END, message)
        self.text_area.see(tk.END)
        self.text_area.config(state='disabled')

    def close(self):
        self.is_running = False
        if self.connection and self.connection.is_open:
            self.connection.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = SerialApplication(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()