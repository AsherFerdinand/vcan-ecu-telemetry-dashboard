"""Shared plot windows, bounded sampling, and discontinuity-safe line groups."""
import math
from .recording import numeric
from .recording_review import physical_issues


def signal_value(recording, row, signal, derived=False):
    if derived:
        return row.derived.get(signal, {}).get('value')
    spec = recording.metadata['signals'][signal]
    return numeric(row.raw.get(spec['source_column'])) if spec['unit_status'] == 'unverified' else row.values.get(signal)


def prepare_signal_plot(recording, indices, signal, *, derived=False, max_points=2000):
    if max_points < 4:
        raise ValueError('max_points must be at least 4')
    if not indices:
        return {'data': [], 'use_time': False, 'domain': [0, 1], 'sampled': False}
    rows = recording.observations
    use_time = all(rows[i].timestamp_s is not None for i in indices)
    boundary_indices = {item['index'] for item in recording.metadata.get('recording_boundaries', [])}
    stride = max(1, math.ceil(len(indices) / max(1, max_points // 2)))
    regular = set(range(0, len(indices), stride)) | {len(indices) - 1}
    events = []
    groups = []
    group = 0
    previous_index = None
    previous_missing = True
    for position, index in enumerate(indices):
        row = rows[index]
        value = signal_value(recording, row, signal, derived)
        if index in boundary_indices or previous_index is None or index != previous_index + 1 or previous_missing or value is None:
            group += 1
        groups.append(group)
        if index in boundary_indices or (physical_issues(row, signal) and any(i['reason'] != 'extended_identical_values' for i in physical_issues(row, signal))):
            events.extend([max(0, position - 1), position, min(len(indices) - 1, position + 1)])
        previous_index, previous_missing = index, value is None
    positions = set(range(len(indices))) if len(indices) <= max_points else regular
    for position in events:
        if len(positions) >= max_points:
            break
        positions.add(position)
    data = []
    for position in sorted(positions):
        row = rows[indices[position]]
        value = signal_value(recording, row, signal, derived)
        physical = physical_issues(row, signal)
        data.append({'x': row.timestamp_s if use_time else row.row_number, 'row_number': row.row_number,
                     'raw_time': str(row.raw.get('time')), 'value': value, 'group': str(groups[position]),
                     'quality': 'MISSING' if value is None else 'PHYSICALLY_SUSPICIOUS' if physical else 'NUMERIC',
                     'flags': str(row.derived.get(signal, {}).get('quality', []) if derived else row.quality.get(signal, []))})
    extent = [min(rows[i].timestamp_s if use_time else rows[i].row_number for i in indices),
              max(rows[i].timestamp_s if use_time else rows[i].row_number for i in indices)]
    if extent[0] == extent[1]:
        extent = [extent[0] - .5, extent[1] + .5]
    return {'data': data, 'use_time': use_time, 'domain': extent, 'sampled': len(positions) < len(indices)}
