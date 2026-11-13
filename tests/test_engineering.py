"""Analytically verifiable synthetic engineering fixtures; no real data required."""
from dataclasses import asdict
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import pytest
from can_lab.recording import COLUMNS, DatasetProfile, Observation, Recording
from can_lab.quality import QualityConfig,validate_recording
from can_lab.operating import OperatingConfig,analyze_operating_states
from can_lab.energy import EnergyConfig,integrate_energy,trapezoid_components
from can_lab.cells import CellConfig,analyze_cells
from can_lab.engineering import EngineeringConfig,analyze_engineering
from can_lab.engineering_reports import (build_report,export_engineering_json,export_engineering_markdown,
    export_engineering_csv,iter_features)
from can_lab.recorded_io import export_recording_json,load_recording_json,export_annotated_csv,load_annotated_csv
from can_lab.diagnostics import calculate_power


def make_recording(times=(0,10,20),*,speed=None,current=None,voltage=None,convention='unknown',status=None,odometer=None,unit_overrides=None):
    units={key:unit for key,(_,unit) in COLUMNS.items() if unit is not None}
    if unit_overrides is not None:units=unit_overrides
    profile=DatasetProfile(dataset_id='SYNTHETIC analytic engineering fixture',time_unit='s',units=units,
        current_convention=convention,current_reference='Synthetic fixture polarity definition' if convention!='unknown' else '',status_codes={'1':'charging mode','3':'driving mode'},status_reference='synthetic fixture definition')
    raw=[];rows=[]
    for i,t in enumerate(times):
        data={'time':t,'vhc_speed':speed[i] if speed is not None else 36,'hv_voltage':voltage[i] if voltage is not None else 400,
              'hv_current':current[i] if current is not None else 25,'charging_signal':status[i] if status is not None else 3,
              'vhc_totalMile':odometer[i] if odometer is not None else 1000+i/10,'bcell_soc':80-i/10,
              'bcell_maxVoltage':4.1,'bcell_minVoltage':4.0,'bcell_maxTemp':26,'bcell_minTemp':25}
        values={target:profile.normalize(key,data[key]) for key,(target,_) in COLUMNS.items()}
        rows.append(Observation(i+2,t,data,values));raw.append(data)
    metadata={'schema':'can-lab-recording-1','data_kind':'synthetic_decoded_telemetry','profile':asdict(profile),
        'signals':{target:{'source_column':key,'canonical_unit':unit,'source_unit':units.get(key),'unit_status':'user_declared' if key in units else 'unverified'} for key,(target,unit) in COLUMNS.items()},
        'source_filename':'synthetic-json-fixture','sha256':hashlib.sha256(json.dumps(raw).encode()).hexdigest(),
        'sha256_scope':'synthetic raw JSON, not a real workbook','normalized_time_basis':'relative','time_interpretation_status':'profile_declared'}
    recording=Recording(metadata,rows)
    validate_recording(recording,QualityConfig(expected_interval_s=10))
    calculate_power(recording)
    return recording


def test_acceleration_deceleration_stationary_and_constant_speed():
    r=make_recording((0,10,20,30,40),speed=[0,36,72,36,36])
    points=analyze_operating_states(r,OperatingConfig(smoothing_samples=1))
    assert points[0].candidates==('stationary',)
    assert points[1].acceleration_m_s2==pytest.approx(1)
    assert points[1].candidates==('acceleration',)
    assert points[2].acceleration_m_s2==pytest.approx(1)
    assert points[3].acceleration_m_s2==pytest.approx(-1)
    assert points[3].candidates==('deceleration',)
    assert points[4].candidates==('approximately_constant_speed',)


def test_median_smoothing_and_noise_thresholds():
    r=make_recording((0,10,20,30,40),speed=[36,36.1,35.9,36,36.1])
    points=analyze_operating_states(r,OperatingConfig(smoothing_samples=3))
    assert all('acceleration' not in p.candidates and 'deceleration' not in p.candidates for p in points)
    assert points[-1].smoothed_speed_kmh==36


def test_gaps_reset_smoothing_and_derivatives():
    r=make_recording((0,10,20,1000,1010),speed=[0,36,72,36,72])
    points=analyze_operating_states(r,OperatingConfig(smoothing_samples=1))
    assert points[3].acceleration_m_s2 is None
    assert 'recording_boundary' in points[3].warnings
    assert points[4].acceleration_m_s2==1


