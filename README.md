# Spectral GUI - Portable Spectral Measurement Application

A modern, device-agnostic Python GUI application for spectral measurements with focus on portability, extensibility, and user experience.

## 🌟 Features

### Core Capabilities
- **Device-Agnostic Architecture**: Works with any spectral measurement device through abstract interface
- **Modern Tabbed Interface**: Organized workflow with 4 main tabs (Measure, Settings, Auto-Repeat, Data)
- **Detached Plot Window**: High-performance spectrum visualization with matplotlib blitting
- **Non-Blocking Measurements**: Threading-based approach keeps UI responsive during measurements
- **Visible Spectrum Colors**: Perceptually uniform HCL color gradient background (380-780nm)

### Measurement Features
- Real-time spectrum plotting with zoom/pan capabilities
- Auto-repeat mode for continuous monitoring
- Multiple measurement types (Radiance, Irradiance, Transmittance, etc.)
- Peak wavelength detection
- Luminance calculation (for supported devices)
- Measurement history and data management

### Plot Window Features
- Fast updates using matplotlib blitting optimization
- Spectrum overlay for comparison (save multiple references)
- Visible spectrum color background with HCL color space
- Export to PNG/PDF images
- Export data to CSV
- Grid and autoscale toggles
- Mouse coordinate tracking
- Keyboard shortcuts

### User Experience
- Progress indicators with percentage and time estimates
- Status bar with real-time feedback
- Keyboard shortcuts (Ctrl+M: measure, Ctrl+S: save, etc.)
- Modern ttk widgets with consistent styling
- Error handling and user-friendly messages

## 📋 Requirements

### Python Version
- Python 3.8 or higher

### Dependencies
```bash
tkinter          # GUI framework (usually included with Python)
matplotlib       # Plotting and visualization
numpy            # Numerical computations
pyserial         # Serial communication (for hardware devices)
```

### Platform Support
- **Windows**: Full support
- **Linux**: Full support
- **macOS**: Full support
- **Android**: Partial support (requires usbserial4a for USB devices)

## 🚀 Installation

### 1. Clone or Download
```bash
cd /path/to/your/project
```

### 2. Install Dependencies
```bash
pip install matplotlib numpy pyserial
```

Or using a virtual environment (recommended):
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install matplotlib numpy pyserial
```

### 3. Verify Installation
```bash
python -m spectral_gui.main --device mock
```

## 📖 Usage

### Basic Usage

#### With Mock Device (for testing)
```bash
python -m spectral_gui.main --device mock
```

#### With OSpRad Hardware
```bash
python -m spectral_gui.main --device osprad
```

The application will automatically detect available serial ports and connect to your device.

### GUI Workflow

#### 1. **Measure Tab**
- Configure measurement parameters:
  - **Integration Time**: Exposure time in milliseconds
  - **Number of Scans**: Averaging count for noise reduction
  - **Measurement Type**: Select radiance, irradiance, etc.
- Click **"Start Measurement"** (Ctrl+M) or press button
- Monitor progress in status bar
- View real-time spectrum in plot window
- Save measurements to history

#### 2. **Settings Tab**
- Configure device-specific settings
- Adjust integration time and scan count
- Settings are dynamically generated based on device capabilities

#### 3. **Auto-Repeat Tab**
- Enable continuous measurement mode
- Set repeat interval (seconds)
- Useful for monitoring time-varying sources
- Start/Stop controls with visual feedback

#### 4. **Data Tab**
- View measurement history table
- Select and review past measurements
- Export selected data to CSV
- Clear history when needed

### Plot Window

Open the plot window from **View → Show Plot** or press **Ctrl+P**.

**Features:**
- **Zoom/Pan**: Use toolbar or zoom buttons
- **Grid**: Toggle via View menu
- **Spectrum Colors**: Show/hide visible spectrum background
- **Overlay**: Save current spectrum as reference overlay
- **Export**: Save plot as image (Ctrl+E) or data as CSV (Ctrl+D)

**Keyboard Shortcuts:**
- `Ctrl+E` - Export image
- `Ctrl+D` - Export data
- Mouse hover - Show wavelength and intensity coordinates

## 🔧 Device Support

### Currently Supported

#### 1. OSpRad (Open Source Spectroradiometer)
- Full support for radiance and irradiance measurements
- Automatic calibration loading from `calibration_data.csv`
- 288-pixel sensor (340-850nm typical range)
- Serial communication via USB

#### 2. Mock Device
- Virtual device for testing without hardware
- Generates realistic spectrum data with Gaussian peaks
- Useful for GUI development and testing

### Adding New Devices

The modular architecture makes it easy to add support for new devices:

1. **Create Device Adapter** (see `spectral_gui/devices/device_template.py`)
2. **Implement SpectralDevice Interface**:
   - `connect()` - Establish communication
   - `disconnect()` - Clean up connection
   - `measure()` - Perform measurement and return MeasurementResult
   - `configure()` - Apply settings
   - `get_capabilities()` - Describe device features
3. **Register Device** in `main.py`

Example minimal device:
```python
from spectral_gui.core import SpectralDevice, DeviceCapabilities, MeasurementResult

