#
#  Spectral GUI Framework - Core Module
#
#  Portable, modular GUI framework for spectral measurement devices
#

from .device_interface import SpectralDevice, DeviceCapabilities
from .measurement_result import MeasurementResult

__all__ = ['SpectralDevice', 'DeviceCapabilities', 'MeasurementResult']
