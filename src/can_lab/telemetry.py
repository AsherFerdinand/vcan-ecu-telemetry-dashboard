"""Transport-independent schema v1. Current is positive during discharge.

Samples are sparse observations, not a forward-filled vehicle state. Timestamps
are seconds in an explicit unix or relative time basis. SOC is percent.
"""
from dataclasses import asdict, dataclass, field
import math
from typing import Iterable

SIGNALS = {
    'speed_kmh': (-1, 350), 'rpm': (0, 25000),
    'battery_voltage_v': (0, 1500), 'battery_current_a': (-3000, 3000),
    'soc_pct': (0, 100), 'battery_temperature_c': (-50, 100),
    'ambient_temperature_c': (-80, 80), 'power_kw': (-2000, 2000),
    'odometer_km': (0, 10_000_000),
}


def number(value, name):
    if isinstance(value, bool):
        raise ValueError(f'{name}: boolean is not a number')
    try:
        result = float(value)
    except (ValueError, TypeError) as error:
        raise ValueError(f'{name}: expected numeric value') from error
    if not math.isfinite(result):
        raise ValueError(f'{name}: must be finite')
    return result


@dataclass
class TelemetrySample:
    timestamp_s: float
    time_basis: str = 'relative'
    source: str = 'unspecified'
    schema_version: int = 1
    speed_kmh: float | None = None
    rpm: float | None = None
    battery_voltage_v: float | None = None
    battery_current_a: float | None = None
    soc_pct: float | None = None
    battery_temperature_c: float | None = None
    ambient_temperature_c: float | None = None
    power_kw: float | None = None
    odometer_km: float | None = None
    quality_flags: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.timestamp_s = number(self.timestamp_s, 'timestamp_s')
        if self.timestamp_s < 0:
            raise ValueError('timestamp_s must be nonnegative')
        if self.time_basis not in ('relative', 'unix'):
            raise ValueError('time_basis must be relative or unix')
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError('unsupported schema_version')
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError('source must be nonempty')
        if not isinstance(self.quality_flags, list) or not all(isinstance(x, str) for x in self.quality_flags):
            raise ValueError('quality_flags must be a list of strings')
        self.quality_flags = list(self.quality_flags)
        for name, (low, high) in SIGNALS.items():
            value = getattr(self, name)
            if value is not None:
                value = number(value, name)
                setattr(self, name, value)
                if not low <= value <= high:
                    flag = f'out_of_range:{name}'
                    if flag not in self.quality_flags:
                        self.quality_flags.append(flag)
        if not any(getattr(self, key) is not None for key in SIGNALS):
            if 'no_signals' not in self.quality_flags:
                self.quality_flags.append('no_signals')

    def to_dict(self):
        return asdict(self)


def validate_series(samples: Iterable[TelemetrySample], max_gap_s: float | None = None):
    """Reject clock reversals/mixed bases; equal timestamps are valid CAN events."""
    if max_gap_s is not None and (not math.isfinite(max_gap_s) or max_gap_s <= 0):
        raise ValueError('max_gap_s must be finite and positive')
    result = list(samples)
    for previous, current in zip(result, result[1:]):
        if previous.time_basis != current.time_basis:
            raise ValueError('mixed time bases')
        gap = current.timestamp_s - previous.timestamp_s
        if gap < 0:
            raise ValueError('timestamps must be nondecreasing')
        if max_gap_s is not None and gap > max_gap_s and 'timestamp_gap' not in current.quality_flags:
            current.quality_flags.append('timestamp_gap')
    return result


# Explicit, field-specific conversions: no guessing from magnitude or names.
CONVERSIONS = {
    ('timestamp_s', 'ms'): lambda x: x / 1000,
    ('speed_kmh', 'm/s'): lambda x: x * 3.6,
    ('speed_kmh', 'mph'): lambda x: x * 1.609344,
    ('soc_pct', 'fraction'): lambda x: x * 100,
    ('battery_voltage_v', 'mV'): lambda x: x / 1000,
    ('battery_current_a', 'mA'): lambda x: x / 1000,
    ('battery_current_a', 'A_charge_positive'): lambda x: -x,
    ('battery_temperature_c', 'K'): lambda x: x - 273.15,
    ('ambient_temperature_c', 'K'): lambda x: x - 273.15,
    ('power_kw', 'W'): lambda x: x / 1000,
    ('odometer_km', 'm'): lambda x: x / 1000,
}
CANONICAL_UNITS = {
    'timestamp_s': 's', 'speed_kmh': 'km/h', 'rpm': 'rpm',
    'battery_voltage_v': 'V', 'battery_current_a': 'A', 'soc_pct': '%',
    'battery_temperature_c': 'degC', 'ambient_temperature_c': 'degC',
    'power_kw': 'kW', 'odometer_km': 'km',
}


def convert(value, field_name, unit):
    value = number(value, field_name)
    if unit == CANONICAL_UNITS.get(field_name):
        return value
    try:
        return CONVERSIONS[field_name, unit](value)
    except KeyError as error:
        raise ValueError(f'unsupported unit {unit!r} for {field_name}') from error
