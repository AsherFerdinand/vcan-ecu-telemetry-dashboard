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


def test_independent_metrics_and_row_fallback_are_explicit():
    upload = make_upload()
    app = app_real()
    with patch('streamlit.file_uploader', side_effect=lambda *a, **kw: upload if kw.get('key') == 'ev_workbook' else None):
        app.run()
    assert not app.exception and not app.error
    metrics = {item.label: item.value for item in app.metric}
    assert metrics['Imported observations'] == '2'
    assert metrics['Metadata-unverified observations'] == '2'
    assert metrics['Timestamp-invalid observations'] == '0'
    assert metrics['Physically suspicious observations'] == '1'  # raw -40 candidate
    assert any('UNVERIFIED TIME' in item.value for item in app.warning)
    slider = next(s for s in app.slider if s.label.startswith('Worksheet row interval'))
    assert slider.value == (2, 3)


def test_explicit_inferred_source_profile_and_shared_zoom():
    workbook = Workbook(); sheet = workbook.active
    sheet.append(['time','vhc_speed','hv_voltage','hv_current','bcell_soc','bcell_maxTemp','bcell_minTemp'])
    for timestamp in [401042949,401042959,401043009,401043019]:
        sheet.append([timestamp, 30,350,-10,80,26,25])
    upload = Upload(); workbook.save(upload); workbook.close(); upload.seek(0)
    app = app_real()
    with patch('streamlit.file_uploader', side_effect=lambda *a, **kw: upload if kw.get('key') == 'ev_workbook' else None):
        app.run()
        next(c for c in app.checkbox if c.label.startswith('Use source-reviewed')).set_value(True)
        app.run()
        assert not app.exception and not app.error
        assert app.session_state['_ev_recording'].duration_s() == 30
        assert app.session_state['_ev_quality_summary']['dimensions']['timestamp_invalid_observations'] == 0
        slider = next(s for s in app.slider if s.label.startswith('Recording seconds interval'))
        slider.set_value((10.0,20.0)).run()
        assert not app.exception
        assert app.session_state['_ev_plot_indices'] == [1,2]
        assert app.session_state['_ev_plot_cache'][('speed_kmh',False)]['domain'] == [10,20]
        assert app.session_state['_ev_plot_cache'][('battery_voltage_v',False)]['domain'] == [10,20]


def test_engineering_workspace_reports_and_threshold_updates():
    upload=make_upload()
    app=app_real()
    with patch('streamlit.file_uploader',side_effect=lambda *a,**kw: upload if kw.get('key')=='ev_workbook' else None):
        app.run()
        set_time_unit(app)
        app.checkbox[0].set_value(True)
        app.run()
        assert not app.exception and not app.error
        assert any(tab.label=='Battery Health Indicators' for tab in app.tabs)
        assert any(tab.label=='Session Explorer' for tab in app.tabs)
        assert any(tab.label=='Diagnostics' for tab in app.tabs)
        analysis=app.session_state['_ev_engineering']
        assert len(analysis.sessions)==1 and analysis.energy['included_intervals']==1
        assert analysis.cells[0].voltage_spread_v is None  # this small workbook lacks cell voltages
        app.button(key='prepare_engineering_reports').click().run()
        assert not app.exception and not app.error
        next(t for t in app.text_area if t.label.startswith('Engineering thresholds')).set_value('{"energy":{"max_interval_s":0.5}}').run()
        assert not app.exception
        assert app.session_state['_ev_engineering'].energy['included_intervals']==0
        app.button(key='ev_play').click().run()
        assert any(m.label=='Current operating candidates' for m in app.metric)
        assert any(m.label=='Current signed power' for m in app.metric)


def test_invalid_engineering_thresholds_are_user_visible():
    upload=make_upload();app=app_real()
    with patch('streamlit.file_uploader',side_effect=lambda *a,**kw: upload if kw.get('key')=='ev_workbook' else None):
        app.run()
        next(t for t in app.text_area if t.label.startswith('Engineering thresholds')).set_value('{"operating":{"smoothing_samples":2}}').run()
    assert not app.exception
    assert any('smoothing_samples' in e.value for e in app.error)
