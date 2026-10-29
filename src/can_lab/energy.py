"""Gap-aware signed energy integration; signed components are not charge labels."""
from collections import Counter
from dataclasses import dataclass
from .engineering_common import boundary_indices, finite, interval_reason, usable


@dataclass
class EnergyConfig:
    max_interval_s: float = 30.0
    max_distance_speed_kmh: float = 350.0  # screening heuristic, not a vehicle spec

    def __post_init__(self):
        if any(not finite(value) or value <= 0 for value in vars(self).values()):
            raise ValueError('energy thresholds must be finite and positive')


def trapezoid_components(p0, p1, dt):
    """Exact positive/negative areas of linearly interpolated power, in kWh."""
    if not all(finite(v) for v in (p0, p1, dt)) or dt <= 0:
        raise ValueError('finite power and positive finite elapsed interval required')
    if p0 >= 0 and p1 >= 0:
        positive,negative = (p0/2+p1/2) * (dt/3600), 0.0
    elif p0 <= 0 and p1 <= 0:
        positive,negative = 0.0, (p0/2+p1/2) * (dt/3600)
    else:
        scale=max(abs(p0),abs(p1))
        fraction=(abs(p0)/scale)/(abs(p0)/scale+abs(p1)/scale)
        first_dt=dt*fraction
        first=(p0/2)*(first_dt/3600)
        second=(p1/2)*((dt-first_dt)/3600)
        positive,negative=max(first,second),min(first,second)
    if not finite(positive) or not finite(negative):
        raise ValueError('energy integral is not representable as finite kWh')
    return positive,negative


def integrate_energy(recording, config=None, *, start=0, end=None):
    """Use intervals entirely inside [start,end); never join nonadjacent samples."""
    config = config or EnergyConfig()
    rows = recording.observations
    end = len(rows) if end is None else end
    if not 0 <= start <= end <= len(rows):
        raise ValueError('invalid energy observation range')
    boundaries = boundary_indices(recording)
    positive = negative = included_s = distance = 0.0
    included = flagged = distance_intervals = 0
    excluded = Counter()
    for i in range(start + 1, end):
        a, b = rows[i-1], rows[i]
        reason = interval_reason(a, b, i, boundaries, config.max_interval_s)
        p0, p1 = a.derived.get('signed_power_kw', {}).get('value'), b.derived.get('signed_power_kw', {}).get('value')
        if reason is None and (not finite(p0) or not finite(p1) or not all(usable(row, signal) for row in (a,b) for signal in ('battery_voltage_v','battery_current_measured_a'))):
            reason = 'unusable_electrical_measurement'
        if reason:
            excluded[reason] += 1
            continue
        dt = b.timestamp_s - a.timestamp_s
        pos, neg = trapezoid_components(p0,p1,dt)
        positive += pos; negative += neg; included_s += dt; included += 1
        if any(any(issue['status'] != 'VALID' for issue in row.derived.get('signed_power_kw', {}).get('quality', [])) or row.quality.get('timestamp_s') for row in (a,b)):
            flagged += 1
        if all(usable(row, 'odometer_km') for row in (a,b)):
            delta = b.values['odometer_km'] - a.values['odometer_km']
            if 0 <= delta <= config.max_distance_speed_kmh * dt / 3600:
                distance += delta; distance_intervals += 1
    signed = positive + negative
    qualified_distance = distance_intervals == included and included > 0 and distance > 0
    return {'signed_net_kwh': signed, 'positive_signed_kwh': positive, 'negative_signed_kwh': negative,
            'absolute_throughput_kwh': positive - negative, 'included_intervals': included,
            'flagged_included_intervals': flagged, 'excluded_intervals': sum(excluded.values()),
            'excluded_reasons': dict(excluded), 'included_duration_s': included_s,
            'candidate_intervals': max(0,end-start-1),
            'distance_over_energy_intervals_km': distance if distance_intervals else None,
            'distance_covered_intervals': distance_intervals,
            'qualified_signed_kwh_per_km': signed / distance if qualified_distance else None,
            'distance_qualification': 'Matched accepted energy intervals only; all must have nondecreasing plausible declared/documented-unit odometer deltas. Not verified vehicle efficiency.',
            'time_interpretation': recording.metadata.get('time_interpretation_status','profile_declared'),
            'current_convention': recording.metadata['profile']['current_convention'],
            'method': 'trapezoidal power interpolation; split sign-crossing intervals at interpolated zero; no bridging boundaries or excluded intervals',
            'sign_labels': 'positive and negative MEASURED signs; not charging/discharging labels',
            'max_interval_s': config.max_interval_s}
