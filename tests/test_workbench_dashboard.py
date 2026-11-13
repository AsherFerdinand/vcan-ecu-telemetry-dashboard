from pathlib import Path
from streamlit.testing.v1 import AppTest
from can_lab.learning import QUESTIONS

DASHBOARD=Path(__file__).parents[1]/'src/can_lab/dashboard.py'


def workspace(page):
    app=AppTest.from_file(str(DASHBOARD)).run()
    app.button_group(key='workbench_page').set_value(page).run()
    assert not app.exception
    if page=='Virtual CAN Network':app.button_group(key='network_view').set_value('Release experiment').run()
    return app


def test_overview_and_card_navigation():
    app=AppTest.from_file(str(DASHBOARD)).run()
    assert not app.exception
    assert app.button_group(key='workbench_page').value=='Overview'
    assert len([button for button in app.button if button.label.startswith('Open ')])==6
    app.button(key='open_Frame LaboratoryNone').click().run()
    assert not app.exception and app.session_state['_frame_result']['raw_integer']==538


def test_frame_live_recalculation_invalid_edit_and_reset():
    app=workspace('Frame Laboratory')
    assert app.session_state['_frame_result']['physical']>3
    app.text_input(key='frame_payload').set_value('38 BD 21 03 0E 00 00 00').run()
    assert app.session_state['_frame_result']['raw_integer']==539
    app.text_input(key='frame_payload').set_value('ZZ').run()
    assert not app.exception and app.error
    assert '_frame_result' not in app.session_state
    app.button(key='frame_reset').click().run()
    assert not app.exception and not app.error
    assert app.session_state['_frame_result']['raw_integer']==538


def test_motorola_lab_and_contextual_learning():
    app=workspace('Frame Laboratory')
    app.text_input(key='frame_id').set_value('0x300').run()
    assert not app.exception
    assert app.session_state['_frame_result']['bits']==[3,2,1,0,15,14,13,12,11,10,9,8]
    app.button(key='frame_learn').click().run()
    assert not app.exception and app.button_group(key='workbench_page').value=='Learn CAN'
    assert len(app.expander)>=20


def test_network_runs_and_reports_configuration_error():
    app=workspace('Virtual CAN Network')
    app.button(key='network_run').click().run()
    assert not app.exception and not app.error
    assert app.session_state['_network_result']['counts']['Powertrain ECU']==16
    app.text_input(key='node_id_1').set_value('0x100')
    app.button(key='network_run').click().run()
    assert not app.exception and any('distinct message IDs' in error.value for error in app.error)
    assert '_network_result' not in app.session_state


def test_all_fault_scenarios_show_evidence():
    app=workspace('Fault Investigation')
    for scenario in ['Missing message','Timing irregularity','Signal discontinuity']:
        app.selectbox(key='fault_scenario').set_value(scenario)
        app.button(key='fault_run').click().run()
        assert not app.exception and not app.error
        result,evidence,stored=app.session_state['_fault_result']
        assert stored==scenario and any(item['exceeded'] for item in evidence)
        assert all(index<len(result['events']) for finding in evidence for index in finding['evidence_indices'])


def test_quiz_submit_retry_and_level_change():
    app=workspace('Learn CAN')
    for question in QUESTIONS:
        if question['level']=='Beginner':
            app.radio(key='quiz_answer_'+question['id']).set_value(question['choices'][question['correct']])
    app.button(key='quiz_submit').click().run()
    assert not app.exception and app.session_state['_quiz_result']['score']==4
    app.button(key='quiz_retry').click().run()
    assert '_quiz_result' not in app.session_state
    assert app.radio(key='quiz_answer_broadcast').value is None
    app.selectbox(key='quiz_level').set_value('Intermediate').run()
    assert not app.exception and app.radio(key='quiz_answer_scale').value is None


def test_network_presets_change_periods_and_phases():
    app=workspace('Virtual CAN Network')
    app.selectbox(key='network_scenario').set_value('Simultaneous releases').run()
    app.button(key='network_run').click().run()
    result=app.session_state['_network_result']
    assert [row['timestamp_ms'] for row in result['events'][:4]]==[0,0,0,0]
    assert all(node['period_ms']==100 for node in result['nodes'])
    app.selectbox(key='network_scenario').set_value('Different message periods').run()
    app.button(key='network_run').click().run()
    assert [node['period_ms'] for node in app.session_state['_network_result']['nodes']]==[100,170,260,430]


def test_changed_quiz_answer_clears_stale_feedback():
    app=workspace('Learn CAN')
    app.button(key='quiz_submit').click().run()
    assert '_quiz_result' in app.session_state
    app.radio(key='quiz_answer_broadcast').set_value('All connected receiving nodes').run()
    assert '_quiz_result' not in app.session_state


def test_network_inspector_clamps_after_shorter_run():
    app=workspace('Virtual CAN Network')
    app.button(key='network_run').click().run()
    last=len(app.session_state['_network_result']['events'])-1
    app.number_input(key='network_event').set_value(last).run()
    app.number_input(key='network_duration').set_value(100)
    app.button(key='network_run').click().run()
    assert not app.exception and not app.error
    assert app.number_input(key='network_event').value==0
