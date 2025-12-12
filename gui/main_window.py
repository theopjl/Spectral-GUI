#
#  Main Window - Portable Spectral Measurement GUI
#
#  Features (Option A - Major Refactor):
#  - Tabbed interface (ttk.Notebook)
#  - Detached plot window
#  - Threading for measurements
#  - Progress indicators
#  - Keyboard shortcuts
#  - Modern ttk widgets
#  - Device-agnostic design
#

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from queue import Queue, Empty
from typing import Optional, Dict, Any, List
from datetime import datetime
import time

from ..core.device_interface import SpectralDevice, DeviceStatus, MeasurementType
from ..core.measurement_result import MeasurementResult
from .plot_window import PlotWindow


class SpectralMeasurementGUI:
    """
    Portable, device-agnostic GUI for spectral measurements.
    
    Features:
    - Works with ANY device implementing SpectralDevice interface
    - Modern tabbed interface
    - Non-blocking measurements (threading)
    - Progress indicators and status feedback
    - Keyboard shortcuts
    - Detached plot window for performance
    """
    
    def __init__(self, root: tk.Tk, device: SpectralDevice):
        self.root = root
        self.device = device
        
        # Get device capabilities to build UI
        self.capabilities = device.get_capabilities()
        
        # Configure window
        self.root.title(f"Spectral Measurement - {self.capabilities.device_name}")
        self.root.geometry("700x600")
        self.root.minsize(600, 500)
        
        # Threading for non-blocking measurements
        self.measurement_queue: Queue = Queue()
        self.is_measuring = False
        self.abort_requested = False
        
        # State
        self.current_result: Optional[MeasurementResult] = None
        self.measurement_history: List[MeasurementResult] = []
        self.saved_labels: List[str] = []
        
        # Auto-repeat state
        self.auto_repeat_active = False
        self.auto_repeat_job = None
        
        # UI variables
        self._create_variables()
        
        # Build UI
        self._apply_theme()
        self._create_menu_bar()
        self._create_status_bar()
        self._create_notebook()
        self._setup_keyboard_shortcuts()
        
        # Create detached plot window (hidden initially)
        self.plot_window = PlotWindow(self.root, f"Spectrum - {self.capabilities.device_name}")
        self.plot_window.withdraw()
        
        # Register device callbacks
        self.device.register_callback('status_changed', self._on_device_status_changed)
        self.device.register_callback('error', self._on_device_error)
        
        # Start queue processing
        self._process_queue()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    
    # =========================================================================
    # UI Creation
    # =========================================================================
    
    def _create_variables(self):
        """Create tkinter variables"""
        # Measurement type
        default_type = self.capabilities.measurement_types[0].value if self.capabilities.measurement_types else 'irradiance'
        self.measurement_type = tk.StringVar(value=default_type)
        
        # Settings variables (created dynamically from capabilities)
        self.setting_vars: Dict[str, tk.Variable] = {}
        for setting in self.capabilities.settings:
            if setting.setting_type == 'int':
                var = tk.IntVar(value=setting.default_value)
            elif setting.setting_type == 'float':
                var = tk.DoubleVar(value=setting.default_value)
            elif setting.setting_type == 'bool':
                var = tk.BooleanVar(value=setting.default_value)
            else:
                var = tk.StringVar(value=str(setting.default_value))
            self.setting_vars[setting.name] = var
        
        # Save label
        self.save_label = tk.StringVar()
        
        # Auto-repeat
        self.auto_repeat_enabled = tk.BooleanVar(value=False)
        self.auto_repeat_interval = tk.IntVar(value=300)
        self.auto_repeat_types: Dict[str, tk.BooleanVar] = {}
        for mtype in self.capabilities.measurement_types:
            self.auto_repeat_types[mtype.value] = tk.BooleanVar(value=False)
    
    def _apply_theme(self):
        """Apply modern ttk theme"""
        style = ttk.Style()
        
        # Try to use a modern theme
        available_themes = style.theme_names()
        for theme in ['clam', 'alt', 'default']:
            if theme in available_themes:
                style.theme_use(theme)
                break
        
        # Custom styles
        style.configure('Title.TLabel', font=('TkDefaultFont', 12, 'bold'))
        style.configure('Status.TLabel', font=('TkDefaultFont', 9))
        style.configure('Success.TLabel', foreground='green')
        style.configure('Error.TLabel', foreground='red')
        style.configure('Warning.TLabel', foreground='orange')
        
        # Big measure button
        style.configure('Measure.TButton', font=('TkDefaultFont', 11, 'bold'), padding=10)
        
        # Progress bar
        style.configure('green.Horizontal.TProgressbar', troughcolor='lightgray', background='green')
    
    def _create_menu_bar(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export Data...", command=self._export_data, accelerator="Ctrl+E")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close, accelerator="Ctrl+Q")
        
        # Measure menu
        measure_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Measure", menu=measure_menu)
        measure_menu.add_command(label="Quick Measure", command=self._measure, accelerator="F5")
        measure_menu.add_command(label="Save Last", command=self._save_measurement, accelerator="Ctrl+S")
        measure_menu.add_separator()
        measure_menu.add_command(label="Abort", command=self._abort_measurement, accelerator="Escape")
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Show Plot Window", command=self._toggle_plot_window, accelerator="Ctrl+P")
        
        # Device menu
        device_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Device", menu=device_menu)
        device_menu.add_command(label="Reconnect", command=self._reconnect_device)
        device_menu.add_command(label="Device Info", command=self._show_device_info)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Keyboard Shortcuts", command=self._show_shortcuts)
        help_menu.add_command(label="About", command=self._show_about)
    
    def _create_status_bar(self):
        """Create status bar at bottom"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Separator
        ttk.Separator(status_frame, orient=tk.HORIZONTAL).pack(fill=tk.X)
        
        inner_frame = ttk.Frame(status_frame)
        inner_frame.pack(fill=tk.X, padx=5, pady=3)
        
        # Status indicator (colored circle)
        self.status_canvas = tk.Canvas(inner_frame, width=12, height=12, highlightthickness=0)
        self.status_canvas.pack(side=tk.LEFT, padx=(0, 5))
        self.status_indicator = self.status_canvas.create_oval(2, 2, 10, 10, fill='gray')
        
        # Status text
        self.status_label = ttk.Label(inner_frame, text="Initializing...", style='Status.TLabel')
        self.status_label.pack(side=tk.LEFT)
        
        # Device info on right
        self.device_info_label = ttk.Label(inner_frame, text="", style='Status.TLabel')
        self.device_info_label.pack(side=tk.RIGHT)
        
        # Progress bar (hidden by default)
        self.progress_frame = ttk.Frame(status_frame)
        self.progress = ttk.Progressbar(self.progress_frame, mode='indeterminate', length=200)
        self.progress.pack(fill=tk.X, padx=5, pady=2)
        
        # Update status
        self._update_status()
    
    def _create_notebook(self):
        """Create tabbed interface"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tab 1: Measure
        self._create_measure_tab()
        
        # Tab 2: Settings
        self._create_settings_tab()
        
        # Tab 3: Auto-Repeat
        self._create_auto_repeat_tab()
        
        # Tab 4: Data
        self._create_data_tab()
    
    def _create_measure_tab(self):
        """Create the main measurement tab"""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="  Measure  ")
        
        # Configure grid
        tab.columnconfigure(0, weight=1)
        tab.columnconfigure(1, weight=1)
        
        # Left side: Measurement controls
        left_frame = ttk.LabelFrame(tab, text="Measurement", padding=10)
        left_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 5), pady=5)
        
        # Measurement type selection
        ttk.Label(left_frame, text="Measurement Type:", style='Title.TLabel').pack(anchor='w', pady=(0, 5))
        
        for mtype in self.capabilities.measurement_types:
            rb = ttk.Radiobutton(left_frame, text=mtype.value.capitalize(), 
                                  variable=self.measurement_type, value=mtype.value)
            rb.pack(anchor='w', padx=20)
        
        ttk.Separator(left_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)
        
        # Measure button
        self.measure_btn = ttk.Button(left_frame, text="⚡ Measure", style='Measure.TButton',
                                       command=self._measure)
        self.measure_btn.pack(fill=tk.X, pady=10)
        
        ttk.Label(left_frame, text="Press F5 or Ctrl+M", foreground='gray').pack()
        
        ttk.Separator(left_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)
        
        # Save controls
        ttk.Label(left_frame, text="Label:").pack(anchor='w')
        ttk.Entry(left_frame, textvariable=self.save_label, width=25).pack(fill=tk.X, pady=(0, 5))
        
        self.save_btn = ttk.Button(left_frame, text="💾 Save Measurement", command=self._save_measurement, state='disabled')
        self.save_btn.pack(fill=tk.X)
        
        # Right side: Last measurement results
        right_frame = ttk.LabelFrame(tab, text="Last Measurement", padding=10)
        right_frame.grid(row=0, column=1, sticky='nsew', padx=(5, 0), pady=5)
        
        # Result display
        self.result_text = tk.Text(right_frame, height=12, width=35, font=('Consolas', 10),
                                    state='disabled', wrap='word')
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
        # Plot button
        plot_btn_frame = ttk.Frame(right_frame)
        plot_btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.plot_btn = ttk.Button(plot_btn_frame, text="📊 Show Plot Window", command=self._toggle_plot_window)
        self.plot_btn.pack(fill=tk.X)
        
        ttk.Label(plot_btn_frame, text="Press Ctrl+P", foreground='gray').pack()
    
    def _create_settings_tab(self):
        """Create settings tab based on device capabilities"""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="  Settings  ")
        
        # Scrollable frame for many settings
        canvas = tk.Canvas(tab, highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Build settings UI from capabilities
        row = 0
        for setting in self.capabilities.settings:
            frame = ttk.Frame(scrollable_frame)
            frame.grid(row=row, column=0, sticky='ew', pady=5, padx=5)
            frame.columnconfigure(1, weight=1)
            
            # Label
            label_text = f"{setting.display_name}:"
            if setting.unit:
                label_text += f" ({setting.unit})"
            ttk.Label(frame, text=label_text, width=25).grid(row=0, column=0, sticky='w')
            
            # Input widget based on type
            var = self.setting_vars[setting.name]
            
            if setting.setting_type == 'bool':
                widget = ttk.Checkbutton(frame, variable=var)
            elif setting.setting_type == 'choice' and setting.choices:
                widget = ttk.Combobox(frame, textvariable=var, values=setting.choices, 
                                       state='readonly', width=15)
            else:
                widget = ttk.Entry(frame, textvariable=var, width=15)
            
            widget.grid(row=0, column=1, sticky='w', padx=(10, 0))
            
            # Tooltip
            if setting.tooltip:
                ttk.Label(frame, text=setting.tooltip, foreground='gray', 
                          font=('TkDefaultFont', 8)).grid(row=1, column=0, columnspan=2, sticky='w')
            
            # Range info
            if setting.min_value is not None or setting.max_value is not None:
                range_text = f"Range: {setting.min_value or 'min'} - {setting.max_value or 'max'}"
                ttk.Label(frame, text=range_text, foreground='gray',
                          font=('TkDefaultFont', 8)).grid(row=2, column=0, columnspan=2, sticky='w')
            
            row += 1
        
        # Apply button
        btn_frame = ttk.Frame(scrollable_frame)
        btn_frame.grid(row=row, column=0, sticky='ew', pady=20, padx=5)
        
        ttk.Button(btn_frame, text="Apply Settings", command=self._apply_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Reset to Defaults", command=self._reset_settings).pack(side=tk.LEFT, padx=5)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _create_auto_repeat_tab(self):
        """Create auto-repeat configuration tab"""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="  Auto-Repeat  ")
        
        # Enable checkbox
        enable_frame = ttk.Frame(tab)
        enable_frame.pack(fill=tk.X, pady=10)
        
        ttk.Checkbutton(enable_frame, text="Enable Auto-Repeat", variable=self.auto_repeat_enabled,
                        command=self._toggle_auto_repeat).pack(anchor='w')
        
        # Interval setting
        interval_frame = ttk.LabelFrame(tab, text="Interval", padding=10)
        interval_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(interval_frame, text="Repeat every:").pack(side=tk.LEFT)
        ttk.Entry(interval_frame, textvariable=self.auto_repeat_interval, width=8).pack(side=tk.LEFT, padx=5)
        ttk.Label(interval_frame, text="seconds").pack(side=tk.LEFT)
        
        # Measurement types to repeat
        types_frame = ttk.LabelFrame(tab, text="Measurements to Repeat", padding=10)
        types_frame.pack(fill=tk.X, pady=10)
        
        for mtype in self.capabilities.measurement_types:
            ttk.Checkbutton(types_frame, text=mtype.value.capitalize(),
                            variable=self.auto_repeat_types[mtype.value]).pack(anchor='w')
        
        # Status
        status_frame = ttk.LabelFrame(tab, text="Auto-Repeat Status", padding=10)
        status_frame.pack(fill=tk.X, pady=10)
        
        self.auto_repeat_status = ttk.Label(status_frame, text="Inactive")
        self.auto_repeat_status.pack(anchor='w')
        
        self.auto_repeat_next = ttk.Label(status_frame, text="")
        self.auto_repeat_next.pack(anchor='w')
        
        # Control buttons
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, pady=10)
        
        self.start_repeat_btn = ttk.Button(btn_frame, text="▶ Start", command=self._start_auto_repeat)
        self.start_repeat_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_repeat_btn = ttk.Button(btn_frame, text="⏹ Stop", command=self._stop_auto_repeat, state='disabled')
        self.stop_repeat_btn.pack(side=tk.LEFT, padx=5)
    
    def _create_data_tab(self):
        """Create data management tab"""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="  Data  ")
        
        # Saved measurements list
        list_frame = ttk.LabelFrame(tab, text="Saved Measurements", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview for saved data
        columns = ('label', 'type', 'value', 'time')
        self.data_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        self.data_tree.heading('label', text='Label')
        self.data_tree.heading('type', text='Type')
        self.data_tree.heading('value', text='Value')
        self.data_tree.heading('time', text='Time')
        
        self.data_tree.column('label', width=150)
        self.data_tree.column('type', width=100)
        self.data_tree.column('value', width=120)
        self.data_tree.column('time', width=100)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.data_tree.yview)
        self.data_tree.configure(yscrollcommand=scrollbar.set)
        
        self.data_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Buttons
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="Export Selected", command=self._export_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Export All", command=self._export_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Delete Selected", command=self._delete_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Clear All", command=self._clear_data).pack(side=tk.LEFT, padx=5)
    
    # =========================================================================
    # Keyboard Shortcuts
    # =========================================================================
    
    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts"""
        self.root.bind('<F5>', lambda e: self._measure())
        self.root.bind('<Control-m>', lambda e: self._measure())
        self.root.bind('<Control-s>', lambda e: self._save_measurement())
        self.root.bind('<Control-p>', lambda e: self._toggle_plot_window())
        self.root.bind('<Control-e>', lambda e: self._export_data())
        self.root.bind('<Control-q>', lambda e: self._on_close())
        self.root.bind('<Escape>', lambda e: self._abort_measurement())
        
        # Measurement type shortcuts
        for i, mtype in enumerate(self.capabilities.measurement_types):
            if i < 9:  # Ctrl+1 through Ctrl+9
                self.root.bind(f'<Control-{i+1}>', 
                              lambda e, t=mtype.value: self._quick_measure(t))
    
    # =========================================================================
    # Measurement Functions
    # =========================================================================
    
    def _measure(self):
        """Start a measurement"""
        if self.is_measuring:
            messagebox.showwarning("Busy", "A measurement is already in progress")
            return
        
        measurement_type = self.measurement_type.get()
        self._start_measurement_thread(measurement_type)
    
    def _quick_measure(self, measurement_type: str):
        """Quick measure with specific type"""
        if self.is_measuring:
            return
        
        self.measurement_type.set(measurement_type)
        self._start_measurement_thread(measurement_type)
    
    def _start_measurement_thread(self, measurement_type: str):
        """Start measurement in background thread"""
        self.is_measuring = True
        self.abort_requested = False
        
        # Update UI
        self.measure_btn.config(state='disabled')
        self.save_btn.config(state='disabled')
        self._show_progress(True)
        self._set_status("Measuring...", "yellow")
        
        # Get current settings
        settings = {name: var.get() for name, var in self.setting_vars.items()}
        
        # Start thread
        thread = threading.Thread(
            target=self._measurement_thread,
            args=(measurement_type, settings),
            daemon=True
        )
        thread.start()
    
    def _measurement_thread(self, measurement_type: str, settings: Dict[str, Any]):
        """Background thread for measurement"""
        try:
            # Apply settings
            self.device.configure(settings)
            
            # Check abort
            if self.abort_requested:
                self.measurement_queue.put(('aborted', None))
                return
            
            # Get measurement type enum
            mtype = MeasurementType(measurement_type)
            
            # Perform measurement
            result = self.device.measure(mtype)
            
            if result is None:
                self.measurement_queue.put(('error', 'Measurement failed'))
            else:
                self.measurement_queue.put(('success', result))
                
        except Exception as e:
            self.measurement_queue.put(('error', str(e)))
    
    def _process_queue(self):
        """Process measurement results from background thread"""
        try:
            while True:
                status, data = self.measurement_queue.get_nowait()
                
                self.is_measuring = False
                self._show_progress(False)
                self.measure_btn.config(state='normal')
                
                if status == 'success':
                    self._on_measurement_complete(data)
                elif status == 'error':
                    self._on_measurement_error(data)
                elif status == 'aborted':
                    self._set_status("Measurement aborted", "orange")
                    
        except Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self._process_queue)
    
    def _on_measurement_complete(self, result: MeasurementResult):
        """Handle successful measurement"""
        self.current_result = result
        self.save_btn.config(state='normal')
        
        # Update status
        self._set_status("Ready", "green")
        
        # Update result display
        self._update_result_display(result)
        
        # Update plot
        self.plot_window.update_spectrum(
            result.wavelengths,
            result.spectral_data,
            result.measurement_type,
            result.get_summary()
        )
    
    def _on_measurement_error(self, error_message: str):
        """Handle measurement error"""
        self._set_status(f"Error: {error_message}", "red")
        messagebox.showerror("Measurement Error", error_message)
    
    def _abort_measurement(self):
        """Abort in-progress measurement"""
        if self.is_measuring:
            self.abort_requested = True
            self.device.abort_measurement()
            self._set_status("Aborting...", "orange")
    
    def _update_result_display(self, result: MeasurementResult):
        """Update the result text display"""
        self.result_text.config(state='normal')
        self.result_text.delete('1.0', tk.END)
        
        text = result.get_summary()
        text += f"\n\nWavelength Range: {result.wavelength_range[0]:.0f} - {result.wavelength_range[1]:.0f} nm"
        text += f"\nPeak: {result.peak_wavelength:.1f} nm"
        text += f"\nPixels: {result.pixel_count}"
        
        self.result_text.insert('1.0', text)
        self.result_text.config(state='disabled')
    
    # =========================================================================
    # Save / Export Functions
    # =========================================================================
    
    def _save_measurement(self):
        """Save current measurement"""
        if self.current_result is None:
            messagebox.showwarning("No Data", "No measurement to save")
            return
        
        label = self.save_label.get() or f"measurement_{len(self.measurement_history) + 1}"
        
        # Add to history
        self.measurement_history.append(self.current_result)
        self.saved_labels.append(label)
        
        # Add to treeview
        result = self.current_result
        self.data_tree.insert('', 'end', values=(
            label,
            result.measurement_type,
            f"{result.display_value:.4g} {result.display_unit}",
            result.timestamp.strftime("%H:%M:%S")
        ))
        
        # Clear label
        self.save_label.set("")
        self.save_btn.config(state='disabled')
        
        self._set_status(f"Saved: {label}", "green")
    
    def _export_data(self):
        """Export all data to CSV"""
        if not self.measurement_history:
            messagebox.showwarning("No Data", "No measurements to export")
            return
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if filepath:
            try:
                with open(filepath, 'w') as f:
                    # Write header
                    f.write(self.measurement_history[0].to_csv_row(include_header=True))
                    f.write("\n")
                    
                    # Write data
                    for result in self.measurement_history[1:]:
                        f.write(result.to_csv_row())
                        f.write("\n")
                
                messagebox.showinfo("Exported", f"Data exported to:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))
    
    def _export_selected(self):
        """Export selected items"""
        selection = self.data_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select items to export")
            return
        
        # Get indices of selected items
        indices = [self.data_tree.index(item) for item in selection]
        selected_results = [self.measurement_history[i] for i in indices]
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if filepath and selected_results:
            with open(filepath, 'w') as f:
                f.write(selected_results[0].to_csv_row(include_header=True))
                f.write("\n")
                for result in selected_results[1:]:
                    f.write(result.to_csv_row())
                    f.write("\n")
            
            messagebox.showinfo("Exported", f"Selected data exported to:\n{filepath}")
    
    def _delete_selected(self):
        """Delete selected items"""
        selection = self.data_tree.selection()
        if not selection:
            return
        
        if messagebox.askyesno("Confirm Delete", "Delete selected measurements?"):
            indices = sorted([self.data_tree.index(item) for item in selection], reverse=True)
            
            for idx in indices:
                del self.measurement_history[idx]
                del self.saved_labels[idx]
            
            for item in selection:
                self.data_tree.delete(item)
    
    def _clear_data(self):
        """Clear all data"""
        if messagebox.askyesno("Confirm Clear", "Delete all saved measurements?"):
            self.measurement_history.clear()
            self.saved_labels.clear()
            for item in self.data_tree.get_children():
                self.data_tree.delete(item)
    
    # =========================================================================
    # Settings Functions
    # =========================================================================
    
    def _apply_settings(self):
        """Apply settings to device"""
        settings = {name: var.get() for name, var in self.setting_vars.items()}
        
        if self.device.configure(settings):
            self._set_status("Settings applied", "green")
        else:
            self._set_status("Failed to apply settings", "red")
            messagebox.showerror("Settings Error", "Failed to apply settings to device")
    
    def _reset_settings(self):
        """Reset settings to defaults"""
        for setting in self.capabilities.settings:
            if setting.name in self.setting_vars:
                self.setting_vars[setting.name].set(setting.default_value)
    
    # =========================================================================
    # Auto-Repeat Functions
    # =========================================================================
    
    def _toggle_auto_repeat(self):
        """Toggle auto-repeat on/off"""
        if self.auto_repeat_enabled.get():
            pass  # Just enables, doesn't start
        else:
            self._stop_auto_repeat()
    
    def _start_auto_repeat(self):
        """Start auto-repeat measurements"""
        # Check if any type is selected
        selected_types = [t for t, v in self.auto_repeat_types.items() if v.get()]
        if not selected_types:
            messagebox.showwarning("No Types Selected", "Please select measurement types to repeat")
            return
        
        self.auto_repeat_active = True
        self.auto_repeat_enabled.set(True)
        
        self.start_repeat_btn.config(state='disabled')
        self.stop_repeat_btn.config(state='normal')
        
        self.auto_repeat_status.config(text="Active", foreground='green')
        
        self._auto_repeat_cycle()
    
    def _stop_auto_repeat(self):
        """Stop auto-repeat measurements"""
        self.auto_repeat_active = False
        
        if self.auto_repeat_job:
            self.root.after_cancel(self.auto_repeat_job)
            self.auto_repeat_job = None
        
        self.start_repeat_btn.config(state='normal')
        self.stop_repeat_btn.config(state='disabled')
        
        self.auto_repeat_status.config(text="Inactive", foreground='gray')
        self.auto_repeat_next.config(text="")
    
    def _auto_repeat_cycle(self):
        """Execute one auto-repeat cycle"""
        if not self.auto_repeat_active:
            return
        
        # Perform measurements for selected types
        for mtype, enabled in self.auto_repeat_types.items():
            if enabled.get() and not self.is_measuring:
                self._quick_measure(mtype)
                self.root.after(2000, self._save_measurement)  # Auto-save after delay
        
        # Schedule next cycle
        interval = self.auto_repeat_interval.get() * 1000  # Convert to ms
        self.auto_repeat_job = self.root.after(interval, self._auto_repeat_cycle)
        
        # Update next time display
        next_time = datetime.now().timestamp() + self.auto_repeat_interval.get()
        next_str = datetime.fromtimestamp(next_time).strftime("%H:%M:%S")
        self.auto_repeat_next.config(text=f"Next: {next_str}")
    
    # =========================================================================
    # Status Functions
    # =========================================================================
    
    def _update_status(self):
        """Update status display from device"""
        status = self.device.status
        status_text = self.device.get_status_string()
        
        colors = {
            DeviceStatus.DISCONNECTED: 'gray',
            DeviceStatus.CONNECTING: 'yellow',
            DeviceStatus.CONNECTED: 'green',
            DeviceStatus.MEASURING: 'blue',
            DeviceStatus.ERROR: 'red',
            DeviceStatus.BUSY: 'orange',
        }
        
        color = colors.get(status, 'gray')
        self._set_status(status_text, color)
        
        # Update device info
        caps = self.capabilities
        self.device_info_label.config(text=f"{caps.device_name} | {caps.serial_number or 'No serial'}")
    
    def _set_status(self, message: str, color: str = 'gray'):
        """Set status bar message and color"""
        self.status_label.config(text=message)
        self.status_canvas.itemconfig(self.status_indicator, fill=color)
    
    def _show_progress(self, show: bool):
        """Show or hide progress bar"""
        if show:
            self.progress_frame.pack(fill=tk.X)
            self.progress.start(10)
        else:
            self.progress.stop()
            self.progress_frame.pack_forget()
    
    def _on_device_status_changed(self, status: DeviceStatus):
        """Callback for device status change"""
        self.root.after(0, self._update_status)
    
    def _on_device_error(self, error_message: str):
        """Callback for device error"""
        self.root.after(0, lambda: self._set_status(f"Error: {error_message}", "red"))
    
    # =========================================================================
    # Utility Functions
    # =========================================================================
    
    def _toggle_plot_window(self):
        """Toggle plot window visibility"""
        self.plot_window.toggle()
    
    def _reconnect_device(self):
        """Reconnect to device"""
        self._set_status("Reconnecting...", "yellow")
        self.device.disconnect()
        
        if self.device.connect():
            self._set_status("Connected", "green")
        else:
            self._set_status("Connection failed", "red")
    
    def _show_device_info(self):
        """Show device information dialog"""
        caps = self.capabilities
        info = f"""Device: {caps.device_name}
