"""Small shared rules for quality-aware engineering calculations (no CAN/UI)."""
import math
from .recording_review import timestamp_classification


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def usable(row, signal):
    value = row.values.get(signal)
    if not finite(value):
        return False
    # Constant quantized signals may be legitimate. Retain their heuristic as a
    # warning, rather than silently preventing stationary/charging analysis.
    return not any(issue['status'] in ('MISSING', 'OUT_OF_RANGE') or
                   (issue['status'] == 'SUSPECT' and issue['reason'] not in ('extended_identical_values',))
                   for issue in row.quality.get(signal, []))


def interval_reason(previous, current, index, boundary_indices, max_interval_s):
    if index in boundary_indices:
        return 'recording_boundary'
    if timestamp_classification(previous) != 'usable' or timestamp_classification(current) != 'usable':
        return 'unusable_timestamp'
    dt = current.timestamp_s - previous.timestamp_s
    if dt <= 0:
        return 'nonpositive_interval'
    if dt > max_interval_s:
        return 'maximum_interval_exceeded'
    return None


def boundary_indices(recording):
    return {item['index'] for item in recording.metadata.get('recording_boundaries', [])}


def source_status(recording, row):
    profile = recording.metadata['profile']
    if not profile.get('status_reference'):
        return None
    raw = row.raw.get('charging_signal')
    key = str(int(raw)) if finite(raw) and float(raw).is_integer() else str(raw)
    return profile.get('status_codes', {}).get(key)
