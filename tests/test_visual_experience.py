import copy
import re
import pytest
from can_lab.visual_model import visual_event,fault_visual
from can_lab.studio_playback import vehicle_experiment,inspect_event
from can_lab.studio_diagrams import topology_html
from can_lab.workbench import Node,network,fault_findings
from can_lab.workbench_style import overview_icon,appearance_style


def test_visual_nodes_are_passive_without_expanding_publishers():
    experiment=vehicle_experiment();before=copy.deepcopy(experiment)
    event=inspect_event(experiment,0);view=visual_event(experiment,event)
    assert len(experiment['nodes'])==4 and len(view['nodes'])==6
    assert sum(node['publisher'] for node in view['nodes'])==4
    assert all(not node['publisher'] for node in view['nodes'][4:])
    assert view['nodes'][4]['label']=='ABS / ESC'
    assert len(view['receivers'])==5 and view['transmitter'] not in view['receivers']
    assert experiment==before


def test_event_mapping_follows_every_original_transmitter():
    experiment=vehicle_experiment()
    for index in range(4):
        event=inspect_event(experiment,index);view=visual_event(experiment,event)
        node=next(node for node in view['nodes'] if node['key']==view['transmitter'])
        assert node['name']==event['node']
        assert view['event_index']==event['index']


def test_fabricated_events_cannot_drive_motion():
    experiment=vehicle_experiment();event=inspect_event(experiment,0)
    event['payload_hex']='FF'*8
    with pytest.raises(ValueError,match='unchanged'):visual_event(experiment,event)


def test_animation_reuses_the_exact_rendered_wire_paths_and_no_random_messages():
    experiment=vehicle_experiment();event=inspect_event(experiment,0)
    view=visual_event(experiment,event)
    markup=topology_html(experiment,event,playing=True)
    for wire in view['paths'][view['transmitter']].values():
        assert f'd="{wire}"' in markup and f'path="{wire}"' in markup
    for key in view['receivers']:
        assert f'path="{view["paths"][key]["H"]}"' in markup
    assert 'keyPoints="1;0"' in markup
    assert event['payload_hex'] in markup and f'EVENT {event["index"]}' in markup
    assert markup.count('120 Ω')==2
    assert all(f'data-node="{sensor}"' in markup for sensor in ['FL','FR','RL','RR','CRASH_L','CRASH_R'])
    assert 'Crash' in markup and 'ABS / ESC' in markup


def test_pause_reduced_motion_and_event_change_reset_animation():
    experiment=vehicle_experiment();event=inspect_event(experiment,0)
    for options in ({'playing':False},{'playing':True,'reduced':True}):
        assert '<animateMotion' not in topology_html(experiment,event,**options)
    running=topology_html(experiment,event,playing=True,pulse_period=2)
    assert '<animateMotion' in running and 'prefers-reduced-motion' in running
    changed=topology_html(experiment,inspect_event(experiment,1),playing=True)
    assert running!=changed and 'EVENT 1' in changed
    assert 'begin="0.000s"' in changed


def test_explicit_fault_mapping_and_missing_release_evidence():
    experiment=network([Node('Powertrain ECU',0x100,100,stop_ms=500)],duration_ms=1000)
    finding=next(row for row in fault_findings(experiment) if row['kind']=='missing_message')
    before=copy.deepcopy(finding);view=fault_visual(experiment,finding)
    assert view['mapped'] and view['label']=='Expected release not observed'
    assert view['evidence_indices']==finding['evidence_indices'] and finding==before
    unknown=network([Node('Unrelated ECU',0x100,100)],duration_ms=1000)
    assert not fault_visual(unknown,{**finding,'node':'Unrelated ECU'})['mapped']


def test_themes_and_six_distinct_inline_icons():
    assert '#0b1220' in appearance_style('dark')
    assert '#f5f7fa' in appearance_style('light')
    assert len({overview_icon(index) for index in range(6)})==6
    experiment=vehicle_experiment();event=inspect_event(experiment,0)
    assert '#0b1220' in topology_html(experiment,event,theme='dark')
    assert '#f5f7fa' in topology_html(experiment,event,theme='light')


def test_changed_identifier_is_not_an_original_visual_event():
    experiment=vehicle_experiment();event=inspect_event(experiment,0)
    event['frame_id']=0x777
    with pytest.raises(ValueError,match='unchanged'):visual_event(experiment,event)


def test_fault_highlight_uses_original_evidence_not_a_missing_frame():
    experiment=network([Node('Powertrain ECU',0x100,100,stop_ms=500)],duration_ms=1000)
    finding=next(row for row in fault_findings(experiment) if row['kind']=='missing_message')
    visual=fault_visual(experiment,finding)
    event=inspect_event(experiment,visual['evidence_indices'][-1])
    markup=topology_html(experiment,event,fault=visual)
    assert 'THRESHOLD EVIDENCE' in markup and event['payload_hex'] in markup
    assert event['timestamp_ms']==400 and '<animateMotion' not in markup
