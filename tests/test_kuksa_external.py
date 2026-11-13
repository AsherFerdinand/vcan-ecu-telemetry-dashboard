"""Explicit optional integration, never a download or ordinary CI requirement."""
import importlib.util
import json
import os
from pathlib import Path
import pytest


@pytest.mark.skipif(not os.environ.get('VCAN_KUKSA_DIR'),reason='optional hash-pinned external KUKSA inputs not configured')
def test_real_source_investigation_and_provenance(tmp_path):
    script=Path(__file__).parents[1]/'examples/investigate_kuksa.py'
    spec=importlib.util.spec_from_file_location('kuksa_example',script)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    result,summary=module.investigate(Path(os.environ['VCAN_KUKSA_DIR']),tmp_path/'investigation',tmp_path)
    assert result.coverage['decoded_frames']==10000 and result.coverage['limit_reached']
    assert len(result.frames)==10000 and result.validation['passed']==3
    assert summary['signals']['0x257/DI_vehicleSpeed']['count']==1994
    assert summary['signals']['0x257/DI_vehicleSpeed']['min']==pytest.approx(-6.56)
    assert summary['signals']['0x266/RearPower266']['max']==4.5
    assert summary['engineering']['energy']['included_intervals']==0
    obs=next(row for row in result.recording.observations if row.row_number==9997)
    assert obs.raw['frame_ref']==9996 and obs.values['speed_kmh']==pytest.approx(3.04)
    frame=result.frames[9996].frame
    with (Path(os.environ['VCAN_KUKSA_DIR'])/'candump.log').open('rb') as raw:
        raw.seek(frame.byte_offset)
        assert raw.readline().split()[2].split(b'#')[1].strip().decode()==frame.payload_hex
    manifest=json.loads((tmp_path/'investigation.manifest.json').read_text())
    assert manifest['source']['sha256']==result.source['sha256']
    assert manifest['reference_configuration']['evidence_kind']=='documented_dbc_vectors'
    assert str(tmp_path) not in json.dumps(manifest)
    with pytest.raises(ValueError,match='overwrite'):
        module.investigate(Path(os.environ['VCAN_KUKSA_DIR']),tmp_path/'investigation',tmp_path)
