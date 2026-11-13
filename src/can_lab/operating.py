"""Candidate vehicle states from documented inputs and explicit time assumptions."""
from collections import deque
from dataclasses import dataclass
from statistics import median
from .engineering_common import boundary_indices, finite, interval_reason, source_status, usable


@dataclass
class OperatingConfig:
    smoothing_samples: int = 3  # causal trailing median, reset at gaps/invalid input
    stationary_speed_kmh: float = 0.5
    acceleration_threshold_m_s2: float = 0.15
    deceleration_threshold_m_s2: float = 0.15
    constant_speed_tolerance_m_s2: float = 0.05
    max_derivative_interval_s: float = 30.0
    regenerative_power_threshold_kw: float = 0.5

    def __post_init__(self):
        if type(self.smoothing_samples) is not int or self.smoothing_samples < 1 or self.smoothing_samples % 2 != 1:
            raise ValueError('smoothing_samples must be a positive odd integer')
        for key, value in vars(self).items():
            if not finite(value) or value < 0:
                raise ValueError(f'{key} must be finite and nonnegative')
        if min(self.acceleration_threshold_m_s2, self.deceleration_threshold_m_s2, self.max_derivative_interval_s) <= 0:
            raise ValueError('acceleration/deceleration and interval thresholds must be positive')
        if self.constant_speed_tolerance_m_s2 >= min(self.acceleration_threshold_m_s2, self.deceleration_threshold_m_s2):
            raise ValueError('constant-speed band must be below acceleration/deceleration thresholds')


@dataclass(slots=True)
class OperatingPoint:
    row_number: int
    smoothed_speed_kmh: float | None
    acceleration_m_s2: float | None
    candidates: tuple[str, ...]
    source_reported_state: str | None
    verification: str
    warnings: tuple[str, ...]


def analyze_operating_states(recording, config=None):
    config = config or OperatingConfig()
    boundaries = boundary_indices(recording)
    history = deque(maxlen=config.smoothing_samples)
    previous = None
    previous_smoothed = None
    result = []
    inferred_time = recording.metadata.get('time_interpretation_status') == 'inferred_yearless_encoding'
    convention = recording.metadata['profile']['current_convention']
    polarity_documented = convention != 'unknown' and bool(recording.metadata['profile'].get('current_reference','').strip())
    for i, row in enumerate(recording.observations):
        speed_ok = usable(row, 'speed_kmh')
        reason = interval_reason(previous, row, i, boundaries, config.max_derivative_interval_s) if previous is not None else 'start_of_recording'
        if reason or not speed_ok or previous_smoothed is None:
            history.clear()
        if speed_ok:
            history.append(row.values['speed_kmh'])
        smoothed = median(history) if history else None
        acceleration = None
        warnings = []
        if reason:
            warnings.append(reason)
        elif smoothed is not None and previous_smoothed is not None:
            acceleration = (smoothed - previous_smoothed) / 3.6 / (row.timestamp_s - previous.timestamp_s)
        reported = source_status(recording, row)
        candidates = []
        if reported and reported.casefold() in ('charging', 'charging mode'):
            candidates.append('charging')
        if speed_ok and row.values['speed_kmh'] <= config.stationary_speed_kmh:
            candidates.append('stationary')
        elif acceleration is not None:
            if acceleration >= config.acceleration_threshold_m_s2:
                candidates.append('acceleration')
            elif acceleration <= -config.deceleration_threshold_m_s2:
                candidates.append('deceleration')
            elif abs(acceleration) <= config.constant_speed_tolerance_m_s2:
                candidates.append('approximately_constant_speed')
        power = row.derived.get('signed_power_kw', {}).get('value')
        if 'deceleration' in candidates and 'charging' not in candidates and polarity_documented and usable(row, 'battery_voltage_v') and usable(row, 'battery_current_measured_a') and finite(power):
            charging_power = power < -config.regenerative_power_threshold_kw if convention == 'positive_discharge' else power > config.regenerative_power_threshold_kw
            if charging_power:
                candidates.append('possible_regenerative_braking')
        if not polarity_documented:
            warnings.append('current_polarity_not_documented_regeneration_not_assessed')
        if not candidates:
            candidates.append('unknown' if speed_ok else 'insufficient_evidence')
        for signal in ('speed_kmh', 'timestamp_s'):
            warnings.extend(f"{signal}:{issue['reason']}" for issue in row.quality.get(signal, []))
        verification = 'inferred_candidates_with_inferred_time' if inferred_time else 'inferred_candidates_with_profile_time'
        result.append(OperatingPoint(row.row_number, smoothed, acceleration, tuple(candidates), reported, verification, tuple(warnings)))
        previous, previous_smoothed = row, smoothed
    return result
