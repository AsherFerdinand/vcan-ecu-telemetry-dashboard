"""Representative clock encodings and synthetic measurements, not a real dataset."""
import io
import json
from importlib.resources import files
import pytest
from openpyxl import Workbook
from can_lab.excel import TimestampParser, load_xlsx
from can_lab.recording import DatasetProfile
from can_lab.quality import QualityConfig, validate_recording, quality_summary
from can_lab.diagnostics import calculate_power
from can_lab.recording_review import inspect_timestamps, anomaly_report
from can_lab.recording_plots import prepare_signal_plot
from can_lab.recorded_io import export_recording_json, load_recording_json
from can_lab.replay import Replay, RecordingSource

TIMES = [401042909,401042919,401042929,401042939,401042949,401042959,401043009,401043019,401043029,401043039]


def book(times, temperatures=None, voltages=None):
    w=Workbook(); s=w.active
    s.append(['time','vhc_speed','hv_voltage','hv_current','bcell_soc','bcell_minTemp','bcell_minVoltage','charging_signal'])
    for i,t in enumerate(times):
        s.append([t, 10+i,322+i, -20+i,80, temperatures[i] if temperatures else 25,
                  voltages[i] if voltages else 4.0,3])
    b=io.BytesIO();w.save(b);w.close();b.seek(0)
    return b


def test_sample_clock_rollover_is_ten_seconds_without_inventing_year():
    r=load_xlsx(book(TIMES+[430235734]),profile=DatasetProfile(time_unit='MDDHHMMSS'))
    assert [x.timestamp_s for x in r.observations[:10]]==list(range(0,100,10))
    assert r.observations[-1].timestamp_s==2575705
    assert r.metadata['time_origin']['year'] is None
    assert r.metadata['time_interpretation_status']=='inferred_yearless_encoding'
    assert r.metadata['excel_time_number_formats']=={'General':11}
    assert [x.raw['time'] for x in r.observations]==TIMES+[430235734]
    validate_recording(r,QualityConfig(expected_interval_s=10))
    assert all(not x.quality.get('timestamp_s') for x in r.observations[:10])
    assert quality_summary(r)['dimensions']['timestamp_invalid_observations']==0
    assert quality_summary(r)['dimensions']['timestamp_anomaly_observations']==1
    evidence=inspect_timestamps(r)
    assert evidence['examples'][6]['raw_time']==401043009
    assert evidence['year'] is None


@pytest.mark.parametrize('value',[431000000,1301000000,401240000,401006000,401000060,400000000,229000000.5,True,'4.01042909e8',40104290,230000000])
def test_calendar_component_validation(value):
    parser=TimestampParser(DatasetProfile(time_unit='MDDHHMMSS'))
    value,error=parser.parse(value)
    assert value is None and error.startswith('invalid_encoded')


def test_month_ten_and_calendar_ambiguity():
    parser=TimestampParser(DatasetProfile(time_unit='MDDHHMMSS'))
    assert parser.parse(1001000000)==(0,None)  # October 1
    assert parser.parse(1002000000)==(86400,None)
    parser=TimestampParser(DatasetProfile(time_unit='MDDHHMMSS'))
    assert parser.parse(228000000)==(0,None)
    assert parser.parse(301000000)[1]=='yearless_february_elapsed_ambiguous'
    for leap,delta in [(True,172800),(False,86400)]:
        parser=TimestampParser(DatasetProfile(time_unit='MDDHHMMSS',calendar_leap=leap))
        parser.parse(228000000)
        assert parser.parse(301000000)==(delta,None)
    parser=TimestampParser(DatasetProfile(time_unit='MDDHHMMSS',calendar_leap=False))
    assert parser.parse(229000000)[1]=='invalid_encoded_calendar_components'
    with pytest.raises(ValueError,match='relative'):
        DatasetProfile(time_unit='MDDHHMMSS',time_basis='unix')


def test_no_year_rollover_is_assumed():
    parser=TimestampParser(DatasetProfile(time_unit='MDDHHMMSS'))
    parser.parse(1231235959)
    value,error=parser.parse(101000000)
    assert value is None and error=='yearless_rollover_or_clock_reversal'


def test_unit_warnings_do_not_invalidate_finite_physical_measurements():
    r=load_xlsx(book([0,1,2]))
    validate_recording(r); calculate_power(r)
    summary=quality_summary(r)
    assert summary['suspicious_observations']==3  # Legacy conservative flags unchanged.
    d=summary['dimensions']
    assert d['metadata_unverified_observations']==3
    assert d['physically_suspicious_observations']==0
    assert d['numerically_plausible_observations']==3
    assert d['timestamp_unverified_observations']==3
    assert d['timestamp_invalid_observations']==0
    assert d['physical_checks_incomplete_observations']==3