class MyDevice(SpectralDevice):
    def connect(self) -> bool:
        # Your connection code
        return True
    
    def measure(self, settings: dict) -> MeasurementResult:
        # Your measurement code
        wavelengths = [380, 390, 400, ...]  # nm
        data = [0.1, 0.15, 0.2, ...]        # intensity
        return MeasurementResult(
            wavelengths=wavelengths,
            spectral_data=data,
            measurement_type="radiance"
        )
    
    def get_capabilities(self) -> DeviceCapabilities:
        return DeviceCapabilities(
            device_name="My Spectrometer",
            device_type="spectrometer",
            wavelength_range=(350, 850)
        )
```

## 📁 Project Structure

```
spectral_gui/
├── __init__.py                 # Package initialization
├── main.py                     # Entry point and device selection
│
├── core/                       # Core abstractions
│   ├── __init__.py
│   ├── device_interface.py     # SpectralDevice ABC and enums
│   └── measurement_result.py   # MeasurementResult dataclass
│
├── devices/                    # Device implementations
│   ├── __init__.py
│   ├── device_template.py      # Template for new devices
│   └── osprad_device.py        # OSpRad implementation
│
└── gui/                        # User interface
    ├── __init__.py
    ├── main_window.py          # Main tabbed interface
    └── plot_window.py          # Detached plot window
```

## 🎨 Customization

### Color Space
The spectrum background uses **HCL (Hue-Chroma-Luminance)** color space for perceptually uniform colors. Edit `wavelength_to_rgb()` in `plot_window.py` to customize color mapping.

### UI Theme
Modify `_apply_theme()` in `main_window.py` to customize colors, fonts, and widget styles.

### Keyboard Shortcuts
Edit `_setup_keyboard_shortcuts()` in `main_window.py` to add or modify shortcuts.

## 🔍 Troubleshooting

### Device Not Found
- Verify USB connection
- Check serial port permissions (Linux: add user to `dialout` group)
- Try running with admin/sudo privileges
- Verify correct device driver installation

### Import Errors
```bash
# Ensure you're running as a module
python -m spectral_gui.main

# Not as a script
python spectral_gui/main.py  # ❌ Won't work
```

### Performance Issues
- Reduce update frequency in auto-repeat mode
- Disable spectrum color background if plotting is slow
- Close unused plot overlays
- Reduce integration time for faster measurements

### Calibration File Not Found (OSpRad)
Place `calibration_data.csv` in the project root directory with format:
```csv
wavelength,responsivity
340,0.0123
341,0.0125
...
```

## 🤝 Contributing

### Adding Features
1. Follow the existing code structure
2. Use type hints throughout
3. Document all public methods and classes
4. Test with both mock and real devices

### Code Style
- PEP 8 compliant
- Use dataclasses for structured data
- Prefer composition over inheritance
- Keep methods focused and single-purpose

## 📄 License

This project is designed for educational and research purposes. Check individual device implementations for hardware-specific license requirements.

## 🙏 Acknowledgments

- **OSpRad**: Open Source Spectroradiometer project
- **matplotlib**: Excellent plotting library
- **tkinter**: Python's standard GUI framework
- **HCL Color Space**: Based on CIELAB perceptually uniform color space

## 📧 Support

For issues, questions, or contributions:
1. Check existing documentation
2. Test with mock device to isolate hardware vs software issues
3. Review error messages in console output
4. Consult device-specific documentation

## 🔄 Version History

### Current Version
- Modular, device-agnostic architecture
- HCL color space for spectrum visualization
- Threading-based non-blocking measurements
- Auto-repeat mode
- Measurement history management
- Full keyboard shortcut support
- Export capabilities (CSV, PNG, PDF)

---

**Happy Measuring! 🌈**
