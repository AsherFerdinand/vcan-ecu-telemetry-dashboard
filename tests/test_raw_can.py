"""Small, authored fixtures; no research download or physical-accuracy claim."""
from dataclasses import asdict
import hashlib
import io
import json
from pathlib import Path
import pytest
from can_lab.can_recording import CANConfig, investigate_candump, check_references
from can_lab.codec import load_classical_dbc
from can_lab.can_reports import export_can_json, export_can_markdown, build_can_report
from can_lab.recorded_io import export_recording_json, load_recording_json, export_annotated_csv, load_annotated_csv
from can_lab.engineering import analyze_engineering
from can_lab.cli import main
from can_lab.artifacts import build_manifest, generated_output, external_data_directory, checked_source_metadata

FIXTURE=Path(__file__).parent/'fixtures/raw_can'
MAPPING=json.loads((FIXTURE/'mapping.json').read_text())
REFERENCES=json.loads((FIXTURE/'references.json').read_text())


def inspect(source=None,**kwargs):
    return investigate_candump(source if source is not None else FIXTURE/'example.log',FIXTURE/'example.dbc',mapping=MAPPING,**kwargs)


def test_complete_fixture_counts_units_values_and_raw_trace():
    r=inspect(references=REFERENCES)
    assert r.coverage['scanned_records']==7
    assert r.coverage['decoded_frames']==4 and r.coverage['unknown_id_frames']==1
    assert r.coverage['invalid_length_frames']==1 and r.coverage['malformed_records']==1
    assert r.coverage['complete_source_scanned'] and not r.coverage['limit_reached']
    first=r.frames[0]
    assert first.signals=={'VehicleSpeed':72.3,'EngineSpeed':2000,'Temperature':-5}
    assert r.frames[1].signals['PackCurrent']==-25
    assert r.definitions['288']['signals']['EngineSpeed']['byte_order']=='big_endian'
    assert r.definitions['289']['signals']['PackCurrent']['signed']
    assert r.validation['passed']==5 and r.validation['failed']==0
    assert r.validation['physical_accuracy']=='not_established'
    obs=r.recording.observations[0]
    assert obs.values['speed_kmh']==72.3 and obs.values['rpm']==2000
    assert obs.values['battery_voltage_v'] is None
    assert obs.raw['frame_ref']==0 and first.frame.line_number==2
    source=(FIXTURE/'example.log').read_bytes()
    assert source[first.frame.byte_offset:].splitlines()[0].startswith(b'(0.000000)')
    assert first.frame.timestamp_text=='0.000000'
    assert r.recording.metadata['can_frames'][0]['payload_hex']=='D3021F4023000000'
    assert 'payload_hex' not in obs.raw
    assert r.recording.observations[1].derived['signed_power_kw']['value']==-10
    assert r.recording.canonical_samples()[0].rpm==2000


def test_sparse_adapter_never_merges_unsynchronised_frames():
    r=inspect()
    assert len(r.recording.observations)==4
    assert [o.raw['frame_ref'] for o in r.recording.observations]==[0,1,2,5]
    assert all(o.values['soc_pct'] is None for o in r.recording.observations)
    assert r.recording.observations[0].derived['signed_power_kw']['value'] is None
    analysis=analyze_engineering(r.recording)
    assert analysis.energy['included_intervals']==0  # Only one frame contains V and I.
    assert r.recording.metadata['profile']['current_convention']=='unknown'


def test_separate_voltage_and_current_frames_do_not_produce_power():
    # Explicit two-message synthetic definition with real physical units, but no
    # claim of simultaneous acquisition even when the timestamps are identical.
    dbc=b'''VERSION "synthetic"
NS_ :
BS_:
BU_: X
BO_ 256 V: 2 X
 SG_ Voltage : 0|16@1+ (1,0) [0|1000] "V" X
BO_ 257 I: 2 X
 SG_ Current : 0|16@1- (1,0) [-1000|1000] "A" X
'''
    mapping=[{'frame_id':256,'signal':'Voltage','target':'battery_voltage_v'},
             {'frame_id':257,'signal':'Current','target':'battery_current_measured_a'}]
    result=investigate_candump(io.BytesIO(b'(1.0) can0 100#9001\n(1.0) can0 101#1900\n'),io.BytesIO(dbc),mapping=mapping)
    assert len(result.recording.observations)==2
    assert all(row.derived['signed_power_kw']['value'] is None for row in result.recording.observations)


