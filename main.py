#!/usr/bin/env python3
#
#  Spectral Measurement Application - Main Entry Point
#
#  This is the main entry point for the portable spectral measurement GUI.
#  Edit this file to select which device to use.
#
#  Usage:
#      python main.py
#      python main.py --device osprad
#      python main.py --device mock
#

import tkinter as tk
from tkinter import messagebox
import argparse
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spectral_gui import SpectralMeasurementGUI, OSpRadDevice


def create_mock_device():
    """
    Create a mock device for testing without hardware.
    
    This demonstrates how easy it is to add a new device type!
    """
    from spectral_gui.core import SpectralDevice, DeviceCapabilities, MeasurementType, SettingDefinition
    from spectral_gui.core.device_interface import DeviceStatus
    from spectral_gui.core.measurement_result import MeasurementResult, MeasurementUnit
    from datetime import datetime
    import math
    import random
    
    class MockDevice(SpectralDevice):
        """Mock device for testing"""
        
        def __init__(self):
            super().__init__()
            self._connected = False
            self.int_time = 100
            self.num_scans = 10
        
        def connect(self) -> bool:
            self._connected = True
            self.status = DeviceStatus.CONNECTED
            return True
        
        def disconnect(self):
            self._connected = False
            self.status = DeviceStatus.DISCONNECTED
        
        def is_connected(self) -> bool:
            return self._connected
        
        def get_capabilities(self) -> DeviceCapabilities:
            return DeviceCapabilities(
                device_name="Mock Spectrometer",
                device_type="Mock",
                manufacturer="Test",
                model="MOCK-1000",
                serial_number="MOCK001",
                measurement_types=[MeasurementType.RADIANCE, MeasurementType.IRRADIANCE],
                wavelength_range=(380, 780),
                pixel_count=401,
                settings=[
                    SettingDefinition("integration_time", "Integration Time", "int", 100, 1, 10000, unit="ms"),
                    SettingDefinition("num_scans", "Number of Scans", "int", 10, 1, 100),
                ],
                supports_auto_integration=True,
            )
        
        def configure(self, settings):
            if 'integration_time' in settings:
                self.int_time = settings['integration_time']
            if 'num_scans' in settings:
                self.num_scans = settings['num_scans']
            return True
        
        def measure(self, measurement_type):
            import time
            self.status = DeviceStatus.MEASURING
            
            # Simulate measurement delay
            time.sleep(0.5 + random.random())
            
            # Generate mock spectrum (Gaussian peaks)
            wavelengths = [380 + i for i in range(401)]
            
            # Create a realistic-looking spectrum with multiple peaks
            data = []
            for wl in wavelengths:
                # Main peak around 550nm (green)
                val = 0.8 * math.exp(-0.5 * ((wl - 550) / 30) ** 2)
                # Secondary peak around 480nm (blue)
                val += 0.4 * math.exp(-0.5 * ((wl - 480) / 20) ** 2)
                # Third peak around 620nm (red)
                val += 0.6 * math.exp(-0.5 * ((wl - 620) / 25) ** 2)
                # Add some noise
                val += random.gauss(0, 0.02)
                data.append(max(0, val))
            
            # Calculate mock luminance
            luminance = sum(data) * 10 + random.gauss(0, 5)
            
            self.status = DeviceStatus.CONNECTED
            
            return MeasurementResult(
                wavelengths=wavelengths,
                spectral_data=data,
                measurement_type=measurement_type.value,
                timestamp=datetime.now(),
                luminance=luminance if measurement_type == MeasurementType.RADIANCE else 0,
                illuminance=luminance if measurement_type == MeasurementType.IRRADIANCE else 0,
                integration_time_ms=self.int_time,
                num_scans=self.num_scans,
                saturation_level=random.random() * 0.1,
                device_name="Mock Spectrometer",
                device_serial="MOCK001",
            )
        
        def get_current_settings(self):
            return {
                'integration_time': self.int_time,
                'num_scans': self.num_scans,
            }
    
    return MockDevice()


def get_device(device_type: str):
    """
    Factory function to create device based on type.
    
    Add your own devices here!
    """
    devices = {
        'osprad': lambda: OSpRadDevice(),
        'mock': create_mock_device,
        # Add more devices:
        # 'oceanoptics': lambda: OceanOpticsDevice(),
        # 'thorlabs': lambda: ThorlabsDevice(),
        # 'custom': lambda: YourCustomDevice(),
    }
    
    if device_type not in devices:
        available = ', '.join(devices.keys())
        raise ValueError(f"Unknown device type: {device_type}. Available: {available}")
    
    return devices[device_type]()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Spectral Measurement GUI')
    parser.add_argument('--device', '-d', type=str, default='osprad',
                        help='Device type: osprad, mock, or custom')
    parser.add_argument('--calibration', '-c', type=str, default='calibration_data.csv',
                        help='Calibration file path (for OSpRad)')
    
    args = parser.parse_args()
    
    # Create root window
    root = tk.Tk()
    
    try:
        # Create device
        print(f"Initializing device: {args.device}")
        
        if args.device == 'osprad':
            device = OSpRadDevice(calibration_file=args.calibration)
        else:
            device = get_device(args.device)
        
        # Connect to device
        print("Connecting to device...")
        if not device.connect():
            messagebox.showerror(
                "Connection Failed",
                f"Could not connect to {args.device} device.\n\n"
                f"Error: {device.last_error}\n\n"
                "Please check:\n"
                "• Device is connected\n"
                "• Correct drivers installed\n"
                "• No other software using the device"
            )
            # Still allow using with mock for testing
            if args.device != 'mock':
                if messagebox.askyesno("Use Mock Device?", 
                                       "Would you like to use a mock device for testing?"):
                    device = create_mock_device()
                    device.connect()
                else:
                    root.destroy()
                    return
        
        # Create GUI
        print("Starting GUI...")
        app = SpectralMeasurementGUI(root, device)
        
        # Run main loop
        root.mainloop()
        
    except Exception as e:
        messagebox.showerror("Error", f"Application error:\n{e}")
        raise


if __name__ == "__main__":
    main()
