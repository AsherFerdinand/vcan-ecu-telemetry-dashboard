"""Independent review dimensions and conservative recording-boundary evidence.

No timestamp magnitude, signal range, or filename establishes units or an OEM
specification. Existing legacy flags are preserved for compatibility.
"""
from collections import Counter
from heapq import nlargest
from .recording import COLUMNS, numeric

METADATA_REASONS = {'unit_unverified', 'status_codes_unverified', 'current_polarity_unverified', 'status_code_not_documented'}


def physical_issues(row, signal):
    return [issue for issue in row.quality.get(signal, [])
            if signal != 'timestamp_s' and issue['status'] in ('OUT_OF_RANGE', 'SUSPECT')
            and issue['reason'] not in METADATA_REASONS]


def timestamp_classification(row):
    """Uninterpreted time is distinct from evidence of an invalid clock/value."""
    reasons = {issue['reason'] for issue in row.quality.get('timestamp_s', [])}
    if reasons & {'duplicate_timestamp', 'non_monotonic'}:
        return 'invalid'
    if any(any(token in reason for token in ('invalid_encoded', 'negative_timestamp', 'mixed_timezone_awareness')) for reason in reasons):
        return 'invalid'
    if row.timestamp_s is not None:
        return 'invalid' if any('before_recording_origin' in r for r in reasons) else 'usable'
    raw = row.raw.get('time')
    if numeric(raw) is not None:
        return 'unverified'
    if isinstance(raw, str) and raw.strip().isdigit():
        return 'unverified'
    return 'invalid'


def dimensions(row, recording):
    numeric_values = [numeric(row.raw.get(column)) for column in COLUMNS if column != 'charging_signal']
    present_numeric = any(value is not None for value in numeric_values)
    physical = any(physical_issues(row, signal) for signal in recording.signals)
    missing = any(issue['status'] == 'MISSING' for issues in row.quality.values() for issue in issues)
    metadata = any(issue['reason'] in METADATA_REASONS for issues in row.quality.values() for issue in issues)
    metadata |= recording.metadata.get('time_interpretation_status') == 'inferred_yearless_encoding'
    metadata |= (recording.metadata.get('profile', {}).get('current_convention', 'unknown') == 'unknown' or not recording.metadata.get('profile', {}).get('current_reference'))
    unassessed = any(numeric(row.raw.get(column)) is not None and row.values.get(signal) is None
                     for column, (signal, _) in COLUMNS.items() if column != 'charging_signal')
    range_failure = any(issue['status'] == 'OUT_OF_RANGE' for signal, issues in row.quality.items() if signal != 'timestamp_s' for issue in issues)
    return {'numerically_plausible': present_numeric and not range_failure,
            'physically_suspicious': physical, 'metadata_unverified': metadata,
            'physical_checks_incomplete': unassessed, 'missing_data': missing,
            'timestamp_anomaly': bool(row.quality.get('timestamp_s')), 'timestamp': timestamp_classification(row)}


def dimension_summary(recording):
    counts = Counter()
    per_signal = {signal: Counter() for signal in recording.signals}
    for row in recording.observations:
        view = dimensions(row, recording)
        for key, value in view.items():
            if key != 'timestamp' and value:
                counts[key + '_observations'] += 1
        counts['timestamp_' + view['timestamp'] + '_observations'] += 1
        for column, (signal, _) in COLUMNS.items():
            issues = row.quality.get(signal, [])
            if any(i['status'] == 'MISSING' for i in issues):
                per_signal[signal]['missing'] += 1
            elif signal != 'charging_status' and numeric(row.raw.get(column)) is not None:
                per_signal[signal]['numeric'] += 1
            if physical_issues(row, signal):
                per_signal[signal]['physically_suspicious'] += 1
            if any(i['reason'] in METADATA_REASONS for i in issues):
                per_signal[signal]['metadata_unverified'] += 1
            if numeric(row.raw.get(column)) is not None and row.values.get(signal) is None and signal != 'charging_status':
                per_signal[signal]['physical_checks_incomplete'] += 1
    keys = ['numerically_plausible', 'physically_suspicious', 'metadata_unverified',
            'physical_checks_incomplete', 'missing_data', 'timestamp_anomaly', 'timestamp_usable', 'timestamp_invalid', 'timestamp_unverified']
    return {'imported_observations': len(recording.observations),
            **{key + '_observations': counts[key + '_observations'] for key in keys},
            'per_signal': {key: dict(value) for key, value in per_signal.items()},
            'policy': 'Independent, overlapping dimensions. Numerically plausible means available finite measurements with no detected normalized range violation; heuristic suspicion and missing fields may overlap. It does not verify units, complete physical screening, timestamps, or sensor accuracy.'}