@pytest.mark.parametrize('exporter,loader',[(export_recording_json,load_recording_json),(export_annotated_csv,load_annotated_csv)])
def test_recording_round_trip_retains_frame_table_rpm_and_provenance(exporter,loader):
    r=inspect()
    out=io.StringIO();exporter(r.recording,out)
    restored=loader(io.StringIO(out.getvalue()))
    assert restored.metadata==json.loads(json.dumps(r.recording.metadata))
    assert [o.to_dict() for o in restored.observations]==[o.to_dict() for o in r.recording.observations]
    assert restored.signals[-1]=='rpm'
    assert restored.metadata['can_definitions']['288']['signals']['VehicleSpeed']['scale']==.1


@pytest.mark.parametrize('line,key',[
    (b'(1.0) can0 120##10000000000000000\n','unsupported_frames'),
    (b'(1.0) can0 00000120#0000000000000000\n','unsupported_frames'),
    (b'(1.0) can0 120#R\n','unsupported_frames'),
    (b'(1.0) can0 120#ABC\n','malformed_records'),
    (b'(1.0) can0 FFF#00\n','malformed_records'),
    (b'garbage\n','malformed_records'),
    (b'(-1.0) can0 120#0000000000000000\n','malformed_records'),
    (b'(1.0) can0 120#000000000000000000\n','malformed_records'),
])
def test_unsupported_and_malformed_are_explicit_counts(line,key):
    r=inspect(io.BytesIO(line))
    assert r.coverage[key]==1 and r.coverage['decoded_frames']==0
    assert not r.recording.observations


def test_timestamp_precision_and_source_stream_positions_are_retained():
    stream=io.BytesIO(b'(1700000000.123456789) can0 120#D3021F4023000000\n')
    dbc=io.BytesIO((FIXTURE/'example.dbc').read_bytes())
    stream.seek(3);dbc.seek(5)
    r=investigate_candump(stream,dbc,mapping=MAPPING)
    assert stream.tell()==3 and dbc.tell()==5
    assert r.frames[0].frame.timestamp_text=='1700000000.123456789'
    assert r.recording.observations[0].raw['time']=='1700000000.123456789'
    assert r.source['sha256']==hashlib.sha256(stream.getvalue()).hexdigest()


def test_filters_limits_and_coverage_scope():
    r=inspect(config=CANConfig(max_frames=2,max_preview_frames=1))
    assert len(r.frames)==2 and r.coverage['scanned_records']==2 and r.coverage['limit_reached']
    assert len(build_can_report(r)['frame_preview'])==1
    r=inspect(config=CANConfig(start_s=.02,end_s=.04))
    assert r.coverage['time_filtered']==3
    assert len(r.frames)==3
    assert r.frames[0].frame.line_number==4
    assert r.source['sha256']==hashlib.sha256((FIXTURE/'example.log').read_bytes()).hexdigest()


def test_channels_are_never_silently_combined():
    stream=b'(1) can0 120#D3021F4023000000\n(2) can1 120#D3021F4023000000\n'
    with pytest.raises(ValueError,match='multiple selected channels'):inspect(io.BytesIO(stream))
    r=inspect(io.BytesIO(stream),config=CANConfig(channel='can1'))
    assert len(r.frames)==1 and r.frames[0].frame.channel=='can1'
    assert r.coverage['channel_filtered']==1


def test_resource_limits_fail_cleanly_without_source_modification():
    source=io.BytesIO((FIXTURE/'example.log').read_bytes());original=source.getvalue()
    with pytest.raises(ValueError,match='byte limit'):inspect(source,config=CANConfig(max_source_bytes=10))
    assert source.getvalue()==original and source.tell()==0
    with pytest.raises(ValueError,match='line-byte limit'):inspect(source,config=CANConfig(max_line_bytes=10))
    assert source.getvalue()==original


