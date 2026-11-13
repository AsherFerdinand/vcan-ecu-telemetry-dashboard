"""Independent byte expectations and bounded deterministic teaching scenarios."""
import copy
import pytest
from can_lab.workbench import (Node,EXAMPLE_ID,EXAMPLE_PAYLOAD,decode_teaching_frame,
                               signal_bits,teaching_database,network,fault_findings)
from can_lab.learning import QUESTIONS,FAQ,score_quiz


def test_kuksa_offline_example_and_changed_payload():
    result=decode_teaching_frame(EXAMPLE_ID,EXAMPLE_PAYLOAD,'DI_vehicleSpeed')
    assert result['raw_integer']==538 and result['physical']==pytest.approx(3.04)
    assert decode_teaching_frame('0X257',EXAMPLE_PAYLOAD,'DI_vehicleSpeed')['raw_integer']==538
    assert result['bits']==list(range(12,24)) and result['binary'][1]=='10101101'
    assert result['bytes']==[0x38,0xad,0x21,3,14,0,0,0]
    changed=decode_teaching_frame('257','38 BD 21 03 0E 00 00 00','DI_vehicleSpeed')
    assert changed['raw_integer']==539 and changed['physical']==pytest.approx(3.12)


def test_original_motorola_rpm_matches_original_protocol():
    result=decode_teaching_frame('100','0B B8 48 00 00 00 00 00','rpm')
    assert result['raw_integer']==3000 and result['physical']==3000
    assert result['bits']==list(range(7,-1,-1))+list(range(15,7,-1))
    assert decode_teaching_frame('100','0B B8 48 00 00 00 00 00','speed_kmh')['physical']==72


@pytest.mark.parametrize('payload,raw,physical',[('0FFF000000000000',-1,-10.5),('0123000000000000',291,135.5),('0800000000000000',-2048,-1034)])
def test_motorola_cross_byte_and_signed_interpretation(payload,raw,physical):
    result=decode_teaching_frame('300',payload,'SignedExample')
    assert result['bits']==[3,2,1,0,15,14,13,12,11,10,9,8]
    assert result['raw_integer']==raw and result['physical']==physical
    assert result['unsigned_integer']==raw & 0xfff


@pytest.mark.parametrize('identifier,payload,signal',[
    ('800',EXAMPLE_PAYLOAD,'DI_vehicleSpeed'),('garbage',EXAMPLE_PAYLOAD,'DI_vehicleSpeed'),
    ('257','GG00000000000000','DI_vehicleSpeed'),('257','123','DI_vehicleSpeed'),
    ('257','00','DI_vehicleSpeed'),('257','00'*9,'DI_vehicleSpeed'),
    ('257',EXAMPLE_PAYLOAD,'unknown'),('7ff',EXAMPLE_PAYLOAD,'DI_vehicleSpeed'),
    ('257','0x38 AD 21 03 0E 00 00 00','DI_vehicleSpeed')])
def test_invalid_frame_input(identifier,payload,signal):
    with pytest.raises(ValueError):decode_teaching_frame(identifier,payload,signal)


def test_deterministic_network_endpoint_and_simultaneous_releases():
    nodes=[Node('P',0x100,100),Node('B',0x200,200)]
    first=network(nodes,duration_ms=1000);second=network(nodes,duration_ms=1000)
    assert first==second and first['counts']=={'P':11,'B':6}
    assert [(row['frame_id'],row['timestamp_ms']) for row in first['events'][:2]]==[(0x100,0),(0x200,0)]
    assert first['events'][0]['speed_kmh']==65
    assert first['events'][0]['payload_hex']=='09C4410000000000'
    assert [event['interval_ms'] for event in first['events'] if event['node']=='B']==[None]+[200]*5
    assert 'no bit-level arbitration' in first['assumptions']


def test_disabled_stopped_nodes_and_payload_override():
    result=network([Node('Off',0x100,100,False),Node('Stopped',0x200,100,stop_ms=300),
                    Node('Custom',0x300,200,payload_hex='ABCD')],duration_ms=1000)
    assert result['counts']=={'Off':0,'Stopped':3,'Custom':6}
    assert all(row['timestamp_ms']<300 for row in result['events'] if row['node']=='Stopped')
    assert {row['payload_hex'] for row in result['events'] if row['node']=='Custom'}=={'ABCD'}


