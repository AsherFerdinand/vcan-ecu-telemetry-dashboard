from copy import deepcopy
from datetime import datetime, timedelta, timezone
import io
import json
import pytest
from openpyxl import Workbook
from can_lab.excel import load_xlsx
from can_lab.recording import COLUMNS, DatasetProfile
from can_lab.quality import QualityConfig, validate_recording, quality_summary
from can_lab.diagnostics import calculate_power, vehicle_dynamics
from can_lab.recorded_io import (export_recording_json, export_annotated_csv, export_diagnostic_summary,
                                load_recording_json, load_annotated_csv)
from can_lab.replay import Replay, RecordingSource
from can_lab.cli import main

UNITS = {column: unit for column, (_, unit) in COLUMNS.items() if unit is not None}
HEADERS = ['time'] + list(COLUMNS)
BASE = [0, 36, 0, 1000, 400, 20, 80, 4.1, 4.0, 26, 25]


def workbook(rows=None, headers=None, second_sheet=False):
    book = Workbook()
    sheet = book.active
    sheet.title = 'Measurements'
    sheet.append(headers if headers is not None else HEADERS)
    for row in rows if rows is not None else [BASE]:
        sheet.append(row)
    if second_sheet:
        sheet = book.create_sheet('Other')
        sheet.append(['time', 'vhc_speed'])
        sheet.append([0, 10])
    buffer = io.BytesIO()
    book.save(buffer)
    book.close()
    buffer.seek(0)
    return buffer


def profile(**options):
    return DatasetProfile(units=UNITS, time_unit='s', dataset_id='synthetic-test', **options)


def recording(rows=None, **kwargs):
    return load_xlsx(workbook(rows), profile=profile(), filename='synthetic.xlsx', **kwargs)


def test_valid_excel_mapping_provenance_and_no_mutation():
    buffer = workbook(second_sheet=True)
    before = buffer.getvalue()
    buffer.seek(7)
    result = load_xlsx(buffer, profile=profile(), filename='vehicle#1.xlsx')
    assert buffer.tell() == 7 and buffer.getvalue() == before
    assert result.metadata['source_filename'] == 'vehicle#1.xlsx'
    assert result.metadata['profile']['dataset_id'] == 'synthetic-test'
    assert len(result.metadata['sha256']) == 64
    assert result.metadata['source_columns'] == HEADERS
    assert result.metadata['available_sheets'] == ['Measurements', 'Other']
    row = result.observations[0]
    for index, (source_column, (target, _)) in enumerate(COLUMNS.items(), 1):
        assert row.raw[source_column] == BASE[index]
        assert result.metadata['signals'][target]['source_column'] == source_column
        if source_column != 'charging_signal':
            assert row.values[target] == BASE[index]
    assert row.values['battery_current_measured_a'] == 20
    assert 'battery_current_a' not in row.values
    assert result.canonical_samples()[0].battery_current_a is None


def test_defaults_do_not_invent_units_or_current_semantics():
    result = load_xlsx(workbook())
    validate_recording(result)
    calculate_power(result)
    row = result.observations[0]
    assert row.raw['hv_current'] == 20
    assert row.values['battery_current_measured_a'] is None
    assert row.timestamp_s is None  # Numeric timestamp units not declared.
    assert row.derived['signed_power_kw']['value'] is None
    assert row.statuses('battery_voltage_v') == {'SUSPECT'}
    assert result.metadata['signals']['battery_voltage_v']['unit_status'] == 'unverified'


def test_missing_columns_and_unknown_extra_column():
    result = load_xlsx(workbook([[0, 36, 'kept']], ['time', 'vhc_speed', 'extra']), profile=profile())
    summary = validate_recording(result)
    assert result.observations[0].raw['extra'] == 'kept'
    assert result.observations[0].values['battery_voltage_v'] is None
    assert result.observations[0].statuses('battery_voltage_v') == {'MISSING'}
    assert summary['missing_observations'] == 1
    assert any('Missing source columns' in warning for warning in result.metadata['warnings'])


@pytest.mark.parametrize('bad', ['bad', '=A1*2', '#N/A', True])
def test_invalid_numeric_raw_values_retained(bad):
    row = BASE.copy()
    row[HEADERS.index('hv_voltage')] = bad
    result = recording([row])
    validate_recording(result)
    calculate_power(result)
    observation = result.observations[0]
    assert observation.raw['hv_voltage'] == bad
    assert observation.statuses('battery_voltage_v') == {'MISSING'}
    assert observation.derived['signed_power_kw']['value'] is None
    assert any(issue.get('input_signal') == 'battery_voltage_v' for issue in observation.derived['signed_power_kw']['quality'])


