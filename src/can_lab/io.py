"""Strict CSV/JSON normalization, candump import, and lossless schema exports."""
import csv
from dataclasses import fields
import json
import re
from typing import TextIO
from .telemetry import CANONICAL_UNITS, TelemetrySample, convert, validate_series

FIELD_NAMES = [field.name for field in fields(TelemetrySample)]


def normalize_rows(rows, *, columns=None, units=None, time_basis='relative',
                   source='recorded-unspecified', max_gap_s=None):
    """columns maps input names to schema names; supplying it selects those columns.

    units maps schema names to explicit input units. Unmapped input is rejected
    when columns is absent. No implicit timestamp sorting, resampling or filling.
    """
    if units is not None and not isinstance(units, dict):
        raise ValueError('units must be an object')
    if columns is not None and not isinstance(columns, dict):
        raise ValueError('columns must be an object')
    units = units or {}
    if any(not isinstance(key, str) or not isinstance(value, str) for key, value in units.items()):
        raise ValueError('unit names and values must be strings')
    for name, unit in units.items():
        if name not in CANONICAL_UNITS:
            raise ValueError(f'unit configured for unknown numeric field: {name}')
        convert(0, name, unit)  # Validate even if the column is entirely missing.
    if columns is not None:
        if any(not isinstance(key, str) or not isinstance(value, str) for key, value in columns.items()):
            raise ValueError('column names and targets must be strings')
        if not columns or len(set(columns.values())) != len(columns):
            raise ValueError('column mapping must be nonempty with unique targets')
        if any(target not in FIELD_NAMES for target in columns.values()):
            raise ValueError('unknown column mapping target')
    samples = []
    for index, row in enumerate(rows, 1):
        try:
            if not isinstance(row, dict) or any(not isinstance(key, str) for key in row):
                raise ValueError('expected an object with string keys')
            if columns is not None:
                missing = set(columns) - set(row)
                if missing:
                    raise ValueError(f'missing mapped columns: {sorted(missing)}')
                row = {target: row[key] for key, target in columns.items()}
            unknown = set(row) - set(FIELD_NAMES)
            if unknown:
                raise ValueError(f'unknown fields: {sorted(unknown)}; supply an explicit column mapping')
            record = {key: value for key, value in row.items() if value is not None and value != ''}
            if 'timestamp_s' not in record:
                raise ValueError('missing timestamp_s')
            record.setdefault('time_basis', time_basis)
            record.setdefault('source', source)
            for name in CANONICAL_UNITS:
                if name in record:
                    record[name] = convert(record[name], name, units.get(name, CANONICAL_UNITS[name]))
            if 'schema_version' in record:
                version = record['schema_version']
                if version == '1':
                    record['schema_version'] = 1
            if isinstance(record.get('quality_flags'), str):
                record['quality_flags'] = json.loads(record['quality_flags'])
            samples.append(TelemetrySample(**record))
        except (ValueError, TypeError) as error:
            raise ValueError(f'record {index}: {error}') from error
    if not samples:
        raise ValueError('input contains no telemetry records')
    return validate_series(samples, max_gap_s=max_gap_s)


def load_csv(stream: TextIO, **options):
    reader = csv.DictReader(stream)
    headers = reader.fieldnames
    if not headers or any(not header for header in headers) or len(headers) != len(set(headers)):
        raise ValueError('CSV must have unique nonempty column headers')
    # Missing trailing fields can mean absent optional signals; surplus cells are errors.
    return normalize_rows(reader, **options)


def load_json(stream: TextIO, **options):
    rows = json.load(stream)
    if not isinstance(rows, list):
        raise ValueError('JSON input must be an array of sample objects')
    return normalize_rows(rows, **options)


CANDUMP = re.compile(r'^\((\d+(?:\.\d+)?)\)\s+(\S+)\s+([0-9a-fA-F]{3}|[0-9a-fA-F]{8})#([0-9a-fA-F]*)$')


def load_candump(stream: TextIO, *, time_basis='unix', source='synthetic-candump',
                 max_gap_s=None):
    """Read can-utils candump -L classical data frames using the synthetic DBC.

    All frames must belong to the original synthetic protocol. FD, RTR, unknown
    IDs and malformed lines fail explicitly, rather than silently losing data.
    """
    import can
    from .codec import SyntheticCodec
    codec = SyntheticCodec()
    samples = []
    channels = set()
    for line_number, line in enumerate(stream, 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        match = CANDUMP.fullmatch(line)
        if not match:
            raise ValueError(f'line {line_number}: unsupported candump line')
        timestamp, channel, identifier, payload = match.groups()
        try:
            channels.add(channel)
            if len(channels) > 1:
                raise ValueError('multiple CAN channels require explicit separation')
            message = can.Message(timestamp=float(timestamp), arbitration_id=int(identifier, 16),
                                  data=bytes.fromhex(payload), is_extended_id=len(identifier) == 8,
                                  check=True)
            samples.append(codec.decode(message, time_basis=time_basis, source=source))
        except ValueError as error:
            raise ValueError(f'line {line_number}: {error}') from error
    if not samples:
        raise ValueError('input contains no CAN data frames')
    return validate_series(samples, max_gap_s=max_gap_s)


def export_json(samples, stream: TextIO):
    samples = validate_series(samples)
    json.dump([sample.to_dict() for sample in samples], stream, indent=2, allow_nan=False)
    stream.write('\n')


def export_csv(samples, stream: TextIO):
    samples = validate_series(samples)
    writer = csv.DictWriter(stream, fieldnames=FIELD_NAMES)
    writer.writeheader()
    for sample in samples:
        row = sample.to_dict()
        row['quality_flags'] = json.dumps(row['quality_flags'])
        writer.writerow(row)
