#
#  Abstract Device Interface
#
#  Any spectral measurement device must implement this interface
#  to work with the portable GUI framework.
#

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class MeasurementType(Enum):
    """Standard measurement types supported by spectral devices"""
    RADIANCE = "radiance"
    IRRADIANCE = "irradiance"
    TRANSMITTANCE = "transmittance"
    REFLECTANCE = "reflectance"
    ABSORBANCE = "absorbance"
    RAW = "raw"


class DeviceStatus(Enum):
    """Standard device status values"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    MEASURING = "measuring"
    ERROR = "error"
    BUSY = "busy"


@dataclass
class SettingDefinition:
    """Definition of a configurable device setting"""
    name: str
    display_name: str
    setting_type: str  # 'int', 'float', 'bool', 'choice'
    default_value: Any
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    choices: Optional[List[Any]] = None  # For 'choice' type
    unit: str = ""
    tooltip: str = ""


@dataclass
class DeviceCapabilities:
    """
    Describes what a device can do.
    The GUI will be dynamically built based on these capabilities.
    """
    # Device identification
    device_name: str
    device_type: str
    manufacturer: str = ""
    model: str = ""
    serial_number: str = ""
    
    # Measurement capabilities
    measurement_types: List[MeasurementType] = field(default_factory=list)
    wavelength_range: tuple = (350, 850)  # (min_nm, max_nm)
    pixel_count: int = 288
    
    # Configurable settings
    settings: List[SettingDefinition] = field(default_factory=list)
    
    # Features
    supports_auto_integration: bool = True
    supports_dark_correction: bool = False
    supports_continuous_mode: bool = False
    supports_triggering: bool = False
    
    # Calibration
    requires_calibration: bool = False
    calibration_types: List[str] = field(default_factory=list)


class SpectralDevice(ABC):
    """
    Abstract base class for all spectral measurement devices.
    
    Implement this interface to make any spectral device work with
    the portable GUI framework.
    
    Example usage:
        class MyDevice(SpectralDevice):
            def connect(self) -> bool:
                # Your connection code
                pass
            # ... implement other methods
    """
    
    def __init__(self):
        self._status = DeviceStatus.DISCONNECTED
        self._last_error: str = ""
        self._callbacks: Dict[str, List[callable]] = {
            'status_changed': [],
            'measurement_complete': [],
            'error': [],
        }
    
    # =========================================================================
    # Abstract methods - MUST be implemented by all devices
    # =========================================================================
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the device.
        
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """
        Clean disconnect from device.
        Should release all resources and close connections.
        """
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if device is currently connected.
        
        Returns:
            True if connected and ready, False otherwise
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> DeviceCapabilities:
        """
        Return device capabilities.
        
        The GUI uses this information to dynamically build the interface.
        
        Returns:
            DeviceCapabilities object describing what the device can do
        """
        pass
    
    @abstractmethod
    def configure(self, settings: Dict[str, Any]) -> bool:
        """
        Apply settings to the device.
        
        Args:
            settings: Dictionary of setting_name -> value
            
        Returns:
            True if settings applied successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def measure(self, measurement_type: MeasurementType) -> Optional['MeasurementResult']:
        """
        Perform a measurement.
        
        This method may block for several seconds depending on integration time.
        The GUI will call this from a background thread.
        
        Args:
            measurement_type: Type of measurement to perform
            
        Returns:
            MeasurementResult object if successful, None on error
        """
        pass
    
    @abstractmethod
    def get_current_settings(self) -> Dict[str, Any]:
        """
        Get current device settings.
        
        Returns:
            Dictionary of current setting values
        """
        pass
    
    # =========================================================================
    # Optional methods - Override if device supports these features
    # =========================================================================
    
    def abort_measurement(self) -> bool:
        """
        Abort an in-progress measurement.
        
        Returns:
            True if abort successful, False if not supported or failed
        """
        return False
    
    def perform_calibration(self, calibration_type: str) -> bool:
        """
        Perform device calibration.
        
        Args:
            calibration_type: Type of calibration to perform
            
        Returns:
            True if calibration successful, False otherwise
        """
        return False
    
    def get_calibration_status(self) -> Dict[str, Any]:
        """
        Get calibration status.
        
        Returns:
            Dictionary with calibration information
        """
        return {'calibrated': False, 'message': 'Calibration not supported'}
    
    def self_test(self) -> tuple:
        """
        Perform device self-test.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        return (True, "Self-test not implemented")
    
    # =========================================================================
    # Status and error handling
    # =========================================================================
    
    @property
    def status(self) -> DeviceStatus:
        """Get current device status"""
        return self._status
    
    @status.setter
    def status(self, value: DeviceStatus):
        """Set device status and notify callbacks"""
        old_status = self._status
        self._status = value
        if old_status != value:
            self._notify('status_changed', value)
    
    @property
    def last_error(self) -> str:
        """Get last error message"""
        return self._last_error
    
    def set_error(self, message: str):
        """Set error state with message"""
        self._last_error = message
        self._status = DeviceStatus.ERROR
        self._notify('error', message)
    
    def clear_error(self):
        """Clear error state"""
        self._last_error = ""
        if self._status == DeviceStatus.ERROR:
            self._status = DeviceStatus.CONNECTED if self.is_connected() else DeviceStatus.DISCONNECTED
    
    # =========================================================================
    # Event callbacks
    # =========================================================================
    
    def register_callback(self, event: str, callback: callable):
        """
        Register a callback for device events.
        
        Events:
            - 'status_changed': Called when device status changes
            - 'measurement_complete': Called when measurement finishes
            - 'error': Called when an error occurs
        """
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def unregister_callback(self, event: str, callback: callable):
        """Unregister a callback"""
        if event in self._callbacks and callback in self._callbacks[event]:
            self._callbacks[event].remove(callback)
    
    def _notify(self, event: str, data: Any = None):
        """Notify all registered callbacks for an event"""
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"Callback error: {e}")
    
    # =========================================================================
    # Utility methods
    # =========================================================================
    
    def get_status_string(self) -> str:
        """Get human-readable status string"""
        status_messages = {
            DeviceStatus.DISCONNECTED: "Disconnected",
            DeviceStatus.CONNECTING: "Connecting...",
            DeviceStatus.CONNECTED: "Ready",
            DeviceStatus.MEASURING: "Measuring...",
            DeviceStatus.ERROR: f"Error: {self._last_error}",
            DeviceStatus.BUSY: "Busy",
        }
        return status_messages.get(self._status, "Unknown")
    
    def __enter__(self):
        """Context manager entry - connect"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - disconnect"""
        self.disconnect()
        return False