def test_irregular_intervals_use_actual_dt_but_long_intervals_are_rejected():
    r=make_recording((0,20,60),speed=[0,72,144])
    points=analyze_operating_states(r,OperatingConfig(smoothing_samples=1,max_derivative_interval_s=30))
    assert points[1].acceleration_m_s2==1
    assert points[2].acceleration_m_s2 is None
    assert any('irregular_interval' in item for item in points[1].warnings)


def test_documented_charging_code_and_unknown_polarity():
    r=make_recording((0,10),speed=[36,0],current=[25,-25],status=[3,1])
    points=analyze_operating_states(r,OperatingConfig(smoothing_samples=1))
    assert 'charging' in points[1].candidates and points[1].source_reported_state=='charging mode'
    assert 'possible_regenerative_braking' not in points[1].candidates
    r.metadata['profile']['status_reference']=''
    assert 'charging' not in analyze_operating_states(r)[1].candidates


@pytest.mark.parametrize('convention,current,expected',[('unknown',-25,False),('positive_discharge',-25,True),('positive_charge',25,True),('positive_discharge',25,False)])
def test_regeneration_requires_polarity_and_deceleration_evidence(convention,current,expected):
    r=make_recording((0,10),speed=[72,36],current=[current,current],convention=convention)
    points=analyze_operating_states(r,OperatingConfig(smoothing_samples=1))
    assert ('possible_regenerative_braking' in points[1].candidates) is expected
    assert 'deceleration' in points[1].candidates
    assert 'inferred_candidates' in points[1].verification


def test_constant_stationary_signal_is_not_discarded_by_flatline_heuristic():
    r=make_recording(tuple(range(0,400,10)),speed=[0]*40)
    assert any(i['reason']=='extended_identical_values' for i in r.observations[0].quality['speed_kmh'])
    assert all('stationary' in p.candidates for p in analyze_operating_states(r))


@pytest.mark.parametrize('p0,p1,dt,positive,negative',[(10,10,3600,10,0),(-10,-10,3600,0,-10),(10,-10,3600,2.5,-2.5),(-10,10,3600,2.5,-2.5),(2,6,1800,2,0),(0,0,10,0,0),(0,-10,3600,0,-5)])
def test_analytic_energy_components(p0,p1,dt,positive,negative):
    pos,neg=trapezoid_components(p0,p1,dt)
    assert pos==pytest.approx(positive) and neg==pytest.approx(negative)
    assert pos+neg==pytest.approx((p0+p1)*dt/7200)


def test_constant_power_energy_and_matched_distance():
    r=make_recording((0,10,20),odometer=[0,.1,.2])
    energy=integrate_energy(r)
    assert energy['signed_net_kwh']==pytest.approx(10*20/3600)
    assert energy['included_intervals']==2 and energy['excluded_intervals']==0
    assert energy['distance_over_energy_intervals_km']==pytest.approx(.2)
    assert energy['qualified_signed_kwh_per_km']==pytest.approx(10*20/3600/.2)
    assert energy['flagged_included_intervals']==2  # Unknown polarity is retained.
    assert energy['current_convention']=='unknown'


def test_energy_does_not_bridge_recording_gaps():
    r=make_recording((0,10,20,1000,1010,1020))
    energy=integrate_energy(r)
    assert energy['included_intervals']==4
    assert energy['excluded_reasons']=={'recording_boundary':1}
    assert energy['signed_net_kwh']==pytest.approx(10*40/3600)


def test_invalid_electrical_and_time_inputs_are_excluded_not_deleted():
    r=make_recording((0,10,20),voltage=[400,0,400])
    original=[row.raw.copy() for row in r.observations]
    assert integrate_energy(r)['included_intervals']==0
    assert integrate_energy(r)['excluded_reasons']['unusable_electrical_measurement']==2
    assert [row.raw for row in r.observations]==original
    r=make_recording((0,10,10,20))
    assert integrate_energy(r)['included_intervals']==0  # Both duplicate endpoints are tainted.


def test_energy_short_gap_config_and_distance_qualification():
    r=make_recording((0,10,50))
    energy=integrate_energy(r)
    assert energy['included_intervals']==1
    assert energy['excluded_reasons']=={'maximum_interval_exceeded':1}
    r.observations[1].values['odometer_km']=None
    assert integrate_energy(r)['qualified_signed_kwh_per_km'] is None
    assert integrate_energy(r)['signed_net_kwh']>0


def test_unknown_units_do_not_produce_power_or_regeneration():
    r=make_recording(unit_overrides={})
    analysis=analyze_engineering(r)
    assert analysis.energy['included_intervals']==0
    assert analysis.electrical['signed_power_kw']['count']==0
    assert all(point.candidates==('insufficient_evidence',) for point in analysis.operating)


