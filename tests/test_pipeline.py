"""Shared workbook preparation retains the established CLI/UI contract."""
import hashlib
import io
import subprocess
import sys
import pytest
from openpyxl import Workbook
from can_lab.pipeline import prepare_workbook
from can_lab.recording import DatasetProfile
from can_lab.quality import QualityConfig, quality_summary


def source():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Synthetic'
    sheet.append(['time', 'hv_voltage', 'hv_current', 'vhc_speed'])
    sheet.append([0, 400, 25, 36])
    sheet.append([10, 398, -20, 37])
    stream = io.BytesIO()
    workbook.save(stream)
    workbook.close()
    stream.seek(0)
    return stream


def test_preparation_preserves_raw_source_and_calculates_measured_sign_power():
    stream = source()
    original = stream.getvalue()
    stream.seek(7)
    profile = DatasetProfile(dataset_id='synthetic-pipeline-test', time_unit='s',
                             units={'hv_voltage': 'V', 'hv_current': 'A', 'vhc_speed': 'km/h'})
    recording = prepare_workbook(stream, profile=profile,
                                 quality_config=QualityConfig(expected_interval_s=10),
                                 sheet='Synthetic', filename='synthetic.xlsx')
    assert stream.tell() == 7 and stream.getvalue() == original
    assert recording.metadata['sha256'] == hashlib.sha256(original).hexdigest()
    assert recording.metadata['profile']['dataset_id'] == 'synthetic-pipeline-test'
    assert [row.timestamp_s for row in recording.observations] == [0, 10]
    assert [row.raw['hv_current'] for row in recording.observations] == [25, -20]
    assert recording.observations[0].derived['signed_power_kw']['value'] == 10
    assert recording.observations[1].derived['signed_power_kw']['value'] == pytest.approx(-7.96)
    assert any(issue['reason'] == 'current_polarity_unverified'
               for issue in recording.observations[0].derived['signed_power_kw']['quality'])
    assert quality_summary(recording)['dimensions']['timestamp_invalid_observations'] == 0


def test_default_preparation_does_not_infer_units_or_numeric_time():
    recording = prepare_workbook(source())
    assert recording.observations[0].timestamp_s is None
    assert recording.observations[0].values['battery_voltage_v'] is None
    assert recording.observations[0].derived['signed_power_kw']['value'] is None
    dimensions = quality_summary(recording)['dimensions']
    assert dimensions['timestamp_unverified_observations'] == 2
    assert dimensions['metadata_unverified_observations'] == 2
    assert dimensions['physically_suspicious_observations'] == 0


def test_preparation_forwards_selection_and_explicit_limits():
    with pytest.raises(ValueError, match='unknown worksheet'):
        prepare_workbook(source(), sheet='not-present')
    with pytest.raises(ValueError, match='max_rows'):
        prepare_workbook(source(), max_rows=1)


def test_pipeline_import_does_not_activate_excel_ui_or_can_dependencies():
    code = '''
import importlib.abc,sys
class BlockExternal(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('can','cantools','pandas','openpyxl','streamlit'):
            raise ImportError('external dependency intentionally unavailable')
sys.meta_path.insert(0,BlockExternal())
from can_lab.pipeline import prepare_workbook
assert callable(prepare_workbook)
'''
    subprocess.run([sys.executable, '-c', code], check=True)