Type: {caps.device_type}
Manufacturer: {caps.manufacturer}
Model: {caps.model}
Serial: {caps.serial_number}

Wavelength Range: {caps.wavelength_range[0]} - {caps.wavelength_range[1]} nm
Pixels: {caps.pixel_count}

Measurement Types: {', '.join(t.value for t in caps.measurement_types)}

Features:
- Auto Integration: {'Yes' if caps.supports_auto_integration else 'No'}
- Dark Correction: {'Yes' if caps.supports_dark_correction else 'No'}
- Continuous Mode: {'Yes' if caps.supports_continuous_mode else 'No'}
"""
        messagebox.showinfo("Device Information", info)
    
    def _show_shortcuts(self):
        """Show keyboard shortcuts"""
        shortcuts = """Keyboard Shortcuts:

F5 / Ctrl+M     Quick Measure
Ctrl+S          Save Measurement
Ctrl+P          Toggle Plot Window
Ctrl+E          Export Data
Ctrl+Q          Exit
Escape          Abort Measurement

Ctrl+1, 2, ...  Quick measure type 1, 2, ...
"""
        messagebox.showinfo("Keyboard Shortcuts", shortcuts)
    
    def _show_about(self):
        """Show about dialog"""
        about = """Spectral Measurement GUI

A portable, device-agnostic interface for spectral measurements.

Features:
• Works with any SpectralDevice implementation
• Threaded measurements (non-blocking)
• Detached plot window for performance
• Auto-repeat measurements
• Data export to CSV

Version: 1.0.0
"""
        messagebox.showinfo("About", about)
    
    def _on_close(self):
        """Handle window close"""
        # Stop auto-repeat
        self._stop_auto_repeat()
        
        # Disconnect device
        try:
            self.device.disconnect()
        except:
            pass
        
        # Close plot window
        self.plot_window.destroy()
        
        # Close main window
        self.root.destroy()