def inspect_timestamps(recording):
    """Describe actual raw representations without choosing a timestamp decoder."""
    rows = recording.observations
    types = Counter(type(row.raw.get('time')).__name__ for row in rows)
    lengths = Counter(len(str(row.raw['time']).strip()) for row in rows if isinstance(row.raw.get('time'), str))
    numbers = [numeric(row.raw.get('time')) for row in rows]
    steps = [b - a for a, b in zip(numbers, numbers[1:]) if a is not None and b is not None]
    sample_indices = sorted(set(list(range(min(10, len(rows)))) + list(range(max(0, len(rows) - 3), len(rows)))))
    return {'raw_types': dict(types), 'raw_string_lengths': dict(lengths),
            'examples': [{'row_number': rows[i].row_number, 'raw_time': rows[i].raw.get('time'),
                          'normalized_timestamp_s': rows[i].timestamp_s} for i in sample_indices],
            'numeric_raw_min': min((v for v in numbers if v is not None), default=None),
            'numeric_raw_max': max((v for v in numbers if v is not None), default=None),
            'raw_adjacent_step_min': min(steps, default=None), 'raw_adjacent_step_max': max(steps, default=None),
            'raw_step_unit': 'source representation; NOT established seconds',
            'excel_time_number_formats': recording.metadata.get('excel_time_number_formats', {}),
            'excel_date_system_origin': recording.metadata.get('excel_date_system_origin'),
            'interpretation_status': recording.metadata.get('time_interpretation_status', 'unverified'),
            'year': None if recording.metadata['profile']['time_unit'] == 'MDDHHMMSS' else 'not separately inferred',
            'selected_time_unit': recording.metadata['profile']['time_unit'],
            'selected_time_basis': recording.metadata['profile']['time_basis'],
            'warning': 'Numeric or compact date-like values are not automatically decoded. Unix/elapsed/encoded-date semantics require source documentation and an explicit profile.'}


def recording_boundaries(recording, *, gap_s=None, gap_factor=10):
    """Possible boundaries, not established driving-session labels.

    Raw numeric reversals can suggest a boundary without establishing time units.
    For interpreted times, explicit gaps or a relative interval factor are used.
    """
    result = []
    expected = recording.metadata.get('sampling_interval_s')
    limit = gap_s if gap_s is not None else (expected * gap_factor if expected else None)
    for i, (before, after) in enumerate(zip(recording.observations, recording.observations[1:]), 1):
        reason = None
        if before.timestamp_s is not None and after.timestamp_s is not None:
            dt = after.timestamp_s - before.timestamp_s
            if dt < 0:
                reason = 'normalized_clock_reversal'
            elif dt == 0:
                reason = 'duplicate_clock_value'
            elif limit is not None and dt > limit:
                reason = 'configured_possible_session_gap'
        else:
            a, b = numeric(before.raw.get('time')), numeric(after.raw.get('time'))
            if a is not None and b is not None and b < a:
                reason = 'raw_numeric_reversal_time_unverified'
            elif (before.timestamp_s is None) != (after.timestamp_s is None):
                reason = 'unusable_time_boundary'
        if reason:
            result.append({'index': i, 'row_number': after.row_number, 'reason': reason,
                           'raw_time_before': before.raw.get('time'), 'raw_time_after': after.raw.get('time')})
    return result


def anomaly_report(recording):
    """Review examples, raw extrema/steps, and diagnostic counts without deletion."""
    report = {}
    boundaries = {item['index'] for item in recording.metadata.get('recording_boundaries', [])}
    rows = recording.observations
    for column, (signal, _) in COLUMNS.items():
        if signal == 'charging_status':
            continue
        values = [(row.row_number, numeric(row.raw.get(column))) for row in recording.observations]
        numeric_values = [(row, value) for row, value in values if value is not None]
        counts = Counter(issue['reason'] for row in recording.observations for issue in physical_issues(row, signal))
        steps = ((abs(b[1] - a[1]), a[0], b[0], b[1] - a[1], i) for i, (a, b) in enumerate(zip(values, values[1:]), 1) if a[1] is not None and b[1] is not None)
        report[signal] = {'physical_issue_counts': dict(counts),
                          'missing_or_nonnumeric': sum(value is None for _, value in values),
                          'raw_minus40_count': sum(value == -40 for _, value in numeric_values) if 'temperature' in signal else None,
                          'raw_zero_count': sum(value == 0 for _, value in numeric_values) if 'cell_voltage' in signal else None,
                          'largest_raw_adjacent_steps': [{'from_row': a, 'to_row': b, 'signed_step': step, 'possible_boundary': i in boundaries,
                                                          'elapsed_s': rows[i].timestamp_s - rows[i-1].timestamp_s if rows[i].timestamp_s is not None and rows[i-1].timestamp_s is not None else None}
                                                         for _, a, b, step, i in nlargest(3, steps)],
                          'step_interpretation': 'source units; not a per-second rate or proof of a physical fault'}
    return report
