"""Configurable, non-destructive recording diagnostics; no bus dependencies."""
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
import json
from statistics import median
from .recording import COLUMNS, numeric


def finite_number(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and numeric(value) is not None


@dataclass
class QualityConfig:
    # Screening defaults, NOT OEM safety limits. Bounds are in normalized units.
    ranges: dict = field(default_factory=lambda: {
        'speed_kmh': (0, 350), 'odometer_km': (0, 10_000_000),
        'battery_voltage_v': (50, 1500), 'battery_current_measured_a': (-3000, 3000),
        'soc_pct': (0, 100), 'cell_voltage_max_v': (0.5, 5), 'cell_voltage_min_v': (0.5, 5),
        'cell_temperature_max_c': (-50, 100), 'cell_temperature_min_c': (-50, 100),
    })
    sentinels: dict = field(default_factory=lambda: {
        'cell_temperature_max_c': [-40], 'cell_temperature_min_c': [-40],
    })
    max_rate_per_s: dict = field(default_factory=lambda: {
        'speed_kmh': 50, 'soc_pct': 5, 'battery_voltage_v': 100,
        'cell_temperature_max_c': 5, 'cell_temperature_min_c': 5,
    })
    session_gap_s: float | None = None
    session_gap_factor: float = 10.0
    raw_max_step: dict = field(default_factory=dict)  # optional thresholds in SOURCE units
    expected_interval_s: float | None = None  # otherwise median positive adjacent interval
    interval_relative_tolerance: float = 0.2
    interval_absolute_tolerance_s: float = 0.001
    flatline_min_samples: int = 30
    flatline_tolerance: float = 0.0
    max_cell_temperature_spread_c: float = 20

    def __post_init__(self):
        if not isinstance(self.flatline_min_samples, int) or self.flatline_min_samples < 2:
            raise ValueError('flatline_min_samples must be >= 2')
        for name in ('interval_relative_tolerance', 'interval_absolute_tolerance_s',
                     'flatline_tolerance', 'max_cell_temperature_spread_c'):
            value = getattr(self, name)
            if not finite_number(value) or value < 0:
                raise ValueError(f'{name} must be finite and nonnegative')
        if self.expected_interval_s is not None and (not finite_number(self.expected_interval_s) or self.expected_interval_s <= 0):
            raise ValueError('expected_interval_s must be finite and positive')
        if not finite_number(self.session_gap_factor) or self.session_gap_factor <= 1:
            raise ValueError('session_gap_factor must be finite and > 1')
        if self.session_gap_s is not None and (not finite_number(self.session_gap_s) or self.session_gap_s <= 0):
            raise ValueError('session_gap_s must be finite and positive')
        for mapping in (self.ranges, self.sentinels, self.max_rate_per_s, self.raw_max_step):
            if not isinstance(mapping, dict) or any(signal not in {target for target, _ in COLUMNS.values()} for signal in mapping):
                raise ValueError('quality thresholds must map known signal names to values')
        for signal, bounds in self.ranges.items():
            if not isinstance(bounds, (list, tuple)) or len(bounds) != 2 or any(not finite_number(v) for v in bounds) or bounds[0] > bounds[1]:
                raise ValueError(f'invalid bounds for {signal}')
        for signal, limit in {**self.max_rate_per_s, **self.raw_max_step}.items():
            if not finite_number(limit) or limit <= 0:
                raise ValueError(f'invalid rate threshold for {signal}')
        for values in self.sentinels.values():
            if not isinstance(values, (list, tuple)) or any(not finite_number(value) for value in values):
                raise ValueError('sentinels must contain finite numeric values')


def validate_recording(recording, config=None):
    """Recompute issues in place; raw cells and every observation remain intact."""
    config = config or QualityConfig()
    rows = recording.observations
    recording.metadata.pop('derived_signals', None)
    # Preserve importer issues; discard prior run's computed issues for repeatability.
    for row in rows:
        importer_issues = [issue for issue in row.quality.get('timestamp_s', []) if issue['reason'].startswith('import:')]
        row.quality = {'timestamp_s': importer_issues} if importer_issues else {}
        # Derived measurements must be recalculated following any validation change.
        row.derived = {}
        for column, (signal, _) in COLUMNS.items():
            raw = row.raw.get(column)
            if raw is None or (isinstance(raw, str) and not raw.strip()):
                row.flag(signal, 'MISSING', 'missing_column' if column not in row.raw else 'missing_value')
                continue
            if signal == 'charging_status':
                codes = recording.metadata['profile'].get('status_codes', {})
                code = str(int(raw)) if isinstance(raw, (int, float)) and numeric(raw) is not None and float(raw).is_integer() else str(raw)
                if not codes:
                    row.flag(signal, 'SUSPECT', 'status_codes_unverified')
                elif code not in codes:
                    row.flag(signal, 'SUSPECT', 'status_code_not_documented')
                continue
            value = numeric(raw)
            if value is None:
                row.flag(signal, 'MISSING', 'nonnumeric_value')
                continue
            value = row.values[signal]
            if value is None:
                row.flag(signal, 'SUSPECT', 'unit_unverified')
                raw_number = numeric(raw)
                if 'temperature' in signal and raw_number == -40:
                    row.flag(signal, 'SUSPECT', 'raw_minus40_temperature_unit_unverified')
                if 'cell_voltage' in signal and raw_number == 0:
                    row.flag(signal, 'SUSPECT', 'raw_zero_cell_voltage')
                continue
            bounds = config.ranges.get(signal)
            if bounds and not bounds[0] <= value <= bounds[1]:
                row.flag(signal, 'OUT_OF_RANGE', 'configured_bounds')
            if value in config.sentinels.get(signal, []):
                row.flag(signal, 'SUSPECT', 'possible_sensor_sentinel')
        if row.timestamp_s is None:
            row.flag('timestamp_s', 'TIMESTAMP_ERROR', 'unusable_timestamp')
            if row.raw.get('time') is None:
                row.flag('timestamp_s', 'MISSING', 'missing_value')

    duplicates = defaultdict(list)
    for i, row in enumerate(rows):
        original = row.raw.get('time')
        if original is not None and original != '':
            key = ('normalized', row.timestamp_s) if row.timestamp_s is not None else ('raw', json.dumps(original, sort_keys=True))
            duplicates[key].append(i)
    for indices in duplicates.values():
        if len(indices) > 1:
            for i in indices:
                rows[i].flag('timestamp_s', 'TIMESTAMP_ERROR', 'duplicate_timestamp')

    intervals = [b.timestamp_s - a.timestamp_s for a, b in zip(rows, rows[1:])
                 if a.timestamp_s is not None and b.timestamp_s is not None and b.timestamp_s > a.timestamp_s]
    expected = config.expected_interval_s
    if expected is None and len(intervals) >= 2:
        expected = median(intervals)
    for previous, current in zip(rows, rows[1:]):
        if previous.timestamp_s is None or current.timestamp_s is None:
            continue
        dt = current.timestamp_s - previous.timestamp_s
        if dt < 0:
            current.flag('timestamp_s', 'TIMESTAMP_ERROR', 'non_monotonic')
        elif dt > 0 and expected is not None:
            tolerance = max(config.interval_absolute_tolerance_s, expected * config.interval_relative_tolerance)
            if abs(dt - expected) > tolerance:
                current.flag('timestamp_s', 'TIMESTAMP_ERROR', 'irregular_interval')
        if dt > 0 and (config.session_gap_s is None or dt <= config.session_gap_s) and (expected is None or dt <= expected * config.session_gap_factor):
            for signal, threshold in config.max_rate_per_s.items():
                before, after = previous.values.get(signal), current.values.get(signal)
                if before is not None and after is not None and abs(after - before) / dt > threshold:
                    current.flag(signal, 'SUSPECT', 'sudden_discontinuity')

    recording.metadata['sampling_interval_s'] = expected
    from .recording_review import recording_boundaries
    boundaries = recording_boundaries(recording, gap_s=config.session_gap_s, gap_factor=config.session_gap_factor)
    boundary_indices = {item['index'] for item in boundaries}
    recording.metadata['recording_boundaries'] = boundaries
    for i, (before, after) in enumerate(zip(rows, rows[1:]), 1):
        if i in boundary_indices:
            continue
        for column, (signal, _) in COLUMNS.items():
            threshold = config.raw_max_step.get(signal)
            a, b = numeric(before.raw.get(column)), numeric(after.raw.get(column))
            if threshold is not None and a is not None and b is not None and abs(b-a) > threshold:
                after.flag(signal, 'SUSPECT', 'raw_step_exceeds_configured_limit')

    # Flatlines are flagged retrospectively, including their first sample. This is
    # a heuristic (stationary/charging values can be constant), never a deletion.
    for signal in recording.signals:
        start = 0
        for end in range(1, len(rows) + 1):
            value = rows[start].values.get(signal)
            continues = (end < len(rows) and end not in boundary_indices and value is not None and rows[end].values.get(signal) is not None
                         and abs(rows[end].values[signal] - value) <= config.flatline_tolerance)
            if continues:
                continue
            if value is not None and end - start >= config.flatline_min_samples:
                for index in range(start, end):
                    rows[index].flag(signal, 'SUSPECT', 'extended_identical_values')
            start = end
    for row in rows:
        high, low = row.values.get('cell_temperature_max_c'), row.values.get('cell_temperature_min_c')
        if high is not None and low is not None and (high < low or high - low > config.max_cell_temperature_spread_c):
            for signal in ('cell_temperature_max_c', 'cell_temperature_min_c'):
                row.flag(signal, 'SUSPECT', 'abnormal_temperature_spread')
        high, low = row.values.get('cell_voltage_max_v'), row.values.get('cell_voltage_min_v')
        if high is not None and low is not None and high < low:
            for signal in ('cell_voltage_max_v', 'cell_voltage_min_v'):
                row.flag(signal, 'SUSPECT', 'inverted_cell_voltage_extrema')
    recording.metadata['quality_configuration'] = asdict(config)
    recording.metadata['sampling_interval_s'] = expected
    recording.metadata['sampling_interval_method'] = 'configured' if config.expected_interval_s is not None else 'median_positive_adjacent_intervals'
    return quality_summary(recording)


def quality_summary(recording):
    result = {'total_observations': len(recording.observations), 'valid_observations': 0,
              'suspicious_observations': 0, 'missing_observations': 0,
              'timestamp_irregularities': 0, 'per_signal': {}}
    signals = recording.signals + ['timestamp_s'] + list(recording.metadata.get('derived_signals', {}))
    for row in recording.observations:
        statuses = {issue['status'] for issues in row.quality.values() for issue in issues}
        statuses.update(issue['status'] for value in row.derived.values() for issue in value.get('quality', []))
        statuses.discard('VALID')
        if not statuses:
            result['valid_observations'] += 1
        if statuses & {'SUSPECT', 'OUT_OF_RANGE', 'TIMESTAMP_ERROR'}:
            result['suspicious_observations'] += 1
        if 'MISSING' in statuses:
            result['missing_observations'] += 1
        if 'TIMESTAMP_ERROR' in statuses:
            result['timestamp_irregularities'] += 1
    for signal in signals:
        counts = Counter()
        reasons = Counter()
        for row in recording.observations:
            issues = row.derived.get(signal, {}).get('quality', []) if signal in recording.metadata.get('derived_signals', {}) else row.quality.get(signal, [])
            counts.update({issue['status'] for issue in issues} or {'VALID'})
            reasons.update(issue['reason'] for issue in issues if issue['status'] != 'VALID')
        result['per_signal'][signal] = {'statuses': dict(counts), 'reasons': dict(reasons)}
    result['counting_policy'] = 'Observation categories and signal statuses overlap; VALID means no flags, not verified sensor accuracy.'
    from .recording_review import dimension_summary
    result['dimensions'] = dimension_summary(recording)
    return result
