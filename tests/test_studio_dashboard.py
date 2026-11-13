from pathlib import Path
from streamlit.testing.v1 import AppTest

DASHBOARD=Path(__file__).parents[1]/'src/can_lab/dashboard.py'


def app_page(page):
    app=AppTest.from_file(str(DASHBOARD)).run()
    app.button_group(key='workbench_page').set_value(page).run()
    assert not app.exception
    return app


def test_navigation_is_compact_not_radio_and_legacy_workflows_remain():
    app=app_page('Frame Laboratory')
    assert not any(item.key=='workbench_page' for item in app.radio)
    assert app.session_state['_studio_frame']['crc']==0x4cd
    app.checkbox(key='frame_advanced').check().run()
    assert not app.exception
    app.checkbox(key='frame_ack').uncheck().run()
    assert app.session_state['_studio_frame']['acknowledged'] is False
    app.text_input(key='frame_payload').set_value('11 22 33 44').run()
    assert app.session_state['_studio_frame']['dlc']==4  # DBC rejects shorter data, frame remains valid.
    app.selectbox(key='data_source').set_value('Raw CAN Investigation (v0.4 foundation)').run()
    assert not app.exception and app.checkbox(key='can_example')


def test_arbitration_stepping_reset_pause_and_invalid_ids():
    app=app_page('Virtual CAN Network')
    app.button_group(key='network_view').set_value('Arbitration').run()
    assert app.session_state['_arbitration']['winner']==0x120
    app.button(key='arbitration_play_step').click().run()
    assert app.session_state['arbitration_play'].index==1
    app.button(key='arbitration_play_previous').click().run()
    assert app.session_state['arbitration_play'].index==0
    app.button(key='arbitration_play_pause').click().run()
    assert not app.session_state['arbitration_play'].playing
    app.button(key='arbitration_play_reset').click().run()
    app.text_input(key='arb_id_1').set_value('0x120').run()
    assert not app.exception and any('Duplicate' in item.value for item in app.error)


def test_differential_noise_and_manual_controls():
    app=app_page('Learn CAN')
    app.button_group(key='learning_view').set_value('Differential signalling').run()
    app.checkbox(key='diff_noise').check().run()
    assert all(abs(row['Vdiff']-(0 if row['bit'] else 2))<1e-12 for row in app.session_state['_differential'])
    app.button(key='differential_play_step').click().run()
    assert app.session_state['differential_play'].index==1
    app.checkbox(key='differential_play_reduced').check().run()
    assert app.button(key='differential_play_start').disabled
    app.button(key='differential_play_reset').click().run()
    assert app.session_state['differential_play'].index==0
    app.text_input(key='diff_sequence').set_value('bad').run()
    assert app.error and not app.exception


def test_vehicle_event_inspection_tracks_playhead():
    app=app_page('Virtual CAN Network')
    first=app.session_state['_current_vehicle_play']
    assert first['index']==0 and len(first['receiving_nodes'])==4
    app.button(key='vehicle_play_step').click().run()
    second=app.session_state['_current_vehicle_play']
    assert second['index']==1 and second['payload_hex']==app.session_state['_vehicle_experiment']['events'][1]['payload_hex']
    app.button(key='vehicle_play_reset').click().run()
    assert app.session_state['_current_vehicle_play']['index']==0


def test_navigation_pauses_active_timer_state():
    app=app_page('Virtual CAN Network')
    app.button(key='vehicle_play_start').click().run()
    assert app.session_state['vehicle_play'].playing
    app.button_group(key='workbench_page').set_value('Overview').run()
    assert not app.session_state['vehicle_play'].playing
