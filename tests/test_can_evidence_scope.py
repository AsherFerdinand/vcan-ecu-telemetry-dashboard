"""Authored DBC examples only: no capture download or third-party data required."""
import io
import json
from pathlib import Path
import pytest
from can_lab.can_recording import CANConfig, investigate_candump, check_references
from can_lab.codec import load_classical_dbc
from can_lab.can_reports import build_can_report
from can_lab.cli import main

FIXTURE=Path(__file__).parent/'fixtures/raw_can'
MUX='''
BO_ 512 OtherMux: 8 X
 SG_ Mode M : 0|4@1+ (1,0) [0|15] "" X
 SG_ Value m1 : 8|8@1+ (1,0) [0|255] "" X
'''


def test_explicit_dbc_scope_preserves_definitions_and_rejects_selected_mux():
    text=(FIXTURE/'example.dbc').read_text()+MUX
    with pytest.raises(ValueError,match='multiplexed'):load_classical_dbc(text)
    db=load_classical_dbc(text,frame_ids=[0x120,0x121])
    assert [m.frame_id for m in db.messages]==[0x120,0x121]
    assert db.get_message_by_frame_id(0x120).get_signal_by_name('EngineSpeed').start==23
    with pytest.raises(ValueError,match='multiplexed'):load_classical_dbc(text,frame_ids=[0x200])


@pytest.mark.parametrize('ids',[[],[True],[0x800],[0x120,0x120],[-1],['0x120']])
def test_invalid_selected_frame_ids(ids):
    with pytest.raises(ValueError):CANConfig(dbc_frame_ids=ids)
    with pytest.raises(ValueError):load_classical_dbc((FIXTURE/'example.dbc').read_text(),frame_ids=ids)


def test_missing_dbc_selection_fails_cleanly():
    with pytest.raises(ValueError,match='absent'):load_classical_dbc((FIXTURE/'example.dbc').read_text(),frame_ids=[0x122])


def test_scope_is_recorded_and_unselected_frames_are_explicit_unknowns():
    result=investigate_candump(FIXTURE/'example.log',FIXTURE/'example.dbc',config=CANConfig(dbc_frame_ids=[0x120]))
    assert set(result.definitions)=={'288'}
    assert result.coverage['unknown_id_frames']==2
    assert result.configuration['dbc_frame_ids']==(0x120,)
    assert result.recording.metadata['can_dbc_scope']['selected_frame_ids']==[0x120]
    assert result.dbc['bytes']==(FIXTURE/'example.dbc').stat().st_size


def test_declared_kph_alias_preserves_dbc_and_source_unit():
    text=(FIXTURE/'example.dbc').read_text().replace('"km/h"','"kph"')
    result=investigate_candump(FIXTURE/'example.log',io.BytesIO(text.encode()),
        mapping=[{'frame_id':0x120,'signal':'VehicleSpeed','target':'speed_kmh'}])
    assert result.recording.observations[0].values['speed_kmh']==72.3
    signal=result.recording.metadata['signals']['speed_kmh']
    assert signal['source_unit']=='kph' and signal['canonical_unit']=='km/h'
    assert result.definitions['288']['signals']['VehicleSpeed']['unit']=='kph'


def test_documented_vectors_are_not_physical_accuracy_evidence():
    result=investigate_candump(FIXTURE/'example.log',FIXTURE/'example.dbc')
    references=json.loads((FIXTURE/'references.json').read_text())
    references['evidence_kind']='documented_dbc_vectors'
    checked=check_references(result,references)
    assert checked['passed']==5 and checked['physical_accuracy']=='not_established'
    report=build_can_report(result)
    assert report['signal_summary']['0x120/VehicleSpeed']=={'count':3,'min':0.0,'max':100.0,'unit':'km/h'}
    assert report['signal_summary']['0x121/PackCurrent']['min']==-25
    assert report==build_can_report(result)


def test_cli_dbc_scope_is_reproduced_in_manifest(tmp_path):
    prefix=tmp_path/'scoped'
    assert main(['investigate-can',str(FIXTURE/'example.log'),'--dbc',str(FIXTURE/'example.dbc'),
        '--time-basis','relative','--dbc-frame-id','0x120','--output-root',str(tmp_path),'--output-prefix',str(prefix)])==0
    manifest=json.loads((tmp_path/'scoped.manifest.json').read_text())
    assert manifest['processing_configuration']['dbc_frame_ids']==[0x120]
    command=manifest['reproduction']['command'];index=command.index('--dbc-frame-id')
    assert command[index+1]=='0x120'


def test_existing_config_positional_time_basis_contract():
    config=CANConfig(10,1,4096,100000,'can0',None,None,'unix')
    assert config.time_basis=='unix' and config.dbc_frame_ids is None