def test_cell_spreads_and_temperature_trends():
    r=make_recording((0,10))
    r.observations[1].values['cell_temperature_max_c']=28
    points=analyze_cells(r)
    assert points[0].voltage_spread_v==pytest.approx(.1)
    assert points[0].temperature_spread_c==1
    assert points[1].temperature_spread_c==3
    assert points[1].max_temperature_rate_c_s==pytest.approx(.2)


def test_negative_spreads_zero_voltage_and_minus40_are_measurement_anomalies():
    r=make_recording((0,10,20))
    r.observations[0].values['cell_voltage_min_v']=4.2
    r.observations[0].values['cell_temperature_min_c']=27
    r.observations[1].values['cell_voltage_min_v']=0
    r.observations[1].values['cell_temperature_min_c']=-40
    validate_recording(r)
    points=analyze_cells(r)
    assert 'negative_voltage_spread' in points[0].voltage_quality
    assert 'negative_temperature_spread' in points[0].temperature_quality
    assert 'zero_cell_voltage' in points[1].voltage_quality
    assert 'possible_minus40_temperature_sentinel' in points[1].temperature_quality
    assert any('OUT_OF_RANGE' in q for q in points[1].voltage_quality)
    assert any('abrupt_temperature_change' in q for q in points[1].temperature_quality)


def test_cell_trend_not_calculated_across_gap():
    r=make_recording((0,1000))
    assert analyze_cells(r)[1].max_temperature_rate_c_s is None


def test_sessions_preserve_boundaries_statistics_and_signed_energy():
    r=make_recording((0,10,20,1000,1010),speed=[0,36,72,0,0],status=[3,3,3,1,1])
    analysis=analyze_engineering(r,EngineeringConfig(operating=OperatingConfig(smoothing_samples=1)))
    assert len(analysis.sessions)==2
    first,second=analysis.sessions
    assert first['observations']==3 and first['duration_s']==20 and first['speed_kmh']['max']==72
    assert second['observations']==2 and second['charging_intervals'][0]['observations']==2
    assert second['source_reported_status_counts']=={'charging mode':2}
    assert first['candidate_dynamics_events'][0]['candidate']=='acceleration'
    assert first['candidate_dynamics_events'][0]['voltage_change_v']==0
    assert sum(s['energy']['signed_net_kwh'] for s in analysis.sessions)==pytest.approx(analysis.energy['signed_net_kwh'])
    assert first['soc_change_pct']==pytest.approx(-.2)


def test_report_provenance_definitions_limitations_and_exports():
    r=make_recording();analysis=analyze_engineering(r)
    report=build_report(r,analysis)
    assert report['provenance']['profile']['dataset_id'].startswith('SYNTHETIC')
    assert report['measurement_coverage']['observations']==3
    assert report['cell_diagnostics']['voltage_spread_v']['min']==pytest.approx(.1)
    assert any('polarity unknown' in s for s in report['limitations'])
    assert 'not charging/discharging' in report['energy']['sign_labels']
    out=io.StringIO();export_engineering_json(r,analysis,out)
    assert json.loads(out.getvalue())['sessions'][0]['observations']==3
    markdown=io.StringIO();export_engineering_markdown(r,analysis,markdown)
    assert 'Engineering limitations' in markdown.getvalue() and 'not verified vehicle efficiency' in markdown.getvalue()
    features=io.StringIO();export_engineering_csv(r,analysis,features)
    text=features.getvalue(); assert text.startswith('# can-lab-engineering-features-1 metadata=')
    csv_rows=list(csv.DictReader(io.StringIO(text.split('\n',1)[1])))
    expected=list(iter_features(r,analysis))
    assert len(csv_rows)==3
    assert float(csv_rows[0]['signed_power_kw'])==expected[0]['signed_power_kw']
    assert json.loads(csv_rows[0]['operating_candidates'])==expected[0]['operating_candidates']
    # Phase 2 recording interchange stays intact after engineering analysis.
    for exporter,loader in [(export_recording_json,load_recording_json),(export_annotated_csv,load_annotated_csv)]:
        output=io.StringIO();exporter(r,output)
        restored=loader(io.StringIO(output.getvalue()))
        assert [row.to_dict() for row in restored.observations]==[row.to_dict() for row in r.observations]


@pytest.mark.parametrize('config',[{'operating':{'smoothing_samples':2}},{'operating':{'max_derivative_interval_s':0}},
    {'energy':{'max_interval_s':float('nan')}},{'cells':{'max_voltage_spread_v':-1}},
    {'power_histogram_bins':0},{'unknown':{}},{'energy':[]}])
