#
#  Detached Plot Window
#
#  Separate window for spectrum display - much faster than embedded plot.
#  Uses matplotlib blitting for optimal performance.
#

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection
import matplotlib.colors as mcolors
from typing import List, Optional, Dict, Any, Tuple
import numpy as np
import math


def hcl_to_rgb(h: float, c: float, l: float) -> Tuple[float, float, float]:
    """
    Convert HCL (Hue-Chroma-Luminance) to RGB.
    
    HCL is a perceptually uniform color space based on CIELAB.
    
    Args:
        h: Hue in degrees [0, 360)
        c: Chroma [0, ~100+] (saturation-like)
        l: Luminance [0, 100]
        
    Returns:
        Tuple of (R, G, B) values in [0, 1] range
    """
    # Convert HCL to Lab
    h_rad = math.radians(h)
    a = c * math.cos(h_rad)
    b = c * math.sin(h_rad)
    
    # Lab to XYZ
    # D65 illuminant reference values
    Xn, Yn, Zn = 95.047, 100.0, 108.883
    
    fy = (l + 16) / 116
    fx = a / 500 + fy
    fz = fy - b / 200
    
    delta = 6 / 29
    
    def f_inv(t):
        if t > delta:
            return t ** 3
        else:
            return 3 * delta ** 2 * (t - 4 / 29)
    
    X = Xn * f_inv(fx)
    Y = Yn * f_inv(fy)
    Z = Zn * f_inv(fz)
    
    # XYZ to sRGB (D65)
    X /= 100
    Y /= 100
    Z /= 100
    
    R =  3.2404542 * X - 1.5371385 * Y - 0.4985314 * Z
    G = -0.9692660 * X + 1.8760108 * Y + 0.0415560 * Z
    B =  0.0556434 * X - 0.2040259 * Y + 1.0572252 * Z
    
    # Apply sRGB gamma correction
    def gamma_correct(c):
        if c <= 0.0031308:
            return 12.92 * c
        else:
            return 1.055 * (c ** (1 / 2.4)) - 0.055
    
    R = gamma_correct(R)
    G = gamma_correct(G)
    B = gamma_correct(B)
    
    # Clamp to [0, 1]
    R = max(0, min(1, R))
    G = max(0, min(1, G))
    B = max(0, min(1, B))
    
    return (R, G, B)


def wavelength_to_rgb(wavelength: float, gamma: float = 0.8) -> Tuple[float, float, float]:
    """
    Convert wavelength (nm) to RGB color using HCL color space.
    
    Maps visible spectrum wavelengths to perceptually uniform HCL colors,
    then converts to RGB for display.
    
    Args:
        wavelength: Wavelength in nanometers (380-780nm for visible light)
        gamma: Unused, kept for API compatibility
        
    Returns:
        Tuple of (R, G, B) values in [0, 1] range
    """
    wavelength = float(wavelength)
    
    # Clamp to visible range
    if wavelength < 380:
        wavelength = 380
    if wavelength > 780:
        wavelength = 780
    
    # Map wavelength to hue (reversed: violet=300°, red=0°)
    # Visible spectrum: 380nm (violet) -> 780nm (red)
    # HCL Hue: ~300° (violet/purple) -> ~0° (red)
    # Using a mapping that follows the natural spectrum
    
    if wavelength < 440:
        # Violet to Blue (380-440nm) -> Hue 285° to 260°
        t = (wavelength - 380) / (440 - 380)
        hue = 285 - t * 25
        chroma = 60 + t * 40  # Increasing chroma
        luminance = 30 + t * 25  # Increasing luminance
    elif wavelength < 490:
        # Blue to Cyan (440-490nm) -> Hue 260° to 210°
        t = (wavelength - 440) / (490 - 440)
        hue = 260 - t * 50
        chroma = 100
        luminance = 55 + t * 15
    elif wavelength < 510:
        # Cyan to Green-ish (490-510nm) -> Hue 210° to 160°
        t = (wavelength - 490) / (510 - 490)
        hue = 210 - t * 50
        chroma = 100 - t * 10
        luminance = 70 + t * 10
    elif wavelength < 580:
        # Green to Yellow (510-580nm) -> Hue 160° to 85°
        t = (wavelength - 510) / (580 - 510)
        hue = 160 - t * 75
        chroma = 90 + t * 10
        luminance = 80 + t * 15
    elif wavelength < 645:
        # Yellow to Orange (580-645nm) -> Hue 85° to 40°
        t = (wavelength - 580) / (645 - 580)
        hue = 85 - t * 45
        chroma = 100
        luminance = 95 - t * 20
    else:
        # Orange to Red (645-780nm) -> Hue 40° to 15°
        t = (wavelength - 645) / (780 - 645)
        hue = 40 - t * 25
        chroma = 100 - t * 30  # Decreasing chroma at far red
        luminance = 75 - t * 35  # Decreasing luminance at far red
    
    # Apply intensity falloff at edges of visible spectrum
    if wavelength < 420:
        intensity = 0.3 + 0.7 * (wavelength - 380) / (420 - 380)
        chroma *= intensity
        luminance *= intensity
    elif wavelength > 700:
        intensity = 0.3 + 0.7 * (780 - wavelength) / (780 - 700)
        chroma *= intensity
        luminance *= intensity
    
    return hcl_to_rgb(hue, chroma, luminance)


