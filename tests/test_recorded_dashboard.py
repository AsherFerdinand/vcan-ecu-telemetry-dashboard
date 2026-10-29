import io
from pathlib import Path
from unittest.mock import patch
from openpyxl import Workbook
from streamlit.testing.v1 import AppTest

DASHBOARD = Path(__file__).parents[1] / 'src/can_lab/dashboard.py'


class Upload(io.BytesIO):
    name = 'synthetic-ev.xlsx'


def make_upload(bad_time=False):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(['time', 'vhc_speed', 'hv_voltage', 'hv_current', 'bcell_soc', 'bcell_maxTemp', 'bcell_minTemp'])
    sheet.append([0, 0, 400, 20, 80, 26, 25])
    sheet.append([-1 if bad_time else 1, 3.6, 401, -10, 79, -40, 25])
    file = Upload()
    workbook.save(file)
    workbook.close()
    file.seek(0)
    return file


def app_real():
    app = AppTest.from_file(str(DASHBOARD)).run()
    app.selectbox(key='data_source').set_value('Real-World EV Dataset')
    return app


def set_time_unit(app):
    next(item for item in app.selectbox if item.label == 'Timestamp representation').set_value('s')
    return app


def test_real_view_without_workbook():
    app = app_real().run()
    assert not app.exception and not app.error
    assert any('No workbook required' in item.value for item in app.info)


def test_real_upload_units_power_quality_replay_and_exports():
    upload = make_upload()
    app = app_real()
    with patch('streamlit.file_uploader', side_effect=lambda *a, **kw: upload if kw.get('key') == 'ev_workbook' else None):
        app.run()
        set_time_unit(app)
        app.checkbox[0].set_value(True)
        app.run()
        assert not app.exception and not app.error
        result = app.session_state['_ev_recording']
        assert len(result.observations) == 2
        assert result.observations[0].derived['signed_power_kw']['value'] == 8
        assert result.observations[1].derived['signed_power_kw']['value'] == -4.01
        assert 'SUSPECT' in result.observations[1].statuses('cell_temperature_max_c')
        assert result.metadata['profile']['current_convention'] == 'unknown'
        app.button(key='ev_play').click().run()
        assert not app.exception
        app.button(key='ev_pause').click().run()
        assert not app.session_state['_ev_replay'].playing
        app.button(key='ev_reset').click().run()
        assert app.session_state['_ev_replay'].cursor == 0
        app.button(key='ev_prepare_exports').click().run()
        assert not app.exception and not app.error


def test_reversed_time_keeps_rows_and_blocks_replay():
    upload = make_upload(bad_time=True)
    app = app_real()
    with patch('streamlit.file_uploader', side_effect=lambda *a, **kw: upload if kw.get('key') == 'ev_workbook' else None):
        app.run()
        set_time_unit(app).run()
    assert not app.exception
    assert len(app.session_state['_ev_recording'].observations) == 2
    assert app.session_state['_ev_replay'] is None
    assert any('requires usable timestamps' in warning.value for warning in app.warning)


def test_invalid_profile_and_quality_config_show_errors():
    upload = make_upload()
    app = app_real()
    with patch('streamlit.file_uploader', side_effect=lambda *a, **kw: upload if kw.get('key') == 'ev_workbook' else None):
        app.run()
        app.text_area[0].set_value('{"flatline_min_samples": 0}').run()
    assert not app.exception
    assert any('flatline_min_samples' in error.value for error in app.error)


def test_virtual_source_can_generate_samples_without_upload():
    app = AppTest.from_file(str(DASHBOARD)).run()
    app.button(key='run_virtual_demo').click().run()
    assert not app.exception and not app.error
    assert len(app.dataframe[0].value) == 100
    assert any('Simulated:' in item.value for item in app.caption)
