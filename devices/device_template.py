#
#  Device Template
#
#  Copy this file to create a new device adapter for the Spectral GUI Framework.
#
#  Steps to add a new device:
#  1. Copy this file to spectral_gui/devices/your_device.py
#  2. Rename the class to YourDevice
#  3. Implement all abstract methods
#  4. Add your device to devices/__init__.py
#  5. Add your device to main.py get_device() function
#

from typing import Dict, List, Optional, Any
from datetime import datetime

from ..core.device_interface import (
    SpectralDevice, DeviceCapabilities, DeviceStatus, 
    MeasurementType, SettingDefinition
)
from ..core.measurement_result import MeasurementResult, MeasurementUnit


class DeviceTemplate(SpectralDevice):
    """
    Template for implementing a new spectral device.
    
    Replace this docstring with a description of your device.
    """
    
    def __init__(self):
        super().__init__()
        
        # Initialize device-specific variables
        self._connected = False
        
        # TODO: Add your device-specific initialization
    
    # =========================================================================
    # Required Methods - You MUST implement these
    # =========================================================================
    
    def connect(self) -> bool:
        """
        Connect to your device.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.status = DeviceStatus.CONNECTING
            
            # TODO: Add your connection code here
            # Example:
            # self.device = YourDeviceLibrary.connect()
            
            self._connected = True
            self.status = DeviceStatus.CONNECTED
            return True
            
        except Exception as e:
            self.set_error(f"Connection failed: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from device"""
        try:
            # TODO: Add your disconnection code here
            # Example:
            # if self.device:
            #     self.device.close()
            pass
        except:
            pass
        
        self._connected = False
        self.status = DeviceStatus.DISCONNECTED
    
    def is_connected(self) -> bool:
        """Check if device is connected"""
        return self._connected
    
    def get_capabilities(self) -> DeviceCapabilities:
        """
        Return device capabilities.
        
        The GUI uses this to build the interface dynamically.
        """
        return DeviceCapabilities(
            # Device identification
            device_name="Your Device Name",
            device_type="Spectrometer",  # or "Spectroradiometer", etc.
            manufacturer="Your Company",
            model="MODEL-1000",
            serial_number="",  # Fill in after connection if available
            
            # Measurement capabilities
            measurement_types=[
                MeasurementType.IRRADIANCE,
                MeasurementType.RADIANCE,
                # Add other types your device supports
            ],
            wavelength_range=(380, 780),  # nm
            pixel_count=1024,  # Number of spectral pixels
            
            # Configurable settings
            # The GUI will create input widgets for each setting
            settings=[
                SettingDefinition(
                    name="integration_time",
                    display_name="Integration Time",
                    setting_type="int",  # int, float, bool, or choice
                    default_value=100,
                    min_value=1,
                    max_value=10000,
                    unit="ms",
                    tooltip="Time to collect light"
                ),
                SettingDefinition(
                    name="averages",
                    display_name="Averages",
                    setting_type="int",
                    default_value=1,
                    min_value=1,
                    max_value=100,
                    tooltip="Number of spectra to average"
                ),
                # Add more settings as needed
            ],
            
            # Features
            supports_auto_integration=True,
            supports_dark_correction=False,
            supports_continuous_mode=False,
            supports_triggering=False,
        )
    
    def configure(self, settings: Dict[str, Any]) -> bool:
        """
        Apply settings to device.
        
        Args:
            settings: Dictionary of setting_name -> value
            
        Returns:
            True if settings applied successfully
        """
        try:
            # TODO: Apply settings to your device
            # Example:
            # if 'integration_time' in settings:
            #     self.device.set_integration_time(settings['integration_time'])
            
            return True
            
        except Exception as e:
            self.set_error(f"Configure failed: {e}")
            return False
    
    def measure(self, measurement_type: MeasurementType) -> Optional[MeasurementResult]:
        """
        Perform a measurement.
        
        This is called from a background thread - safe to block.
        
        Args:
            measurement_type: Type of measurement to perform
            
        Returns:
            MeasurementResult if successful, None on error
        """
        if not self.is_connected():
            self.set_error("Device not connected")
            return None
        
        self.status = DeviceStatus.MEASURING
        
        try:
            # TODO: Perform measurement with your device
            # Example:
            # spectrum = self.device.get_spectrum()
            # wavelengths = self.device.get_wavelengths()
            
            # Placeholder data - replace with actual measurement
            wavelengths = [380 + i for i in range(401)]
            spectral_data = [0.0] * 401
            
            # Create result
            result = MeasurementResult(
                wavelengths=wavelengths,
                spectral_data=spectral_data,
                measurement_type=measurement_type.value,
                timestamp=datetime.now(),
                
                # Populate these based on measurement type
                luminance=0.0,  # cd/m² for radiance
                illuminance=0.0,  # lux for irradiance
                
                # Acquisition parameters
                integration_time_ms=100,
                num_scans=1,
                
                # Quality
                saturation_level=0.0,
                
                # Units
                spectral_unit=MeasurementUnit.WATTS_PER_SQM_NM,
                
                # Device info
                device_name="Your Device",
                device_serial="",
                device_info={
                    # Add any device-specific info
                },
            )
            
            self.status = DeviceStatus.CONNECTED
            return result
            
        except Exception as e:
            self.set_error(f"Measurement failed: {e}")
            self.status = DeviceStatus.ERROR
            return None
    
    def get_current_settings(self) -> Dict[str, Any]:
        """Get current device settings"""
        return {
            'integration_time': 100,
            'averages': 1,
            # Return current values for all settings
        }
    
    # =========================================================================
    # Optional Methods - Override if your device supports these
    # =========================================================================
    
    def abort_measurement(self) -> bool:
        """
        Abort an in-progress measurement.
        
        Override if your device supports measurement abortion.
        """
        # TODO: Implement if supported
        # Example:
        # self.device.abort()
        # return True
        return False
    
    def perform_calibration(self, calibration_type: str) -> bool:
        """
        Perform device calibration.
        
        Override if your device supports calibration.
        """
        # TODO: Implement if supported
        return False
    
    def self_test(self) -> tuple:
        """
        Perform device self-test.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        # TODO: Implement if supported
        return (True, "Self-test not implemented")


# ============================================================================
# Example: How to add this device to the application
# ============================================================================
#
# 1. Add to spectral_gui/devices/__init__.py:
#    from .your_device import YourDevice
#    __all__ = ['OSpRadDevice', 'YourDevice']
#
# 2. Add to spectral_gui/main.py get_device():
#    devices = {
#        'osprad': lambda: OSpRadDevice(),
#        'mock': create_mock_device,
#        'yourdevice': lambda: YourDevice(),  # Add this line
#    }
#
# 3. Run with:
#    python -m spectral_gui.main --device yourdevice