def test_large_stream_processing_retains_only_explicit_frame_budget(tmp_path):
    path=tmp_path/'large-synthetic.log'
    with path.open('wb') as out:
        for i in range(20000):out.write(f'({i}.0) can0 120#D3021F4023000000\n'.encode())
    r=inspect(path,config=CANConfig(max_frames=10,max_preview_frames=3))
    assert len(r.frames)==len(r.recording.observations)==10
    assert r.coverage['limit_reached'] and not r.coverage['complete_source_scanned']
    assert len(r.recording.metadata['can_frames'])==10
    assert r.source['bytes']==path.stat().st_size
    assert len(build_can_report(r)['frame_preview'])==3


@pytest.mark.parametrize('kwargs',[{'max_frames':0},{'max_source_bytes':-1},{'start_s':float('nan')},
    {'start_s':2,'end_s':1},{'time_basis':'guess'},{'channel':'bad channel'}])
def test_invalid_limits(kwargs):
    with pytest.raises(ValueError):CANConfig(**kwargs)


@pytest.mark.parametrize('dbc',[b'not a dbc',b'VERSION "empty"\nNS_ :\nBS_:\nBU_: X\n',
    b'VERSION "synthetic"\nNS_ :\nBS_:\nBU_: X\nBO_ 2147483936 X: 8 X\n SG_ N : 0|8@1+ (1,0) [0|255] "km/h" X\n',
    b'VERSION "synthetic"\nNS_ :\nBS_:\nBU_: X\nBO_ 256 X: 8 X\n SG_ M M : 0|4@1+ (1,0) [0|15] "" X\n SG_ N m1 : 8|8@1+ (1,0) [0|255] "km/h" X\n'])
def test_invalid_or_unsupported_dbc_is_rejected(dbc):
    with pytest.raises(ValueError):load_classical_dbc(dbc.decode())


@pytest.mark.parametrize('mapping',[{},[{'frame_id':288,'signal':'VehicleSpeed','target':'not_a_signal'}],
    [{'frame_id':288,'signal':'VehicleSpeed','target':'rpm'}],
    [{'frame_id':288,'signal':'absent','target':'speed_kmh'}],MAPPING+[MAPPING[0]]])
def test_invalid_mappings(mapping):
    with pytest.raises(ValueError):investigate_candump(FIXTURE/'example.log',FIXTURE/'example.dbc',mapping=mapping)


def test_reference_failures_missing_vectors_and_hash_binding():
    r=inspect();evidence=json.loads(json.dumps(REFERENCES))
    evidence['vectors'][0]['expected']=73
    assert check_references(r,evidence)['failed']==1
    evidence['vectors'][0]['payload_hex']='0000000000000000'
    assert check_references(r,evidence)['not_observed']==1
    evidence['dbc_sha256']='0'*64
    with pytest.raises(ValueError,match='exact DBC'):check_references(r,evidence)
    evidence=json.loads(json.dumps(REFERENCES));evidence['vectors'][0]['absolute_tolerance']=-1
    with pytest.raises(ValueError):check_references(r,evidence)


def test_deterministic_reports_and_manifest_without_private_paths(tmp_path):
    r=inspect(references=REFERENCES)
    outputs=[]
    for name,exporter in [('report.json',export_can_json),('report.md',export_can_markdown)]:
        a=io.StringIO();b=io.StringIO();exporter(r,a);exporter(r,b)
        assert a.getvalue()==b.getvalue()
        path=tmp_path/name;path.write_text(a.getvalue());outputs.append(path)
    manifest=build_manifest(r,outputs,output_root=tmp_path,reproduction={'command':['can-lab','investigate-can','${VCAN_DATA_DIR}/example.log']},validation_timestamp='2026-11-13T00:00:00+00:00')
    assert manifest['source']['sha256']==r.source['sha256']
    assert manifest['dbc']['sha256']==r.dbc['sha256']
    assert manifest['outputs'][0]['path']=='report.json'
    assert str(tmp_path) not in json.dumps(manifest)
    assert manifest['git']['commit']
    assert manifest['physical_accuracy']=='not_established'