def test_duplicate_nonmonotonic_irregular_and_original_order():
    rows = []
    for value in [0, 1, 1, .5, 10]:
        row = BASE.copy(); row[0] = value; rows.append(row)
    result = recording(rows)
    summary = validate_recording(result, QualityConfig(expected_interval_s=1))
    assert [row.raw['time'] for row in result.observations] == [0, 1, 1, .5, 10]
    assert all('duplicate_timestamp' in [x['reason'] for x in result.observations[i].quality['timestamp_s']] for i in [1, 2])
    assert 'non_monotonic' in [x['reason'] for x in result.observations[3].quality['timestamp_s']]
    assert 'irregular_interval' in [x['reason'] for x in result.observations[4].quality['timestamp_s']]
    assert summary['timestamp_irregularities'] == 4
    assert result.duration_s() is None
    with pytest.raises(ValueError, match='nondecreasing'):
        Replay(RecordingSource(result))
    before = deepcopy([row.to_dict() for row in result.observations])
    validate_recording(result, QualityConfig(expected_interval_s=1))
    assert before == [row.to_dict() for row in result.observations]


def test_timestamp_datetime_and_original_type():
    start = datetime(2026, 1, 1, 12)
    rows = [BASE.copy(), BASE.copy()]
    rows[0][0] = start; rows[1][0] = start + timedelta(seconds=2)
    result = load_xlsx(workbook(rows), profile=DatasetProfile(units=UNITS))
    assert [row.timestamp_s for row in result.observations] == [0, 2]
    assert result.metadata['time_origin'] == start.isoformat()
    assert result.observations[0].raw['time'] == {'type': 'datetime', 'value': start.isoformat()}
    assert result.duration_s() == 2


def test_iso_timezone_and_no_timezone_invention():
    buffer = workbook([['2026-01-01T00:00:00Z', 10]], ['time', 'vhc_speed'])
    result = load_xlsx(buffer, profile=DatasetProfile(time_basis='unix'))
    assert result.observations[0].timestamp_s == datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()
    buffer = workbook([[datetime(2026, 1, 1), 10]], ['time', 'vhc_speed'])
    result = load_xlsx(buffer, profile=DatasetProfile(time_basis='unix'))
    assert result.observations[0].timestamp_s is None


def test_datetime_clock_reset_and_invalid_time():
    start = datetime(2026, 1, 1, 12)
    rows = [[start, 10], [start - timedelta(seconds=1), 11], ['not-time', 12], [None, 13]]
    result = load_xlsx(workbook(rows, ['time', 'vhc_speed']))
    validate_recording(result)
    assert result.observations[1].timestamp_s == -1
    assert 'TIMESTAMP_ERROR' in result.observations[1].statuses('timestamp_s')
    assert result.observations[2].raw['time'] == 'not-time'
    assert result.observations[3].statuses('timestamp_s') == {'TIMESTAMP_ERROR', 'MISSING'}
    with pytest.raises(ValueError, match='timestamps'):
        result.canonical_samples()


def test_unit_conversions_and_canonical_current_bridge():
    row = BASE.copy()
    row[0] = 1000; row[1] = 10; row[4] = 400000; row[5] = -20000; row[6] = .8; row[7] = 4100; row[9] = 298.15
    units = dict(UNITS, vhc_speed='m/s', hv_voltage='mV', hv_current='mA', bcell_soc='fraction', bcell_maxVoltage='mV', bcell_maxTemp='K')
    result = load_xlsx(workbook([row]), profile=DatasetProfile(units=units, time_unit='ms', current_convention='positive_charge'))
    values = result.observations[0].values
    assert values['speed_kmh'] == 36 and values['soc_pct'] == 80
    assert values['battery_voltage_v'] == 400 and values['cell_voltage_max_v'] == 4.1
    assert values['cell_temperature_max_c'] == pytest.approx(25)
    assert result.observations[0].timestamp_s == 1
    assert result.canonical_samples()[0].battery_current_a == 20