def test_raw_candidates_are_flagged_without_asserting_units():
    r=load_xlsx(book([0,1,2],temperatures=[25,-40,25],voltages=[4,4,0]))
    validate_recording(r)
    d=quality_summary(r)['dimensions']
    assert d['physically_suspicious_observations']==2
    assert r.observations[1].raw['bcell_minTemp']==-40
    report=anomaly_report(r)
    assert report['cell_temperature_min_c']['raw_minus40_count']==1
    assert report['cell_voltage_min_v']['raw_zero_count']==1
    assert r.observations[1].values['cell_temperature_min_c'] is None


def test_missing_dimension_is_separate():
    r=load_xlsx(book([None,'invalid']))
    validate_recording(r)
    d=quality_summary(r)['dimensions']
    assert d['timestamp_invalid_observations']==2
    assert d['missing_data_observations']==2  # Optional missing columns are reported.
    assert d['physically_suspicious_observations']==0


def test_source_profile_only_marks_documented_quantities():
    p=DatasetProfile(**json.loads(files('can_lab').joinpath('data/translab_scut_vehicle1_review.json').read_text()))
    r=load_xlsx(book(TIMES),profile=p); validate_recording(r,QualityConfig(expected_interval_s=10));calculate_power(r)
    assert r.metadata['signals']['battery_voltage_v']['unit_status']=='source_documented'
    assert r.metadata['signals']['soc_pct']['unit_status']=='unverified'
    assert r.observations[0].values['soc_pct'] is None
    assert not r.observations[0].quality.get('charging_status')
    assert r.metadata['profile']['current_convention']=='unknown'
    output=io.StringIO();export_recording_json(r,output)
    restored=load_recording_json(io.StringIO(output.getvalue()))
    assert restored.metadata['profile']['unit_references']==p.unit_references
    assert restored.observations[0].raw==r.observations[0].raw
    replay=Replay(RecordingSource(r));replay.play(0)
    assert len(replay.advance(10))==2


def test_shared_plot_domain_boundaries_and_no_false_connections():
    p=DatasetProfile(time_unit='s', units={'vhc_speed':'km/h','hv_voltage':'V'})
    r=load_xlsx(book([0,10,20,1000,1010,5]),profile=p)
    validate_recording(r,QualityConfig(expected_interval_s=10,session_gap_s=100))
    assert [x['index'] for x in r.metadata['recording_boundaries']]==[3,5]
    speed=prepare_signal_plot(r,list(range(6)),'speed_kmh')
    voltage=prepare_signal_plot(r,list(range(6)),'battery_voltage_v')
    assert speed['domain']==voltage['domain'] and speed['use_time']
    assert speed['data'][2]['group']!=speed['data'][3]['group']
    assert speed['data'][4]['group']!=speed['data'][5]['group']
    narrow=prepare_signal_plot(r,[1,2],'speed_kmh')
    assert narrow['domain']==[10,20]
    unknown=load_xlsx(book([0,1]));validate_recording(unknown)
    plot=prepare_signal_plot(unknown,[0,1],'speed_kmh')
    assert not plot['use_time'] and [x['x'] for x in plot['data']]==[2,3]


def test_missing_signal_breaks_lines_even_after_sampling():
    p=DatasetProfile(time_unit='s',units={'vhc_speed':'km/h'})
    r=load_xlsx(book(list(range(20))),profile=p)
    r.observations[10].values['speed_kmh']=None
    validate_recording(r)
    plot=prepare_signal_plot(r,list(range(20)),'speed_kmh',max_points=8)
    before=[x for x in plot['data'] if x['row_number']<12]
    after=[x for x in plot['data'] if x['row_number']>12]
    assert before[-1]['group']!=after[0]['group']
    assert len(plot['data'])<=8


def test_numerical_plausibility_and_flatline_suspicion_can_overlap():
    r=load_xlsx(book([0,1,2]),profile=DatasetProfile(time_unit='s',units={'bcell_minVoltage':'V'}))
    validate_recording(r,QualityConfig(flatline_min_samples=3))
    d=quality_summary(r)['dimensions']
    assert d['numerically_plausible_observations']==3
    assert d['physically_suspicious_observations']==3
    r.observations[1].values['cell_voltage_min_v']=0
    validate_recording(r,QualityConfig(flatline_min_samples=3))
    assert quality_summary(r)['dimensions']['numerically_plausible_observations']==2
