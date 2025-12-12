#
#  Measurement Result
#
#  Standard data format for all spectral measurements.
#  All devices must return data in this format.
#

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class MeasurementUnit(Enum):
    """Standard units for spectral measurements"""
    # Radiometric
    WATTS_PER_SQM_NM = "W/(m²·nm)"           # Spectral irradiance
    WATTS_PER_SR_SQM_NM = "W/(sr·m²·nm)"     # Spectral radiance
    
    # Photometric
    LUX = "lux"
    CD_PER_SQM = "cd/m²"
    LUMENS = "lm"
    
    # Dimensionless
    PERCENT = "%"
    ABSORBANCE_UNITS = "AU"
    COUNTS = "counts"
    
    # Other
    ARBITRARY = "a.u."


@dataclass
class MeasurementResult:
    """
    Standard measurement result format.
    
    All spectral devices must return data in this format to ensure
    compatibility with the portable GUI framework.
    """
    
    # =========================================================================
    # Required fields - Must always be populated
    # =========================================================================
    
    # Spectral data
    wavelengths: List[float]          # Wavelength array in nm
    spectral_data: List[float]        # Calibrated spectral values
    
    # Measurement info
    measurement_type: str             # 'radiance', 'irradiance', etc.
    timestamp: datetime = field(default_factory=datetime.now)
    
    # =========================================================================
    # Common fields - Populated when available
    # =========================================================================
    
    # Photometric values
    luminance: float = 0.0            # cd/m² for radiance
    illuminance: float = 0.0          # lux for irradiance
    
    # Acquisition parameters
    integration_time_ms: int = 0      # Integration time in milliseconds
    num_scans: int = 1                # Number of averaged scans
    
    # Quality indicators
    saturation_level: float = 0.0     # 0-1, fraction of saturated pixels
    signal_to_noise: float = 0.0      # SNR if available
    is_valid: bool = True             # False if measurement failed
    
    # Units
    spectral_unit: MeasurementUnit = MeasurementUnit.ARBITRARY
    luminance_unit: MeasurementUnit = MeasurementUnit.CD_PER_SQM
    
    # =========================================================================
    # Optional fields - Device-specific data
    # =========================================================================
    
    # Raw data (before calibration)
    raw_counts: Optional[List[float]] = None
    dark_reference: Optional[List[float]] = None
    
    # Device info
    device_name: str = ""
    device_serial: str = ""
    device_info: Dict[str, Any] = field(default_factory=dict)
    
    # Extra device-specific data
    extra_data: Dict[str, Any] = field(default_factory=dict)
    
    # Error info
    error_message: str = ""
    
    # =========================================================================
    # Computed properties
    # =========================================================================
    
    @property
    def pixel_count(self) -> int:
        """Number of spectral pixels"""
        return len(self.wavelengths)
    
    @property
    def wavelength_range(self) -> tuple:
        """(min_wavelength, max_wavelength) in nm"""
        if self.wavelengths:
            return (min(self.wavelengths), max(self.wavelengths))
        return (0, 0)
    
    @property
    def peak_wavelength(self) -> float:
        """Wavelength at maximum intensity"""
        if self.spectral_data and self.wavelengths:
            max_idx = self.spectral_data.index(max(self.spectral_data))
            return self.wavelengths[max_idx]
        return 0.0
    
    @property
    def peak_value(self) -> float:
        """Maximum spectral value"""
        if self.spectral_data:
            return max(self.spectral_data)
        return 0.0
    
    @property
    def integrated_value(self) -> float:
        """Integrated (total) spectral power"""
        if len(self.spectral_data) < 2 or len(self.wavelengths) < 2:
            return 0.0
        
        total = 0.0
        for i in range(len(self.spectral_data) - 1):
            dw = self.wavelengths[i + 1] - self.wavelengths[i]
            total += self.spectral_data[i] * dw
        return total
    
    @property
    def display_value(self) -> float:
        """Primary display value based on measurement type"""
        if self.measurement_type in ('radiance', 'r'):
            return self.luminance
        elif self.measurement_type in ('irradiance', 'i'):
            return self.illuminance
        return self.integrated_value
    
    @property
    def display_unit(self) -> str:
        """Unit string for primary display value"""
        if self.measurement_type in ('radiance', 'r'):
            return "cd/m²"
        elif self.measurement_type in ('irradiance', 'i'):
            return "lux"
        return str(self.spectral_unit.value)
    
    # =========================================================================
    # Methods
    # =========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'wavelengths': self.wavelengths,
            'spectral_data': self.spectral_data,
            'measurement_type': self.measurement_type,
            'timestamp': self.timestamp.isoformat(),
            'luminance': self.luminance,
            'illuminance': self.illuminance,
            'integration_time_ms': self.integration_time_ms,
            'num_scans': self.num_scans,
            'saturation_level': self.saturation_level,
            'device_name': self.device_name,
            'device_info': self.device_info,
            'extra_data': self.extra_data,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MeasurementResult':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)
    
    def to_csv_row(self, include_header: bool = False) -> str:
        """Generate CSV row for this measurement"""
        header = ""
        if include_header:
            wavelength_headers = ",".join(f"{w:.2f}" for w in self.wavelengths)
            header = f"timestamp,type,luminance,int_time_ms,num_scans,saturation,{wavelength_headers}\n"
        
        spectral_values = ",".join(f"{v:.6e}" for v in self.spectral_data)
        row = f"{self.timestamp.isoformat()},{self.measurement_type},{self.display_value:.6e},{self.integration_time_ms},{self.num_scans},{self.saturation_level:.4f},{spectral_values}"
        
        return header + row
    
    def get_summary(self) -> str:
        """Get human-readable summary"""
        return (
            f"Type: {self.measurement_type.capitalize()}\n"
            f"Value: {self.display_value:.4g} {self.display_unit}\n"
            f"Integration: {self.integration_time_ms}ms\n"
            f"Scans: {self.num_scans}\n"
            f"Saturation: {self.saturation_level:.1%}\n"
            f"Time: {self.timestamp.strftime('%H:%M:%S')}"
        )


@dataclass  
class MeasurementError:
    """Represents a measurement error"""
    error_type: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    recoverable: bool = True
    device_info: Dict[str, Any] = field(default_factory=dict)
    
    def to_result(self) -> MeasurementResult:
        """Convert to invalid MeasurementResult"""
        return MeasurementResult(
            wavelengths=[],
            spectral_data=[],
            measurement_type="error",
            is_valid=False,
            error_message=self.message,
            timestamp=self.timestamp,
        )