@pytest.mark.parametrize('column,value,status', [
    ('bcell_soc', 101, 'OUT_OF_RANGE'), ('bcell_soc', -1, 'OUT_OF_RANGE'),
    ('bcell_maxTemp', -40, 'SUSPECT'), ('bcell_minTemp', 200, 'OUT_OF_RANGE'),
    ('bcell_maxVoltage', 0, 'OUT_OF_RANGE'), ('bcell_minVoltage', -1, 'OUT_OF_RANGE'),
    ('hv_voltage', 0, 'OUT_OF_RANGE'),
])
def test_quality_limits(column, value, status):
    row = BASE.copy(); row[HEADERS.index(column)] = value
    result = recording([row]); validate_recording(result)
    target = COLUMNS[column][0]
    assert status in result.observations[0].statuses(target)
    assert result.observations[0].raw[column] == value


def test_configurable_flatline_discontinuity_and_temperature_spread():
    rows = []
    for i in range(4):
        row = BASE.copy(); row[0] = i; rows.append(row)
    rows[-1][1] = 100
    rows[-1][-2] = 60
    result = recording(rows)
    validate_recording(result, QualityConfig(flatline_min_samples=3, max_rate_per_s={'speed_kmh': 1}))
    assert any(issue['reason'] == 'extended_identical_values' for issue in result.observations[0].quality['battery_voltage_v'])
    assert any(issue['reason'] == 'sudden_discontinuity' for issue in result.observations[-1].quality['speed_kmh'])
    assert any(issue['reason'] == 'abnormal_temperature_spread' for issue in result.observations[-1].quality['cell_temperature_max_c'])


def test_power_sign_and_quality_propagation():
    rows = [BASE.copy(), BASE.copy()]
    rows[1][0] = 1; rows[1][5] = -30
    result = recording(rows)
    validate_recording(result, QualityConfig(max_rate_per_s={'battery_current_measured_a': 1}))
    calculate_power(result)
    assert result.observations[0].derived['signed_power_kw']['value'] == 8
    assert result.observations[1].derived['signed_power_kw']['value'] == -12
    quality = result.observations[1].derived['signed_power_kw']['quality']
    assert any(issue['reason'] == 'sudden_discontinuity' for issue in quality)
    assert any(issue['reason'] == 'current_polarity_unverified' for issue in quality)
    assert 'unverified' in result.metadata['derived_signals']['signed_power_kw']['sign_interpretation']


def test_dynamics_no_derivative_across_duplicate_time():
    rows = [BASE.copy(), BASE.copy(), BASE.copy()]
    rows[0][1] = 0; rows[1][0] = 1; rows[1][1] = 3.6; rows[2][0] = 1; rows[2][1] = 7.2
    result = recording(rows); validate_recording(result)
    # Duplicates taint both participating timestamps, so no derivative hides them.
    values = vehicle_dynamics(result)
    assert values[0]['stationary'] is True
    assert values[1]['acceleration_m_s2'] is None
    assert values[2]['acceleration_m_s2'] is None
    rows = [BASE.copy(), BASE.copy()]; rows[0][1] = 0; rows[1][0] = 1; rows[1][1] = 3.6
    result = recording(rows); validate_recording(result)
    assert vehicle_dynamics(result)[1]['acceleration_m_s2'] == pytest.approx(1)


def test_replay_order_pause_reset_speed_and_duplicates():
    rows = []
    for timestamp in [0, 0, 2, 10]:
        row = BASE.copy(); row[0] = timestamp; rows.append(row)
    result = recording(rows)
    replay = Replay(RecordingSource(result))
    replay.play(100)
    assert [row.row_number for row in replay.advance(100)] == [2, 3]
    assert replay.advance(101) == ()
    replay.set_speed(2, 101)
    assert [row.row_number for row in replay.advance(102)] == [4]
    replay.pause(103)
    position = replay.position_s
    assert replay.advance(1000) == () and replay.position_s == position
    replay.play(1000)
    assert [row.row_number for row in replay.advance(1003)] == [5]
    assert replay.finished and replay.current is result.observations[-1]
    replay.reset()
    assert replay.cursor == 0 and replay.position_s == 0 and not replay.playing
    replay.play(0)
    with pytest.raises(ValueError, match='monotonic'):
        replay.advance(-1)
    with pytest.raises(ValueError):
        replay.set_speed(0, 1)


@pytest.mark.parametrize('exporter,loader', [(export_recording_json, load_recording_json), (export_annotated_csv, load_annotated_csv)])
def test_export_consistency_and_summary(exporter, loader):
    rows = [BASE.copy(), BASE.copy()]; rows[1][0] = 'bad'; rows[1][6] = 110; rows[1][9] = -40
    result = recording(rows); validate_recording(result); calculate_power(result)
    stream = io.StringIO(); exporter(result, stream)
    restored = loader(io.StringIO(stream.getvalue()))
    assert restored.metadata == json.loads(json.dumps(result.metadata))
    assert [row.to_dict() for row in restored.observations] == [row.to_dict() for row in result.observations]
    diagnostic = io.StringIO(); export_diagnostic_summary(result, diagnostic)
    report = json.loads(diagnostic.getvalue())
    assert report['quality']['total_observations'] == 2
    assert report['quality']['timestamp_irregularities'] == 1
    assert report['metadata']['profile']['current_convention'] == 'unknown'


