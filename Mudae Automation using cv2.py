import cv2
import numpy as np
import pyautogui
import time
import random
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import threading
import json
import os


class MudaeInstance:
    def __init__(self, name, chat_region, w_interval, rolls_interval):
        self.name = name
        self.chat_region = chat_region
        self.w_interval = w_interval
        self.rolls_interval = rolls_interval
        self.last_w_time = 0
        self.last_rolls_time = 0
        self.running = False
        self.paused = False
       
    def to_dict(self):
        return {
            'name': self.name,
            'chat_region': self.chat_region,
            'w_interval': self.w_interval,
            'rolls_interval': self.rolls_interval
        }
   
    @classmethod
    def from_dict(cls, data):
        return cls(
            data['name'],
            data['chat_region'],
            data['w_interval'],
            data['rolls_interval']
        )

class MudaeMultiAutomation:
    def __init__(self):
        self.instances = {}
        self.automation_threads = {}
        self.config_file = "mudae_instances.json"
        self.pyautogui_lock = threading.Lock() 
        self.retry_attempts = 3  # New: Default retry attempts
        self.command_delay = 0.2  # New: Default command delay (seconds)
       
        # Region selection variables
        self.selection_start = None
        self.selection_end = None
        self.selection_rect = None
       
        # Setup GUI first
        self.setup_gui()
       
        # Load saved instances after GUI is ready
        self.load_instances()
       
    def setup_gui(self):
        self.root = tk.Tk()
        self.root.title("Mudae Multi-Instance Automation")
        self.root.geometry("800x700")
       
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
       
        # Instance Management Tab
        self.setup_instance_tab()
       
        # Control Tab
        self.setup_control_tab()
       
        # Log Tab
        self.setup_log_tab()

        # New: Settings Tab
        self.setup_settings_tab()
       
    def setup_instance_tab(self):
        instance_frame = ttk.Frame(self.notebook)
        self.notebook.add(instance_frame, text="Manage Instances")
       
        # Add new instance section
        add_frame = ttk.LabelFrame(instance_frame, text="Add New Instance", padding="10")
        add_frame.pack(fill=tk.X, padx=5, pady=5)
       
        # Instance name
        ttk.Label(add_frame, text="Instance Name:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.name_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.name_var, width=20).grid(row=0, column=1, sticky=tk.W, pady=2)
       
        # Intervals
        ttk.Label(add_frame, text="W Interval (seconds):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.w_interval_var = tk.StringVar(value="3600")
        ttk.Entry(add_frame, textvariable=self.w_interval_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=2)
       
        ttk.Label(add_frame, text="Rolls Interval (seconds):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.rolls_interval_var = tk.StringVar(value="180")
        ttk.Entry(add_frame, textvariable=self.rolls_interval_var, width=10).grid(row=2, column=1, sticky=tk.W, pady=2)
       
        # Buttons
        button_frame = ttk.Frame(add_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
       
        ttk.Button(button_frame, text="Select Chat Region", command=self.select_region_for_new).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Add Instance", command=self.add_instance).pack(side=tk.LEFT, padx=5)
       
        self.temp_region = None
        self.region_status = ttk.Label(add_frame, text="No region selected", foreground="red")
        self.region_status.grid(row=4, column=0, columnspan=2, pady=5)
       
        # Existing instances section
        list_frame = ttk.LabelFrame(instance_frame, text="Existing Instances", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
       
        # Treeview for instances
        columns = ('Name', 'W Interval', 'Rolls Interval', 'Status')
        self.instance_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)
       
        for col in columns:
            self.instance_tree.heading(col, text=col)
            self.instance_tree.column(col, width=120)
       
        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.instance_tree.yview)
        self.instance_tree.configure(yscrollcommand=scrollbar.set)
       
        self.instance_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
       
        # Instance control buttons
        instance_btn_frame = ttk.Frame(list_frame)
        instance_btn_frame.pack(fill=tk.X, pady=5)
       
        ttk.Button(instance_btn_frame, text="Edit Selected", command=self.edit_instance).pack(side=tk.LEFT, padx=5)
        ttk.Button(instance_btn_frame, text="Delete Selected", command=self.delete_instance).pack(side=tk.LEFT, padx=5)
        ttk.Button(instance_btn_frame, text="Test Region", command=self.test_region).pack(side=tk.LEFT, padx=5)
       
        # Advanced cleanup buttons
        cleanup_btn_frame = ttk.Frame(list_frame)
        cleanup_btn_frame.pack(fill=tk.X, pady=5)
       
        ttk.Button(cleanup_btn_frame, text="Force Cleanup", command=self.force_cleanup_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(cleanup_btn_frame, text="Reset All Instances", command=self.reset_all_instances).pack(side=tk.LEFT, padx=5)
       
        # Add monitor info section
        monitor_frame = ttk.LabelFrame(instance_frame, text="Monitor Information", padding="10")
        monitor_frame.pack(fill=tk.X, padx=5, pady=5)
       
        self.monitor_info_label = ttk.Label(monitor_frame, text="Loading monitor info...")
        self.monitor_info_label.pack()
       
        ttk.Button(monitor_frame, text="Refresh Monitor Info", command=self.update_monitor_info).pack(side=tk.LEFT, padx=5)
        ttk.Button(monitor_frame, text="Show Mouse Position", command=self.show_mouse_position).pack(side=tk.LEFT, padx=5)
       
        # Update monitor info
        self.update_monitor_info()
       
    def setup_control_tab(self):
        control_frame = ttk.Frame(self.notebook)
        self.notebook.add(control_frame, text="Control Panel")
       
        # Global controls
        global_frame = ttk.LabelFrame(control_frame, text="Global Controls", padding="10")
        global_frame.pack(fill=tk.X, padx=5, pady=5)
       
        global_btn_frame = ttk.Frame(global_frame)
        global_btn_frame.pack()
       
        self.start_all_btn = ttk.Button(global_btn_frame, text="Start All", command=self.start_all_instances)
        self.start_all_btn.pack(side=tk.LEFT, padx=5)
       
        self.pause_all_btn = ttk.Button(global_btn_frame, text="Pause All", command=self.pause_all_instances)
        self.pause_all_btn.pack(side=tk.LEFT, padx=5)
       
        self.stop_all_btn = ttk.Button(global_btn_frame, text="Stop All", command=self.stop_all_instances)
        self.stop_all_btn.pack(side=tk.LEFT, padx=5)
       
        # Individual instance controls
        individual_frame = ttk.LabelFrame(control_frame, text="Individual Controls", padding="10")
        individual_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
       
        # Instance selection
        ttk.Label(individual_frame, text="Select Instance:").pack(anchor=tk.W)
        self.control_instance_var = tk.StringVar()
        self.instance_combo = ttk.Combobox(individual_frame, textvariable=self.control_instance_var, state="readonly")
        self.instance_combo.pack(fill=tk.X, pady=5)
       
        # Individual control buttons
        individual_btn_frame = ttk.Frame(individual_frame)
        individual_btn_frame.pack()
       
        ttk.Button(individual_btn_frame, text="Start", command=self.start_selected_instance).pack(side=tk.LEFT, padx=5)
        ttk.Button(individual_btn_frame, text="Pause", command=self.pause_selected_instance).pack(side=tk.LEFT, padx=5)
        ttk.Button(individual_btn_frame, text="Stop", command=self.stop_selected_instance).pack(side=tk.LEFT, padx=5)
       
        # Status display
        status_frame = ttk.LabelFrame(individual_frame, text="Instance Status", padding="10")
        status_frame.pack(fill=tk.BOTH, expand=True, pady=10)
       
        self.status_text = tk.Text(status_frame, height=15, width=60, state=tk.DISABLED)
        status_scrollbar = ttk.Scrollbar(status_frame, orient="vertical", command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=status_scrollbar.set)
       
        self.status_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        status_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
       
        self.refresh_control_combo()
       
    def setup_log_tab(self):
        log_frame = ttk.Frame(self.notebook)
        self.notebook.add(log_frame, text="Logs")
       
        # Log display
        self.log_text = tk.Text(log_frame, height=30, width=80)
        log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
       
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
       
        # Clear log button
        ttk.Button(log_frame, text="Clear Log", command=self.clear_log).pack(pady=5)

    def setup_settings_tab(self):
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="Settings")
       
        ttk.Label(settings_frame, text="Retry Attempts:").pack(anchor=tk.W, pady=5)
        self.retry_var = tk.StringVar(value=str(self.retry_attempts))
        ttk.Entry(settings_frame, textvariable=self.retry_var, width=10).pack(fill=tk.X, pady=5)
       
        ttk.Label(settings_frame, text="Command Delay (seconds):").pack(anchor=tk.W, pady=5)
        self.delay_var = tk.StringVar(value=str(self.command_delay))
        ttk.Entry(settings_frame, textvariable=self.delay_var, width=10).pack(fill=tk.X, pady=5)
       
        ttk.Button(settings_frame, text="Save Settings", command=self.save_settings).pack(pady=10)
       
    def save_settings(self):
        try:
            self.retry_attempts = int(self.retry_var.get())
            self.command_delay = float(self.delay_var.get())
            self.log_message("Settings saved successfully")
            messagebox.showinfo("Success", "Settings saved!")
        except ValueError:
            self.log_message("Invalid settings values")
            messagebox.showerror("Error", "Please enter valid numbers for settings")
       
    def select_region_for_new(self):
        """Select region for new instance"""
        self.select_chat_region(callback=self.set_temp_region)
       
    def set_temp_region(self, region):
        """Set temporary region for new instance"""
        self.temp_region = region
        if region:
            self.region_status.config(text=f"Region: {region}", foreground="green")
        else:
            self.region_status.config(text="No region selected", foreground="red")
           
    def select_chat_region(self, callback=None):
        """Improved region selection with dual monitor support"""
        try:
            self.root.withdraw()  # Hide main window temporarily
           
            # Get all monitor information
            total_width, total_height = pyautogui.size()  # Fallback
           
            # Try to get actual multi-monitor setup
            temp_root = tk.Tk()
            total_width = temp_root.winfo_screenwidth()
            total_height = temp_root.winfo_screenheight()
            temp_root.destroy()
           
            # Create overlay that spans ALL monitors
            overlay = tk.Toplevel()
            overlay.geometry(f"{total_width}x{total_height}+0+0")
            overlay.attributes('-alpha', 0.3)
            overlay.configure(bg='black')
            overlay.attributes('-topmost', True)
            overlay.overrideredirect(True)  # Remove window decorations
           
            # Variables to store selection coordinates
            selection_start = None
            selection_end = None
            selection_rect = None
           
            # Create canvas for drawing selection rectangle
            canvas = tk.Canvas(overlay, highlightthickness=0, bg='black', cursor='crosshair')
            canvas.pack(fill=tk.BOTH, expand=True)
           
            # Instructions - position in center of total screen area
            canvas.create_text(
                total_width//2, 50,
                text="Click and drag to select the Discord chat area (works on all monitors)\nPress ESC to cancel",
                fill='white', font=('Arial', 16), anchor='center'
            )
           
            def start_selection(event):
                nonlocal selection_start, selection_rect
                selection_start = (event.x, event.y)
                if selection_rect:
                    canvas.delete(selection_rect)
                   
            def update_selection(event):
                nonlocal selection_rect
                if selection_start:
                    if selection_rect:
                        canvas.delete(selection_rect)
                   
                    selection_rect = canvas.create_rectangle(
                        selection_start[0], selection_start[1],
                        event.x, event.y,
                        outline='red', width=2, fill=''
                    )
                   
            def end_selection(event):
                nonlocal selection_end
                if selection_start:
                    selection_end = (event.x, event.y)
                   
                    # Calculate region coordinates
                    x1, y1 = selection_start
                    x2, y2 = selection_end
                   
                    chat_region = (
                        min(x1, x2), min(y1, y2),
                        abs(x2 - x1), abs(y2 - y1)
                    )
                   
                    overlay.destroy()
                    self.root.deiconify()  # Show main window again
                   
                    self.log_message(f"Chat region selected: {chat_region}")
                   
                    if callback:
                        callback(chat_region)
                   
            def cancel_selection(event=None):
                overlay.destroy()
                self.root.deiconify()  # Show main window again
                self.log_message("Region selection cancelled")
                if callback:
                    callback(None)
               
            # Bind mouse events
            canvas.bind('<Button-1>', start_selection)
            canvas.bind('<B1-Motion>', update_selection)
            canvas.bind('<ButtonRelease-1>', end_selection)
            canvas.bind('<Escape>', cancel_selection)
            overlay.bind('<Escape>', cancel_selection)
            overlay.protocol("WM_DELETE_WINDOW", cancel_selection)  # New: Handle window close
           
            # Focus on overlay to capture escape key
            overlay.focus_set()
           
        except Exception as e:
            self.log_message(f"Error in region selection: {e}")
            self.root.deiconify()  # Make sure main window is visible
            if callback:
                callback(None)
            messagebox.showerror("Error", f"Region selection failed: {e}")
               
    def add_instance(self):
        """Add a new instance"""
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Error", "Please enter an instance name")
            return
           
        if name in self.instances:
            messagebox.showerror("Error", f"Instance '{name}' already exists")
            return
           
        if not self.temp_region:
            messagebox.showerror("Error", "Please select a chat region first")
            return
           
        try:
            w_interval = int(self.w_interval_var.get())
            rolls_interval = int(self.rolls_interval_var.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for intervals")
            return
           
        if not self.validate_region(self.temp_region):
            messagebox.showerror("Error", "Selected region is invalid (out of screen bounds)")
            return
           
        # Create new instance
        instance = MudaeInstance(name, self.temp_region, w_interval, rolls_interval)
        self.instances[name] = instance
       
        # Clear form
        self.name_var.set("")
        self.temp_region = None
        self.region_status.config(text="No region selected", foreground="red")
       
        # Refresh displays
        self.refresh_instance_list()
        self.refresh_control_combo()
        self.save_instances()
        self.log_message(f"Added instance: {name}")
       
    def update_monitor_info(self):
        """Update monitor information display"""
        try:
            # Get screen dimensions
            temp_root = tk.Tk()
            screen_width = temp_root.winfo_screenwidth()
            screen_height = temp_root.winfo_screenheight()
            temp_root.destroy()
           
            # Get pyautogui screen size (primary monitor)
            primary_width, primary_height = pyautogui.size()
           
            monitor_text = f"Total Screen Area: {screen_width}x{screen_height}\n"
            monitor_text += f"Primary Monitor: {primary_width}x{primary_height}\n"
           
            if screen_width > primary_width or screen_height > primary_height:
                monitor_text += "✓ Multi-monitor setup detected!\n"
                monitor_text += "You can select regions on any monitor."
            else:
                monitor_text += "Single monitor detected."
               
            self.monitor_info_label.config(text=monitor_text)
           
        except Exception as e:
            self.monitor_info_label.config(text=f"Error detecting monitors: {e}")
           
    def show_mouse_position(self):
        """Show real-time mouse position to help with multi-monitor debugging"""
        pos_window = tk.Toplevel(self.root)
        pos_window.title("Mouse Position Tracker")
        pos_window.geometry("300x120")
        pos_window.attributes('-topmost', True)
       
        pos_label = ttk.Label(pos_window, text="Move mouse to see coordinates", font=('Arial', 12))
        pos_label.pack(expand=True)
       
        help_label = ttk.Label(pos_window, text="Use these coordinates to verify your regions", font=('Arial', 9))
        help_label.pack()
       
        def update_position():
            try:
                x, y = pyautogui.position()
                pos_label.config(text=f"Mouse Position:\nX: {x}, Y: {y}")
                pos_window.after(100, update_position)
            except:
                pos_window.destroy()
               
        update_position()
       
        # Auto close after 30 seconds
        pos_window.after(30000, pos_window.destroy)
       
    def refresh_instance_list(self):
        """Refresh the instance list in the treeview"""
        for item in self.instance_tree.get_children():
            self.instance_tree.delete(item)
           
        for name, instance in self.instances.items():
            status = "Stopped"
            if instance.running:
                status = "Paused" if instance.paused else "Running"
               
            self.instance_tree.insert('', 'end', values=(
                name, instance.w_interval, instance.rolls_interval, status
            ))
           
    def refresh_control_combo(self):
        """Refresh the control combo box"""
        self.instance_combo['values'] = list(self.instances.keys())
       
    def edit_instance(self):
        """Edit selected instance"""
        selection = self.instance_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an instance to edit")
            return
           
        item = self.instance_tree.item(selection[0])
        instance_name = item['values'][0]
       
        # TODO: Implement edit dialog
        messagebox.showinfo("Info", f"Edit functionality for '{instance_name}' - Coming soon!")
       
    def delete_instance(self):
        """Delete selected instance with better error handling"""
        selection = self.instance_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an instance to delete")
            return
           
        item = self.instance_tree.item(selection[0])
        instance_name = item['values'][0]
       
        if messagebox.askyesno("Confirm", f"Delete instance '{instance_name}'?"):
            try:
                # Force stop instance if running
                if instance_name in self.instances:
                    instance = self.instances[instance_name]
                    if instance.running:
                        self.stop_instance(instance_name)
                        time.sleep(0.5)  # Give thread time to stop
                   
                    del self.instances[instance_name]
               
                # Clean up thread reference
                if instance_name in self.automation_threads:
                    del self.automation_threads[instance_name]
               
                # Update displays
                self.refresh_instance_list()
                self.refresh_control_combo()
                self.save_instances()
                self.log_message(f"Deleted instance: {instance_name}")
               
            except Exception as e:
                self.log_message(f"Error deleting {instance_name}: {e}")
                messagebox.showerror("Error", f"Failed to delete {instance_name}: {e}")
               
    def force_cleanup_all(self):
        """Force cleanup all instances and threads"""
        try:
            # Stop all automation threads
            for name in list(self.instances.keys()):
                if self.instances[name].running:
                    self.stop_instance(name)
           
            # Clear thread references
            self.automation_threads.clear()
           
            # Give threads time to stop
            time.sleep(1)
           
            self.log_message("Force cleanup completed")
            messagebox.showinfo("Cleanup", "All instances and threads have been force cleaned")
           
        except Exception as e:
            self.log_message(f"Error during force cleanup: {e}")
            messagebox.showerror("Error", f"Force cleanup failed: {e}")
           
    def reset_all_instances(self):
        """Nuclear option - reset everything"""
        if messagebox.askyesno("Reset All",
                              "This will DELETE ALL instances and reset everything.\n"
                              "This cannot be undone. Are you sure?"):
            try:
                # Stop everything
                self.force_cleanup_all()
               
                # Clear all data
                self.instances.clear()
                self.automation_threads.clear()
               
                # Update displays
                self.refresh_instance_list()
                self.refresh_control_combo()
               
                # Delete config file
                if os.path.exists(self.config_file):
                    os.remove(self.config_file)
                   
                self.log_message("All instances reset - starting fresh")
                messagebox.showinfo("Reset Complete", "All instances have been deleted")
               
            except Exception as e:
                self.log_message(f"Error during reset: {e}")
                messagebox.showerror("Reset Error", f"Error during reset: {e}")
           
    def test_region(self):
        """Test selected instance's chat region with visual feedback"""
        selection = self.instance_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an instance to test")
            return
           
        item = self.instance_tree.item(selection[0])
        instance_name = item['values'][0]
        instance = self.instances[instance_name]
       
        if not instance.chat_region:
            messagebox.showerror("Error", "Instance has no chat region set")
            return
       
        # Show visual indicator of where the click will happen
        self.show_click_preview(instance.chat_region)
       
        # Ask user if they want to proceed with test
        if messagebox.askyesno("Test Region",
                              f"This will click in the selected region and type '$test'.\n"
                              f"Region: {instance.chat_region}\n"
                              f"Make sure Discord is visible. Proceed?"):
           
            # Send a test message
            self.send_command_to_instance(instance, "$test")
            self.log_message(f"Sent test command to {instance_name}")
       
    def show_click_preview(self, region):
        """Show a visual preview of where the click will happen"""
        try:
            x, y, w, h = region
            center_x = x + w // 2
            center_y = y + h // 2
           
            # Create a small preview window
            preview = tk.Toplevel(self.root)
            preview.geometry(f"300x150+{center_x-150}+{center_y-75}")
            preview.attributes('-topmost', True)
            preview.title("Click Preview")
           
            ttk.Label(preview, text=f"Click will happen at:\nX: {center_x}, Y: {center_y}\n"
                                   f"Region: {w}x{h}").pack(expand=True)
                                  
            # Auto-close after 3 seconds
            preview.after(3000, preview.destroy)
           
        except Exception as e:
            self.log_message(f"Error showing click preview: {e}")
       
    def validate_region(self, region):
        """Validate if region is within screen bounds"""
        try:
            screen_width, screen_height = pyautogui.size()
            x, y, w, h = region
            center_x = x + w // 2
            center_y = y + h // 2
            if 0 <= center_x < screen_width and 0 <= center_y < screen_height:
                return True
            return False
        except Exception as e:
            self.log_message(f"Error validating region: {e}")
            return False
       
    def send_command_to_instance(self, instance, command):
        """Send a command to a specific instance with retry"""
        with self.pyautogui_lock:  # Lock to prevent concurrent PyAutoGUI usage
            for attempt in range(1, self.retry_attempts + 1):
                try:
                    if not self.validate_region(instance.chat_region):
                        self.log_message(f"[{instance.name}] Invalid chat region")
                        return False
                   
                    center_x = instance.chat_region[0] + instance.chat_region[2] // 2
                    center_y = instance.chat_region[1] + instance.chat_region[3] // 2
                    pyautogui.click(center_x, center_y)
                    time.sleep(self.command_delay)
                    pyautogui.typewrite(command)
                    time.sleep(self.command_delay)
                    pyautogui.press('enter')
                   
                    self.log_message(f"[{instance.name}] Sent command: {command} (attempt {attempt})")
                   
                    # Optional: Verify command success (uncomment if pytesseract installed)
                    # if self.verify_command(instance, command):
                    #     return True
                   
                    return True
               
                except Exception as e:
                    self.log_message(f"[{instance.name}] Error sending command {command} (attempt {attempt}): {e}")
                    if attempt < self.retry_attempts:
                        time.sleep(1)  # Wait before retry
           
            self.log_message(f"[{instance.name}] Failed to send command {command} after {self.retry_attempts} attempts")
            return False
           
    def verify_command(self, instance, command):
        """Verify if command was successful by capturing and analyzing chat region (requires pytesseract)"""
        try:
            import pytesseract  # Requires pip install pytesseract and Tesseract OCR installed
            x, y, w, h = instance.chat_region
            screenshot = pyautogui.screenshot(region=(x, y, w, h))
            text = pytesseract.image_to_string(screenshot)
           
            # Check for expected response (customize based on Mudae bot responses)
            if "rolled" in text.lower() or "claimed" in text.lower():  # Example keywords
                self.log_message(f"[{instance.name}] Command {command} verified successfully")
                return True
            else:
                self.log_message(f"[{instance.name}] Command {command} verification failed (no expected response)")
                return False
           
        except ImportError:
            self.log_message("pytesseract not installed; skipping verification")
            return True  # Assume success if not installed
        except Exception as e:
            self.log_message(f"[{instance.name}] Error verifying command {command}: {e}")
            return False
           
    def automation_loop(self, instance_name):
        """Main automation loop for an instance with dynamic sleep"""
        instance = self.instances[instance_name]
       
        while instance.running:
            if instance.paused:
                time.sleep(1)
                continue
               
            current_time = time.time()
           
            next_w = max(0, instance.w_interval - (current_time - instance.last_w_time))
            next_rolls = max(0, instance.rolls_interval - (current_time - instance.last_rolls_time))
           
            # Send commands if time is up
            if next_w <= 0:
                if self.send_command_to_instance(instance, ".w"):
                    instance.last_w_time = current_time
                    time.sleep(random.uniform(1, 3))
                   
            if next_rolls <= 0:
                if self.send_command_to_instance(instance, ".rolls"):
                    instance.last_rolls_time = current_time
                    time.sleep(random.uniform(1, 3))
           
            # Dynamic sleep: Sleep until the next command or max 5 seconds
            sleep_time = min(next_w, next_rolls, 5)
            time.sleep(sleep_time if sleep_time > 0 else 1)
           
        # Clean up thread reference when done
        if instance_name in self.automation_threads:
            del self.automation_threads[instance_name]
           
    def start_instance(self, instance_name):
        """Start automation for a specific instance"""
        if instance_name not in self.instances:
            return
           
        instance = self.instances[instance_name]
        instance.running = True
        instance.paused = False
       
        # Start automation thread
        thread = threading.Thread(target=self.automation_loop, args=(instance_name,), daemon=True)
        self.automation_threads[instance_name] = thread
        thread.start()
       
        self.log_message(f"Started automation for: {instance_name}")
        self.refresh_instance_list()
        self.update_status_display()
       
    def pause_instance(self, instance_name):
        """Pause automation for a specific instance"""
        if instance_name in self.instances:
            instance = self.instances[instance_name]
            instance.paused = not instance.paused
            status = "paused" if instance.paused else "resumed"
            self.log_message(f"{instance_name} automation {status}")
            self.refresh_instance_list()
            self.update_status_display()
           
    def stop_instance(self, instance_name):
        """Stop automation for a specific instance with error handling"""
        try:
            if instance_name in self.instances:
                instance = self.instances[instance_name]
                instance.running = False
                instance.paused = False
               
                # Wait for thread to stop gracefully
                if instance_name in self.automation_threads:
                    thread = self.automation_threads[instance_name]
                    thread.join(timeout=2)  # Wait up to 2 seconds
                    if thread.is_alive():
                        self.log_message(f"Warning: Thread for {instance_name} did not stop gracefully")
                    del self.automation_threads[instance_name]
                   
                self.log_message(f"Stopped automation for: {instance_name}")
                self.refresh_instance_list()
                self.update_status_display()
        except Exception as e:
            self.log_message(f"Error stopping {instance_name}: {e}")
           
    def start_all_instances(self):
        """Start all instances"""
        for name in list(self.instances.keys()):
            if not self.instances[name].running:
                self.start_instance(name)
               
    def pause_all_instances(self):
        """Pause all running instances"""
        for name in self.instances:
            if self.instances[name].running:
                self.pause_instance(name)
               
    def stop_all_instances(self):
        """Stop all instances"""
        for name in list(self.instances.keys()):
            self.stop_instance(name)
           
    def start_selected_instance(self):
        """Start selected instance from control panel"""
        instance_name = self.control_instance_var.get()
        if instance_name and not self.instances[instance_name].running:
            self.start_instance(instance_name)
           
    def pause_selected_instance(self):
        """Pause selected instance from control panel"""
        instance_name = self.control_instance_var.get()
        if instance_name:
            self.pause_instance(instance_name)
           
    def stop_selected_instance(self):
        """Stop selected instance from control panel"""
        instance_name = self.control_instance_var.get()
        if instance_name:
            self.stop_instance(instance_name)
           
    def update_status_display(self):
        """Update the status display in control panel"""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete(1.0, tk.END)
       
        for name, instance in self.instances.items():
            status = "Stopped"
            if instance.running:
                status = "Paused" if instance.paused else "Running"
               
            next_w = max(0, int(instance.w_interval - (time.time() - instance.last_w_time)))
            next_rolls = max(0, int(instance.rolls_interval - (time.time() - instance.last_rolls_time)))
           
            self.status_text.insert(tk.END, f"{name}:\n")
            self.status_text.insert(tk.END, f" Status: {status}\n")
            self.status_text.insert(tk.END, f" Next $w in: {next_w} seconds\n")
            self.status_text.insert(tk.END, f" Next $rolls in: {next_rolls} seconds\n")
            self.status_text.insert(tk.END, f" Region: {instance.chat_region}\n\n")
           
        self.status_text.config(state=tk.DISABLED)
       
        # Schedule next update
        self.root.after(5000, self.update_status_display)
       
    def save_instances(self):
        """Save instances to file"""
        try:
            data = {name: instance.to_dict() for name, instance in self.instances.items()}
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.log_message(f"Error saving instances: {e}")
            messagebox.showerror("Error", f"Failed to save instances: {e}")
           
    def load_instances(self):
        """Load instances from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                   
                for name, instance_data in data.items():
                    self.instances[name] = MudaeInstance.from_dict(instance_data)
                   
                self.log_message(f"Loaded {len(self.instances)} instances from config")
                self.refresh_instance_list()
                self.refresh_control_combo()
        except Exception as e:
            self.log_message(f"Error loading instances: {e}")
            messagebox.showerror("Error", f"Failed to load instances: {e}")
           
    def log_message(self, message):
        """Add message to log with full timestamp and save to file"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
       
        # Check if GUI is initialized
        if hasattr(self, 'log_text') and self.log_text:
            try:
                self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
                self.log_text.see(tk.END)
                self.root.update()
            except:
                print(f"[{timestamp}] {message}")
        else:
            print(f"[{timestamp}] {message}")
       
        # Save to file
        try:
            with open("mudae_log.txt", "a") as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            print(f"Error saving log: {e}")
       
    def clear_log(self):
        """Clear the log"""
        self.log_text.delete(1.0, tk.END)
       
    def run(self):
        """Run the GUI"""
        try:
            # Start status update loop
            self.update_status_display()
            self.root.mainloop()
        except KeyboardInterrupt:
            self.stop_all_instances()
        except Exception as e:
            self.log_message(f"GUI error: {e}")
            messagebox.showerror("Error", f"Application error: {e}")
           
if __name__ == "__main__":
    # Install required packages if not present (informational)
    try:
        import pyautogui
        import cv2
        import numpy as np
        from PIL import Image, ImageTk
    except ImportError as e:
        print(f"Missing required package: {e}")
        print("Please install with: pip install opencv-python pyautogui pillow numpy")
        exit(1)
       
    # OS-specific instructions
    # Configure pyautogui safety
    pyautogui.FAILSAFE = True  # Move mouse to corner to stop
    pyautogui.PAUSE = 0.1  # Small pause between actions
   
    print("Mudae Multi-Instance Automation Bot")
    print("===================================")
    print("This bot supports multiple Discord accounts/tabs")
    print("Each instance can have different settings and chat regions")
    print("Move mouse to top-left corner for emergency stop")
    print()
   
    app = MudaeMultiAutomation()
    app.run()