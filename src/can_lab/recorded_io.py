"""Provenance-preserving recording envelope exports, separate from schema-v1 IO."""
import csv
import json
from .quality import quality_summary
from .recording import Observation, Recording

CSV_METADATA_PREFIX = '# can-lab-recording-1 metadata='


def export_recording_json(recording, stream):
    # Write one observation at a time, avoiding a second full dictionary copy.
    stream.write('{"metadata":')
    json.dump(recording.metadata, stream, allow_nan=False)
    stream.write(',"observations":[')
    for i, observation in enumerate(recording.observations):
        if i:
            stream.write(',')
        json.dump(observation.to_dict(), stream, allow_nan=False)
    stream.write(']}\n')


def export_annotated_csv(recording, stream):
    """One metadata comment followed by CSV; normalized columns plus raw cells.

    JSON raw-cell column retains original types and avoids executing formula-like
    raw text when the CSV is opened in spreadsheet software.
    """
    stream.write(CSV_METADATA_PREFIX + json.dumps(recording.metadata, allow_nan=False) + '\n')
    columns = ['row_number', 'timestamp_s'] + recording.signals + ['signed_power_kw', 'raw_json', 'quality_json', 'derived_json']
    writer = csv.DictWriter(stream, fieldnames=columns)
    writer.writeheader()
    for row in recording.observations:
        writer.writerow({
            'row_number': row.row_number, 'timestamp_s': row.timestamp_s,
            **row.values, 'signed_power_kw': row.derived.get('signed_power_kw', {}).get('value'),
            'raw_json': json.dumps(row.raw, allow_nan=False),
            'quality_json': json.dumps(row.quality, allow_nan=False),
            'derived_json': json.dumps(row.derived, allow_nan=False),
        })


def load_recording_json(stream):
    data = json.load(stream)
    if not isinstance(data, dict) or data.get('metadata', {}).get('schema') != 'can-lab-recording-1':
        raise ValueError('expected a can-lab-recording-1 envelope')
    return Recording(data['metadata'], [Observation(**row) for row in data['observations']])


def load_annotated_csv(stream):
    line = stream.readline()
    if not line.startswith(CSV_METADATA_PREFIX):
        raise ValueError('missing recording metadata preamble')
    metadata = json.loads(line[len(CSV_METADATA_PREFIX):])
    rows = []
    for row in csv.DictReader(stream):
        values = {signal: float(row[signal]) if row[signal] else None for signal in metadata['signals']}
        rows.append(Observation(int(row['row_number']), float(row['timestamp_s']) if row['timestamp_s'] else None,
                                json.loads(row['raw_json']), values, json.loads(row['quality_json']),
                                json.loads(row['derived_json'])))
    return Recording(metadata, rows)


def export_diagnostic_summary(recording, stream):
    powers = [row.derived['signed_power_kw']['value'] for row in recording.observations
              if row.derived.get('signed_power_kw', {}).get('value') is not None]
    json.dump({'metadata': recording.metadata, 'quality': quality_summary(recording),
               'duration_s': recording.duration_s(),
               'signed_power_kw': {'min': min(powers) if powers else None, 'max': max(powers) if powers else None}},
              stream, indent=2, allow_nan=False)
    stream.write('\n')