@pytest.mark.parametrize('options', [
    {'time_unit': 'minutes'}, {'current_convention': 'guess'}, {'units': {'hv_voltage': 'amps'}},
    {'units': {'unknown': 'V'}}, {'units': []}, {'dataset_id': ''},
])
def test_invalid_profiles(options):
    with pytest.raises(ValueError):
        DatasetProfile(**options)


@pytest.mark.parametrize('options', [
    {'flatline_min_samples': 1}, {'expected_interval_s': 0}, {'expected_interval_s': float('nan')},
    {'flatline_tolerance': -1}, {'ranges': {'soc_pct': [100, 0]}},
    {'max_rate_per_s': {'soc_pct': 0}}, {'sentinels': {'soc_pct': [float('nan')]}},
])
def test_invalid_quality_configs(options):
    with pytest.raises(ValueError):
        QualityConfig(**options)


def test_sheet_selection_limits_missing_time_and_bad_headers():
    result = load_xlsx(workbook(second_sheet=True), sheet='Other', profile=profile())
    assert result.observations[0].values['speed_kmh'] == 10
    with pytest.raises(ValueError, match='unknown worksheet'):
        load_xlsx(workbook(), sheet='missing')
    with pytest.raises(ValueError, match='max_rows'):
        load_xlsx(workbook([BASE, BASE]), max_rows=1)
    with pytest.raises(ValueError, match='unique'):
        load_xlsx(workbook([[1, 2]], ['time', 'time']))
    result = load_xlsx(workbook([[10]], ['vhc_speed']), profile=profile())
    validate_recording(result)
    assert result.observations[0].timestamp_s is None
    with pytest.raises(ValueError, match='timestamps'):
        Replay(RecordingSource(result))


def test_cli_workbook_and_no_overwrite(tmp_path):
    input_path = tmp_path / 'synthetic.xlsx'; input_path.write_bytes(workbook().getvalue())
    profile_path = tmp_path / 'profile.json'; profile_path.write_text(json.dumps({'units': UNITS, 'time_unit': 's'}))
    output = tmp_path / 'outputs/result'
    args = ['analyze-xlsx', str(input_path), '--profile', str(profile_path), '--output-prefix', str(output)]
    assert main(args) == 0
    assert output.with_suffix('.json').exists() and output.with_suffix('.csv').exists()
    assert (output.parent / 'result.diagnostics.json').exists()
    assert main(args) == 1


def test_bad_zip_and_empty_workbook_are_actionable():
    with pytest.raises(ValueError, match='readable .xlsx'):
        load_xlsx(io.BytesIO(b'not a zip workbook'))
    with pytest.raises(ValueError, match='no observations'):
        load_xlsx(workbook([]))


def test_power_range_rejection_and_diagnostic_derived_flags():
    row = BASE.copy(); row[4] = 0
    result = recording([row]); validate_recording(result); calculate_power(result)
    assert result.observations[0].derived['signed_power_kw']['value'] is None
    assert 'OUT_OF_RANGE' in {item['status'] for item in result.observations[0].derived['signed_power_kw']['quality']}
    assert quality_summary(result)['per_signal']['signed_power_kw']['statuses']['OUT_OF_RANGE'] == 1


def test_unverified_numeric_time_duplicates_detected_without_assuming_seconds():
    result = load_xlsx(workbook([BASE, BASE]))
    validate_recording(result)
    assert all(row.timestamp_s is None for row in result.observations)
    assert all(any(issue['reason'] == 'duplicate_timestamp' for issue in row.quality['timestamp_s']) for row in result.observations)


@pytest.mark.parametrize('options', [{'ranges': []}, {'ranges': {'soc_pct': ['0', '100']}},
                                    {'max_rate_per_s': {'soc_pct': '1'}}, {'sentinels': {'soc_pct': ['0']}},
                                    {'interval_absolute_tolerance_s': True}])
def test_threshold_types_must_not_silently_disable_checks(options):
    with pytest.raises(ValueError):
        QualityConfig(**options)