def test_output_safety_refuses_overwrites_outside_roots_and_symlinks(tmp_path):
    root=tmp_path/'generated';root.mkdir()
    known=root/'historical.csv';known.write_text('important evidence')
    with pytest.raises(ValueError):generated_output(known,root)
    with pytest.raises(ValueError):generated_output(tmp_path/'outside.json',root)
    outside=tmp_path/'evidence';outside.mkdir()
    try:(root/'escape').symlink_to(outside,target_is_directory=True)
    except OSError:pytest.skip('symlinks unavailable on this platform')
    with pytest.raises(ValueError):generated_output(root/'escape'/'report.json',root)
    assert known.read_text()=='important evidence'


@pytest.mark.parametrize('metadata',[{'url':'https://user:secret@example.com/x'},{'url':'https://example.com/x?token=secret'},
    {'dataset_id':'/private/user/capture.log'},{'path':'ignored'}])
def test_metadata_rejects_credentials_and_absolute_private_paths(metadata):
    with pytest.raises(ValueError):checked_source_metadata(metadata)


def test_configurable_data_directory_does_not_create_or_delete(monkeypatch,tmp_path):
    path=tmp_path/'external-data';monkeypatch.setenv('VCAN_DATA_DIR',str(path))
    assert external_data_directory()==path and not path.exists()


def test_cli_optional_exports_and_manifest_hash_verification(tmp_path):
    root=Path(__file__).parents[1]
    prefix=tmp_path/'review'
    args=['investigate-can',str(FIXTURE/'example.log'),'--dbc',str(FIXTURE/'example.dbc'),
        '--mapping',str(FIXTURE/'mapping.json'),'--references',str(FIXTURE/'references.json'),
        '--provenance',str(root/'data/manifests/synthetic_can.json'),'--time-basis','relative',
        '--output-prefix',str(prefix),'--output-root',str(tmp_path),'--include-recording','--engineering-report']
    assert main(args)==0
    assert json.loads((tmp_path/'review.can.json').read_text())['validation']['passed']==5
    assert json.loads((tmp_path/'review.manifest.json').read_text())['source']['sha256']==hashlib.sha256((FIXTURE/'example.log').read_bytes()).hexdigest()
    assert main(args)==1
    assert (tmp_path/'review.recording.json').exists()
    assert (tmp_path/'review.engineering.json').exists()


def test_hash_mismatch_fails_before_decoding_or_writing(tmp_path):
    manifest=json.loads((Path(__file__).parents[1]/'data/manifests/synthetic_can.json').read_text())
    manifest['expected_hashes']['source']='0'*64
    config=tmp_path/'provenance.json';config.write_text(json.dumps(manifest))
    assert main(['investigate-can',str(FIXTURE/'example.log'),'--dbc',str(FIXTURE/'example.dbc'),
        '--provenance',str(config),'--time-basis','relative','--output-prefix',str(tmp_path/'report'),
        '--output-root',str(tmp_path)])==1
    assert not list(tmp_path.glob('report.*'))


def test_incomplete_provenance_is_clean_cli_error(tmp_path):
    config=tmp_path/'provenance.json';config.write_text('{"schema":"vcan-source-manifest-1"}')
    assert main(['investigate-can',str(FIXTURE/'example.log'),'--dbc',str(FIXTURE/'example.dbc'),
        '--provenance',str(config),'--time-basis','relative'])==1


def test_storage_audit_is_read_only_and_skips_symlinks(tmp_path):
    from can_lab.artifacts import audit_storage
    root=tmp_path/'outputs';root.mkdir()
    original=root/'historical.csv';original.write_bytes(b'important evidence')
    (root/'link').symlink_to(FIXTURE,target_is_directory=True)
    result=audit_storage(Path(__file__).parents[1],output_root=root)
    assert result['generated_bytes']==len(b'important evidence')
    assert result['generated_file_count']==1 and result['symlinks_skipped']==1
    assert original.read_bytes()==b'important evidence'
