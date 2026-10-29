"""Decoded recording model, independent of CAN and the strict v1 live schema.

Unknown units/sign conventions remain explicit. Raw cells and recording order are
retained; only declared units produce normalized engineering values.
"""
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time
import math


# Column meanings supplied by the Phase 2 task, NOT independently verified OEM definitions.
COLUMNS = {
    'vhc_speed': ('speed_kmh', 'km/h'),
    'charging_signal': ('charging_status', None),
    'vhc_totalMile': ('odometer_km', 'km'),
    'hv_voltage': ('battery_voltage_v', 'V'),
    'hv_current': ('battery_current_measured_a', 'A'),
    'bcell_soc': ('soc_pct', '%'),
    'bcell_maxVoltage': ('cell_voltage_max_v', 'V'),
    'bcell_minVoltage': ('cell_voltage_min_v', 'V'),
    'bcell_maxTemp': ('cell_temperature_max_c', 'degC'),
    'bcell_minTemp': ('cell_temperature_min_c', 'degC'),
}
CANONICAL_UNITS = {target: unit for target, unit in COLUMNS.values()}
CONVERSIONS = {
    ('speed_kmh', 'm/s'): lambda v: v * 3.6,
    ('speed_kmh', 'mph'): lambda v: v * 1.609344,
    ('odometer_km', 'm'): lambda v: v / 1000,
    ('battery_voltage_v', 'mV'): lambda v: v / 1000,
    ('battery_current_measured_a', 'mA'): lambda v: v / 1000,
    ('soc_pct', 'fraction'): lambda v: v * 100,
    ('cell_voltage_max_v', 'mV'): lambda v: v / 1000,
    ('cell_voltage_min_v', 'mV'): lambda v: v / 1000,
    ('cell_temperature_max_c', 'K'): lambda v: v - 273.15,
    ('cell_temperature_min_c', 'K'): lambda v: v - 273.15,
}


def raw_value(value):
    """Lossless JSON-safe encoding of supported Excel cell value types."""
    if isinstance(value, (datetime, date, time)):
        return {'type': type(value).__name__, 'value': value.isoformat()}
    if isinstance(value, float) and not math.isfinite(value):
        return {'type': 'nonfinite', 'value': str(value)}
    return value


def numeric(value):
    if value is None or isinstance(value, bool) or (isinstance(value, str) and not value.strip()):
        return None
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return result if math.isfinite(result) else None


@dataclass
class DatasetProfile:
    dataset_id: str = 'Electric Vehicle Operation Data (user-supplied; edition unverified)'
    units: dict[str, str] = field(default_factory=dict)  # original column -> declared input unit
    time_unit: str = 'datetime'  # datetime/ISO only by default; numeric units must be declared
    time_basis: str = 'relative'
    current_convention: str = 'unknown'
    current_reference: str = ''  # distinct evidence for polarity; generic profile citation is insufficient
    calendar_leap: bool | None = None  # only needed for elapsed intervals crossing February
    unit_references: dict[str, str] = field(default_factory=dict)
    status_codes: dict[str, str] = field(default_factory=dict)
    status_reference: str = ''
    reference: str = ''  # caller-supplied documentation citation; not an automatic verification

    def __post_init__(self):
        if not isinstance(self.dataset_id, str) or not self.dataset_id.strip():
            raise ValueError('dataset_id must be nonempty')
        if self.time_unit not in ('datetime', 's', 'ms', 'us', 'MDDHHMMSS'):
            raise ValueError('time_unit must be datetime, s, ms, us or MDDHHMMSS')
        if self.time_unit == 'MDDHHMMSS' and self.time_basis != 'relative':
            raise ValueError('yearless MDDHHMMSS supports relative elapsed time only')
        if self.calendar_leap is not None and type(self.calendar_leap) is not bool:
            raise ValueError('calendar_leap must be true, false or null')
        if not isinstance(self.unit_references, dict) or any(k not in self.units or not isinstance(v, str) or not v.strip() for k, v in self.unit_references.items()):
            raise ValueError('unit references must cite declared source columns')
        if not isinstance(self.status_codes, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in self.status_codes.items()):
            raise ValueError('status_codes must map source code strings to labels')
        if self.status_codes and not self.status_reference:
            raise ValueError('status code definitions require a source reference')
        if self.time_basis not in ('relative', 'unix'):
            raise ValueError('time_basis must be relative or unix')
        if not isinstance(self.current_reference, str):
            raise ValueError('current_reference must be a documentation string')
        if self.current_convention not in ('unknown', 'positive_discharge', 'positive_charge'):
            raise ValueError('unknown current convention')
        if not isinstance(self.units, dict):
            raise ValueError('units must be a mapping from source column to input unit')
        for column, unit in self.units.items():
            if column not in COLUMNS or not isinstance(unit, str):
                raise ValueError(f'unsupported unit declaration: {column}')
            target, canonical = COLUMNS[column]
            if canonical is None or (unit != canonical and (target, unit) not in CONVERSIONS):
                raise ValueError(f'unsupported unit {unit!r} for {column}')

    def normalize(self, column, value):
        unit = self.units.get(column)
        value = numeric(value)
        if unit is None or value is None:
            return None
        target, canonical = COLUMNS[column]
        if unit == canonical:
            return value
        return CONVERSIONS[target, unit](value)


@dataclass
class Observation:
    row_number: int
    timestamp_s: float | None
    raw: dict  # includes original time and ALL original columns, including unknown columns
    values: dict[str, float | None]
    quality: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    derived: dict = field(default_factory=dict)

    def flag(self, signal, status, reason):
        issue = {'status': status, 'reason': reason}
        issues = self.quality.setdefault(signal, [])
        if issue not in issues:
            issues.append(issue)

    def statuses(self, signal):
        return {issue['status'] for issue in self.quality.get(signal, [])} or {'VALID'}

    def to_dict(self):
        return asdict(self)


@dataclass
class Recording:
    metadata: dict
    observations: list[Observation]

    @property
    def signals(self):
        return list(CANONICAL_UNITS)

    def duration_s(self):
        times = [row.timestamp_s for row in self.observations]
        if not times or any(t is None for t in times) or any(b < a for a, b in zip(times, times[1:])):
            return None
        return times[-1] - times[0]

    def canonical_samples(self):
        """Explicit bridge to Phase 1. Never pretend unknown current polarity is canonical.

        Invalid timestamps cannot enter the stricter live schema; no rows are
        silently omitted. Cell extrema remain in the richer recording envelope.
        """
        from .telemetry import TelemetrySample, validate_series
        samples = []
        convention = self.metadata['profile']['current_convention']
        for row in self.observations:
            if row.timestamp_s is None or row.timestamp_s < 0:
                raise ValueError('canonical v1 export requires valid timestamps for every observation')
            values = {key: row.values.get(key) for key in
                      ('speed_kmh', 'odometer_km', 'battery_voltage_v', 'soc_pct')}
            current = row.values.get('battery_current_measured_a')
            if convention != 'unknown' and current is not None:
                values['battery_current_a'] = -current if convention == 'positive_charge' else current
            flags = [f"{item['status']}:{signal}:{item['reason']}" for signal, issues in row.quality.items() for item in issues]
            samples.append(TelemetrySample(row.timestamp_s,
                           time_basis=self.metadata['normalized_time_basis'],
                           source=self.metadata['profile']['dataset_id'], quality_flags=flags, **values))
        return validate_series(samples)
