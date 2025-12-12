#
#  Spectral GUI Framework
#
#  A portable, device-agnostic GUI framework for spectral measurements.
#
#  Usage:
#      from spectral_gui import SpectralMeasurementGUI, OSpRadDevice
#      
#      device = OSpRadDevice()
#      app = SpectralMeasurementGUI(root, device)
#

from .core import SpectralDevice, DeviceCapabilities, MeasurementResult
from .gui import SpectralMeasurementGUI, PlotWindow
from .devices import OSpRadDevice

__version__ = "1.0.0"

__all__ = [
    'SpectralDevice',
    'DeviceCapabilities', 
    'MeasurementResult',
    'SpectralMeasurementGUI',
    'PlotWindow',
    'OSpRadDevice',
]