class PlotWindow(tk.Toplevel):
    """
    Detached plot window for spectrum display.
    
    Features:
    - Fast updates using blitting
    - Zoom/pan with matplotlib toolbar
    - Export to image/CSV
    - Multiple spectra overlay
    - Dark theme option
    - Visible spectrum color background
    """
    
    def __init__(self, parent, title: str = "Spectrum Plot"):
        super().__init__(parent)
        self.title(title)
        self.geometry("800x600")
        self.minsize(600, 400)
        
        # Configuration
        self.dark_theme = False
        self.show_grid = True
        self.autoscale_y = True
        self.show_spectrum_colors = True  # Show visible spectrum background
        self.spectrum_alpha = 0.3  # Transparency of spectrum background
        
        # Data storage
        self.current_wavelengths: List[float] = []
        self.current_data: List[float] = []
        self.overlay_spectra: Dict[str, tuple] = {}  # name -> (wavelengths, data, color)
        
        # Plot objects for blitting
        self.main_line = None
        self.overlay_lines: Dict[str, Any] = {}
        self.background = None
        self.spectrum_bars = None  # Spectrum color bars
        
        # Build UI
        self._create_menu()
        self._create_toolbar()
        self._create_plot()
        self._create_info_bar()
        
        # Handle close button
        self.protocol("WM_DELETE_WINDOW", self.hide)
        
        # Bind resize event for background update
        self.bind('<Configure>', self._on_resize)
    
    def _create_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export Image...", command=self.export_image, accelerator="Ctrl+E")
        file_menu.add_command(label="Export Data...", command=self.export_data, accelerator="Ctrl+D")
        file_menu.add_separator()
        file_menu.add_command(label="Close", command=self.hide)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        
        self.grid_var = tk.BooleanVar(value=True)
        view_menu.add_checkbutton(label="Show Grid", variable=self.grid_var, command=self._toggle_grid)
        
        self.autoscale_var = tk.BooleanVar(value=True)
        view_menu.add_checkbutton(label="Auto-scale Y", variable=self.autoscale_var, command=self._toggle_autoscale)
        
        self.spectrum_colors_var = tk.BooleanVar(value=True)
        view_menu.add_checkbutton(label="Show Spectrum Colors", variable=self.spectrum_colors_var, 
                                   command=self._toggle_spectrum_colors)
        
        view_menu.add_separator()
        view_menu.add_command(label="Reset Zoom", command=self.reset_zoom)
        
        # Overlay menu
        overlay_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Overlay", menu=overlay_menu)
        overlay_menu.add_command(label="Save Current as Reference", command=self._save_as_reference)
        overlay_menu.add_command(label="Clear All Overlays", command=self.clear_overlays)
        
        # Keyboard shortcuts
        self.bind_all('<Control-e>', lambda e: self.export_image())
        self.bind_all('<Control-d>', lambda e: self.export_data())
    
    def _create_toolbar(self):
        """Create toolbar with quick actions"""
        toolbar_frame = ttk.Frame(self)
        toolbar_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Zoom controls
        ttk.Button(toolbar_frame, text="🔍+", width=3, command=self._zoom_in).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar_frame, text="🔍-", width=3, command=self._zoom_out).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar_frame, text="Reset", command=self.reset_zoom).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Display options
        ttk.Label(toolbar_frame, text="Y-axis:").pack(side=tk.LEFT, padx=2)
        self.yscale_var = tk.StringVar(value="linear")
        yscale_combo = ttk.Combobox(toolbar_frame, textvariable=self.yscale_var, 
                                     values=["linear", "log"], width=8, state="readonly")
        yscale_combo.pack(side=tk.LEFT, padx=2)
        yscale_combo.bind('<<ComboboxSelected>>', self._change_yscale)
        
        # Peak info
        ttk.Separator(toolbar_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        self.peak_label = ttk.Label(toolbar_frame, text="Peak: --")
        self.peak_label.pack(side=tk.LEFT, padx=5)
    
    def _create_plot(self):
        """Create matplotlib figure and canvas"""
        # Create figure with appropriate style
        self.figure = Figure(figsize=(8, 5), dpi=100, facecolor='white')
        self.ax = self.figure.add_subplot(111)
        
        # Configure axes
        self.ax.set_xlabel('Wavelength (nm)', fontsize=10)
        self.ax.set_ylabel('Spectral Intensity', fontsize=10)
        self.ax.set_title('Spectrum', fontsize=12)
        self.ax.grid(True, alpha=0.3)
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.figure, self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add matplotlib navigation toolbar
        toolbar_frame = ttk.Frame(self)
        toolbar_frame.pack(fill=tk.X)
        self.nav_toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.nav_toolbar.update()
        
        # Initial draw
        self.canvas.draw()
    
    def _create_info_bar(self):
        """Create info bar at bottom"""
        info_frame = ttk.Frame(self)
        info_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.info_label = ttk.Label(info_frame, text="No data", font=('TkDefaultFont', 9))
        self.info_label.pack(side=tk.LEFT)
        
        self.coords_label = ttk.Label(info_frame, text="", font=('TkDefaultFont', 9))
        self.coords_label.pack(side=tk.RIGHT)
        
        # Mouse motion tracking for coordinates
        self.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)
    
    def update_spectrum(self, wavelengths: List[float], data: List[float], 
                        measurement_type: str = "", info: str = ""):
        """
        Update the displayed spectrum.
        
        Uses blitting for fast updates when possible.
        
        Args:
            wavelengths: Wavelength array
            data: Spectral data array
            measurement_type: Type of measurement for labeling
            info: Additional info string to display
        """
        self.current_wavelengths = wavelengths
        self.current_data = data
        
        if not wavelengths or not data:
            return
        
        # Update or create main line
        if self.main_line is None:
            # First plot - full draw with spectrum background
            self.ax.set_xlim(min(wavelengths), max(wavelengths))
            self._update_ylim()
            self._draw_spectrum_background()  # Draw spectrum colors first (behind)
            self.main_line, = self.ax.plot(wavelengths, data, 'b-', linewidth=1.5, label='Current', zorder=2)
            self.canvas.draw()
            self.background = self.canvas.copy_from_bbox(self.ax.bbox)
        else:
            # Update with blitting for speed
            try:
                self.canvas.restore_region(self.background)
                self.main_line.set_data(wavelengths, data)
                
                if self.autoscale_var.get():
                    self._update_ylim()
                    # Redraw spectrum background when ylim changes
                    self._draw_spectrum_background()
                    self.canvas.draw()
                    self.background = self.canvas.copy_from_bbox(self.ax.bbox)
                
                self.ax.draw_artist(self.main_line)
                
                # Draw overlay lines
                for line in self.overlay_lines.values():
                    self.ax.draw_artist(line)
                
                self.canvas.blit(self.ax.bbox)
            except Exception:
                # Fallback to full redraw
                self.main_line.set_data(wavelengths, data)
                if self.autoscale_var.get():
                    self._update_ylim()
                self._draw_spectrum_background()
                self.canvas.draw_idle()
        
        # Update labels
        y_label = self._get_ylabel(measurement_type)
        self.ax.set_ylabel(y_label)
        
        # Update peak info
        if data:
            peak_idx = np.argmax(data)
            peak_wl = wavelengths[peak_idx]
            peak_val = data[peak_idx]
            self.peak_label.config(text=f"Peak: {peak_wl:.1f}nm @ {peak_val:.3e}")
        
        # Update info bar
        self.info_label.config(text=info if info else f"Points: {len(data)}")
    
    def _get_ylabel(self, measurement_type: str) -> str:
        """Get appropriate Y-axis label"""
        labels = {
            'radiance': 'Spectral Radiance (W/sr·m²·nm)',
            'r': 'Spectral Radiance (W/sr·m²·nm)',
            'irradiance': 'Spectral Irradiance (W/m²·nm)',
            'i': 'Spectral Irradiance (W/m²·nm)',
            'transmittance': 'Transmittance (%)',
            'reflectance': 'Reflectance (%)',
            'absorbance': 'Absorbance (AU)',
        }
        return labels.get(measurement_type.lower(), 'Intensity')
    
    def _update_ylim(self):
        """Update Y-axis limits based on data"""
        all_data = list(self.current_data)
        for _, (_, d, _) in self.overlay_spectra.items():
            all_data.extend(d)
        
        if all_data:
            ymin = min(all_data)
            ymax = max(all_data)
            margin = (ymax - ymin) * 0.1 if ymax != ymin else 0.1
            self.ax.set_ylim(ymin - margin, ymax + margin)
    
    def add_overlay(self, name: str, wavelengths: List[float], data: List[float], color: str = 'red'):
        """Add an overlay spectrum"""
        self.overlay_spectra[name] = (wavelengths, data, color)
        
        if name in self.overlay_lines:
            self.overlay_lines[name].set_data(wavelengths, data)
        else:
            line, = self.ax.plot(wavelengths, data, color=color, linestyle='--', 
                                  linewidth=1, alpha=0.7, label=name)
            self.overlay_lines[name] = line
        
        self.ax.legend(loc='upper right', fontsize=8)
        self.canvas.draw_idle()
        
        # Update background for blitting
        self.background = self.canvas.copy_from_bbox(self.ax.bbox)
    
    def remove_overlay(self, name: str):
        """Remove an overlay spectrum"""
        if name in self.overlay_spectra:
            del self.overlay_spectra[name]
        
        if name in self.overlay_lines:
            self.overlay_lines[name].remove()
            del self.overlay_lines[name]
        
        self.ax.legend(loc='upper right', fontsize=8)
        self.canvas.draw_idle()
    
    def clear_overlays(self):
        """Clear all overlay spectra"""
        for line in self.overlay_lines.values():
            line.remove()
        self.overlay_lines.clear()
        self.overlay_spectra.clear()
        self.ax.legend(loc='upper right', fontsize=8)
        self.canvas.draw_idle()
    
    def _save_as_reference(self):
        """Save current spectrum as reference overlay"""
        if not self.current_data:
            messagebox.showwarning("No Data", "No spectrum to save as reference")
            return
        
        name = f"Reference {len(self.overlay_spectra) + 1}"
        colors = ['red', 'green', 'orange', 'purple', 'brown']
        color = colors[len(self.overlay_spectra) % len(colors)]
        
        self.add_overlay(name, self.current_wavelengths.copy(), 
                        self.current_data.copy(), color)
    
    def reset_zoom(self):
        """Reset to full view"""
        if self.current_wavelengths:
            self.ax.set_xlim(min(self.current_wavelengths), max(self.current_wavelengths))
            self._update_ylim()
            self._draw_spectrum_background()
        self.canvas.draw_idle()
        
        # Update background
        self.background = self.canvas.copy_from_bbox(self.ax.bbox)
    
    def _zoom_in(self):
        """Zoom in on center"""
        xlim = self.ax.get_xlim()
        xrange = xlim[1] - xlim[0]
        center = (xlim[0] + xlim[1]) / 2
        new_range = xrange * 0.7
        self.ax.set_xlim(center - new_range/2, center + new_range/2)
        self._draw_spectrum_background()
        self.canvas.draw_idle()
    
    def _zoom_out(self):
        """Zoom out from center"""
        xlim = self.ax.get_xlim()
        xrange = xlim[1] - xlim[0]
        center = (xlim[0] + xlim[1]) / 2
        new_range = xrange * 1.4
        self.ax.set_xlim(center - new_range/2, center + new_range/2)
        self._draw_spectrum_background()
        self.canvas.draw_idle()
    
    def _toggle_grid(self):
        """Toggle grid visibility"""
        self.ax.grid(self.grid_var.get(), alpha=0.3)
        self.canvas.draw_idle()
    
    def _toggle_autoscale(self):
        """Toggle Y-axis autoscaling"""
        self.autoscale_y = self.autoscale_var.get()
    
    def _toggle_spectrum_colors(self):
        """Toggle visible spectrum color background"""
        self.show_spectrum_colors = self.spectrum_colors_var.get()
        self._draw_spectrum_background()
        self.canvas.draw_idle()
    
    def _draw_spectrum_background(self):
        """Draw or remove the visible spectrum color background"""
        # Remove existing spectrum bars if present
        if self.spectrum_bars is not None:
            self.spectrum_bars.remove()
            self.spectrum_bars = None
        
        if not self.show_spectrum_colors:
            return
        
        # Get current x-axis limits
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        
        # Create colored bars for each wavelength in visible spectrum
        visible_start = max(380, xlim[0])
        visible_end = min(780, xlim[1])
        
        if visible_start >= visible_end:
            return
        
        # Generate colors for the visible spectrum as an image
        num_colors = int(visible_end - visible_start)
        wavelengths = np.linspace(visible_start, visible_end, num_colors)
        
        # Create RGBA array for the spectrum gradient
        colors = np.array([wavelength_to_rgb(wl) + (self.spectrum_alpha,) for wl in wavelengths])
        # Reshape to 2D image (1 row, N columns, 4 channels for RGBA)
        spectrum_image = colors.reshape(1, -1, 4)
        
        # Use imshow to display the gradient as background
        self.spectrum_bars = self.ax.imshow(
            spectrum_image,
            aspect='auto',
            extent=[visible_start, visible_end, ylim[0], ylim[1]],
            origin='lower',
            zorder=0  # Behind everything else
        )
    
    def _change_yscale(self, event=None):
        """Change Y-axis scale (linear/log)"""
        self.ax.set_yscale(self.yscale_var.get())
        self.canvas.draw_idle()
    
    def _on_mouse_move(self, event):
        """Update coordinates display on mouse move"""
        if event.inaxes == self.ax and event.xdata is not None:
            self.coords_label.config(text=f"λ={event.xdata:.1f}nm, I={event.ydata:.3e}")
    
    def _on_resize(self, event):
        """Handle window resize - update background for blitting"""
        try:
            self.figure.tight_layout()
            self.canvas.draw()
            self.background = self.canvas.copy_from_bbox(self.ax.bbox)
        except Exception:
            pass
    
    def export_image(self):
        """Export plot to image file"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[
                ("PNG files", "*.png"),
                ("PDF files", "*.pdf"),
                ("SVG files", "*.svg"),
                ("All files", "*.*")
            ]
        )
        if filepath:
            self.figure.savefig(filepath, dpi=150, bbox_inches='tight')
            messagebox.showinfo("Exported", f"Image saved to:\n{filepath}")
    
    def export_data(self):
        """Export spectrum data to CSV"""
        if not self.current_data:
            messagebox.showwarning("No Data", "No spectrum data to export")
            return
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filepath:
            with open(filepath, 'w') as f:
                f.write("Wavelength (nm),Intensity\n")
                for wl, val in zip(self.current_wavelengths, self.current_data):
                    f.write(f"{wl:.2f},{val:.6e}\n")
            messagebox.showinfo("Exported", f"Data saved to:\n{filepath}")
    
    def show(self):
        """Show the window"""
        self.deiconify()
        self.lift()
        self.focus_force()
    
    def hide(self):
        """Hide the window (don't destroy)"""
        self.withdraw()
    
    def toggle(self):
        """Toggle window visibility"""
        if self.winfo_viewable():
            self.hide()
        else:
            self.show()