def test_invalid_engineering_configuration(config):
    with pytest.raises(ValueError):EngineeringConfig.from_dict(config)


def test_engineering_modules_do_not_require_can_or_dashboard_libraries():
    code='''
import importlib.abc,sys
class NoExternal(importlib.abc.MetaPathFinder):
 def find_spec(self, fullname, path=None, target=None):
  if fullname.split('.')[0] in ('can','cantools','pandas','openpyxl','streamlit'):
   raise ImportError('external dependency unavailable')
sys.meta_path.insert(0,NoExternal())
from can_lab.engineering import EngineeringConfig
from can_lab.energy import trapezoid_components
from can_lab.engineering_reports import build_report
assert trapezoid_components(1,1,3600)==(1,0)
'''
    subprocess.run([sys.executable,'-c',code],check=True)


def test_unreferenced_declared_polarity_is_not_enough_for_regeneration():
    r=make_recording((0,10),speed=[72,36],current=[-25,-25],convention='positive_discharge')
    r.metadata['profile']['current_reference']=''
    points=analyze_operating_states(r,OperatingConfig(smoothing_samples=1))
    assert 'possible_regenerative_braking' not in points[-1].candidates
    assert 'current_polarity_not_documented_regeneration_not_assessed' in points[-1].warnings


def test_report_cli_and_optional_feature_csv(tmp_path):
    from can_lab.cli import main
    root=Path(__file__).parents[1]
    workbook=tmp_path/'example.xlsx'
    subprocess.run([sys.executable,str(root/'examples/make_ev_fixture.py'),str(workbook)],check=True,capture_output=True)
    output=tmp_path/'report'
    args=['report-xlsx',str(workbook),'--profile',str(workbook.with_suffix('.profile.json')),'--output-prefix',str(output),'--include-features']
    assert main(args)==0
    report=json.loads((tmp_path/'report.engineering.json').read_text())
    assert report['schema']=='can-lab-engineering-report-1'
    assert report['measurement_coverage']['observations']==60
    assert (tmp_path/'report.engineering.md').read_text().startswith('# Virtual ECU & CAN Lab')
    assert (tmp_path/'report.features.csv').read_text().startswith('# can-lab-engineering-features-1')
    assert main(args)==1


def test_unequal_sign_crossing_is_split_analytically():
    pos,neg=trapezoid_components(20,-10,3600)
    assert pos==pytest.approx(20/3*1)
    assert neg==pytest.approx(-5/3)
    assert pos+neg==pytest.approx(5)


def test_cached_pre_power_quality_is_refreshed_for_engineering_report():
    from can_lab.quality import quality_summary
    r=make_recording()
    validate_recording(r)
    before=quality_summary(r)
    assert 'signed_power_kw' not in before['per_signal']
    analysis=analyze_engineering(r,quality=before)
    assert 'signed_power_kw' in analysis.quality['per_signal']


def test_energy_rejects_nonrepresentable_output_and_avoids_intermediate_overflow():
    with pytest.raises(ValueError,match='finite kWh'):
        trapezoid_components(1e308,1e308,1e308)
    positive,negative=trapezoid_components(1e308,1e308,1e-308)
    assert positive==pytest.approx(1/3600) and negative==0


def test_direct_configuration_rejects_wrong_component_types():
    with pytest.raises(ValueError):EngineeringConfig(operating={})


def test_engineering_sampling_does_not_mislabel_missing_time_as_actual_seconds():
    from can_lab.engineering_dashboard import feature_frame
    r=make_recording(tuple(range(0,20000,10)))
    r.observations[1].timestamp_s=None
    validate_recording(r)
    analysis=analyze_engineering(r)
    frame=feature_frame(r,analysis,list(range(2000)))
    assert len(frame)<=1500
    assert frame.attrs['use_time'] is False
    assert frame.attrs['x_domain']==[2,2001]
    assert frame.iloc[0]['x']==2


def test_engineering_preserves_custom_source_and_derived_definitions():
    r=make_recording()
    r.metadata['source_custom']={'note':'preserve original provenance'}
    r.metadata['derived_signals']['external_signal']={'formula':'external reference'}
    raw=[row.raw.copy() for row in r.observations]
    analyze_engineering(r)
    assert r.metadata['source_custom']=={'note':'preserve original provenance'}
    assert r.metadata['derived_signals']['external_signal']=={'formula':'external reference'}
    assert [row.raw for row in r.observations]==raw