@pytest.mark.parametrize('nodes,kwargs',[
    ([Node('x',0x100,0)],{}),([Node('x',0x800,100)],{}),
    ([Node('x',0x100,100),Node('y',0x100,100)],{}),([Node('x',0x100,100)],{'duration_ms':20000}),
    ([Node('x',0x100,100)],{'jitter_ms':100,'jitter_node':'x'}),
    ([Node('x',0x100,100,payload_hex='XYZ')],{}),
    ([Node('x',0x200,100)],{'jump_node':'x'}),([Node('x',0x100,100)],{'jitter_node':'absent'})])
def test_invalid_network_configuration(nodes,kwargs):
    with pytest.raises(ValueError):network(nodes,**kwargs)


def test_frame_budget_bounds_and_zero_arrivals():
    result=network([Node(str(i),i+1,10) for i in range(4)],duration_ms=10000)
    assert len(result['events'])==4004
    none=network([Node('P',0x100,100,stop_ms=0)],duration_ms=1000)
    findings=fault_findings(none)
    assert findings[0]['last_received_ms'] is None and findings[0]['interval_ms']==1000
    assert findings[0]['evidence_indices']==[]


def test_missing_message_evidence_and_unchanged_inputs():
    result=network([Node('P',0x100,100,stop_ms=500)],duration_ms=1000)
    before=copy.deepcopy(result)
    findings=fault_findings(result,missing_factor=2.5)
    missing=next(item for item in findings if item['kind']=='missing_message')
    assert missing['last_received_ms']==400 and missing['interval_ms']==600
    assert missing['threshold_ms']==250 and missing['evidence_indices']==[4]
    assert result==before


def test_controlled_jitter_and_strict_timing_threshold():
    result=network([Node('P',0x100,100)],duration_ms=500,jitter_ms=30,jitter_node='P')
    assert [event['timestamp_ms'] for event in result['events']]==[0,130,200,330,400]
    at_threshold=fault_findings(result,timing_tolerance_ms=30)
    assert not any(row['exceeded'] for row in at_threshold if row['kind']=='timing')
    beyond=fault_findings(result,timing_tolerance_ms=29)
    assert all(row['exceeded'] for row in beyond if row['kind']=='timing')


def test_injected_signal_step_and_threshold_rate():
    result=network([Node('P',0x100,100)],duration_ms=1000,jump_node='P',jump_at_ms=500,jump_kmh=60)
    findings=fault_findings(result,rate_threshold_kmh_s=100)
    flagged=[row for row in findings if row['kind']=='signal_rate' and row['exceeded']]
    assert len(flagged)==1
    item=flagged[0];a,b=(result['events'][i] for i in item['evidence_indices'])
    assert b['timestamp_ms']==500 and item['interval_ms']==100
    assert item['rate_kmh_s']==(b['speed_kmh']-a['speed_kmh'])/.1


@pytest.mark.parametrize('threshold',[0,-1,float('nan'),True])
def test_invalid_fault_thresholds(threshold):
    with pytest.raises(ValueError):fault_findings(network([Node('x',0x100,100)]),missing_factor=threshold)


@pytest.mark.parametrize('level',['Beginner','Intermediate'])
def test_quiz_scoring_and_unanswered_feedback(level):
    questions=[question for question in QUESTIONS if question['level']==level]
    correct={question['id']:question['correct'] for question in questions}
    result=score_quiz(level,correct)
    assert result['score']==result['total']==4
    assert score_quiz(level,{})['score']==0
    assert all(not row['answered'] for row in score_quiz(level,{})['feedback'])
    assert len(FAQ)==20


@pytest.mark.parametrize('level,answers',[('unknown',{}),('Beginner',{'broadcast':True}),('Beginner',{'broadcast':9}),('Beginner',{'missing':0})])
def test_quiz_rejects_invalid_answers(level,answers):
    with pytest.raises(ValueError):score_quiz(level,answers)


def test_release_phases_change_actual_schedule():
    result=network([Node('P',0x100,100),Node('B',0x200,100,phase_ms=30)],duration_ms=300)
    assert [row['timestamp_ms'] for row in result['events'] if row['node']=='B']==[30,130,230]
    assert result['counts']=={'P':4,'B':3}
