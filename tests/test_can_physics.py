import pytest
from can_lab.can_physics import classical_frame,crc15,stuff_bits,bits,arbitrate,differential
from can_lab.studio_playback import Playhead,vehicle_experiment,inspect_event
from can_lab.studio_diagrams import topology_html,frame_html
from can_lab.artifacts import format_size,display_sizes


def test_crc15_can_published_check_value():
    # CRC-15/CAN catalogue check: ASCII 123456789, init/xorout zero, no reflection.
    assert crc15([bit for byte in b'123456789' for bit in bits(byte,8)])==0x059e


@pytest.mark.parametrize('identifier,payload,expected',[(0,b'',0),(0x123,bytes.fromhex('11223344'),0x11da),(0x257,bytes.fromhex('38AD21030E000000'),0x04cd)])
def test_frame_crc_polynomial_long_division_vectors(identifier,payload,expected):
    frame=classical_frame(identifier,payload)
    assert frame['crc']==expected
    # Independent polynomial remainder, dividend multiplied by x^15.
    dividend=int(''.join(map(str,frame['crc_input']))+'0'*15,2)
    while dividend.bit_length()>15:dividend^=0xc599<<(dividend.bit_length()-16)
    assert dividend==expected
    assert crc15(frame['crc_input']+bits(expected,15))==0


def test_frame_fields_lengths_and_intermission_boundary():
    frame=classical_frame(0x257,bytes.fromhex('38AD21030E000000'))
    assert [field['length'] for field in frame['fields']]==[1,11,1,1,1,4,64,15,1,1,1,7,3]
    assert frame['fields'][1]['bits']==[int(bit) for bit in '01001010111']
    assert len(frame['unstuffed_frame_bits'])==108
    assert frame['fields'][-1]['inside_frame'] is False
    assert len(frame['transmitted_with_intermission'])==111+frame['stuff_count']
    assert frame['ack_transmitter_bit']==1 and frame['fields'][9]['bits']==[0]
    assert classical_frame(0,b'',acknowledged=False)['fields'][9]['bits']==[1]
    assert 'AFTER FRAME' in frame_html(frame,'Identifier')


@pytest.mark.parametrize('identifier,payload,dlc',[(0x800,b'',0),(-1,b'',0),(True,b'',0),(0,b'123456789',9),(0,b'1',0),(0,b'',True),(0,b'',15)])
def test_unsupported_frame_configuration(identifier,payload,dlc):
    with pytest.raises(ValueError):classical_frame(identifier,payload,dlc=dlc)


@pytest.mark.parametrize('original,expected',[
    ([0]*5,[0,0,0,0,0,1]),([1]*5,[1,1,1,1,1,0]),
    ([0]*5+[1]*4,[0,0,0,0,0,1,1,1,1,1,0]),([0,1]*4,[0,1]*4)])
def test_stuffing_complement_and_inserted_bit_run_participation(original,expected):
    stuffed=stuff_bits(original)
    assert [item['bit'] for item in stuffed]==expected
    assert [item['bit'] for item in stuffed if not item['stuffed']]==original
    assert all(item['source_index'] is None for item in stuffed if item['stuffed'])


def test_arbitration_independently_specified_loss_bits():
    result=arbitrate([0x120,0x124,0x3e0])
    assert result['winner']==0x120
    assert result['steps'][1]['identifier_bit']==9 and result['steps'][1]['lost']==[2]
    assert result['steps'][8]['identifier_bit']==2 and result['steps'][8]['lost']==[1]
    assert all(step['bus']==min(step['sent'].values()) for step in result['steps'])
    assert 2 not in result['steps'][2]['sent']
    assert arbitrate([0x7ff,0])['winner']==0


@pytest.mark.parametrize('values',[[1,1],[0x800,1],[1],[1,2,3,4,5],[True,2]])
def test_unsupported_arbitration(values):
    with pytest.raises(ValueError):arbitrate(values)


@pytest.mark.parametrize('amplitude',[0,.5,1])
def test_differential_levels_and_ideal_cancellation(amplitude):
    rows=differential('10',amplitude=amplitude)
    assert rows[0]['CAN_H_original']==rows[0]['CAN_L_original']==2.5
    assert rows[1]['CAN_H_original']==3.5 and rows[1]['CAN_L_original']==1.5
    assert rows[0]['Vdiff']==pytest.approx(0) and rows[1]['Vdiff']==pytest.approx(2)
    assert rows[1]['CAN_H']-rows[1]['CAN_H_original']==pytest.approx(rows[1]['CAN_L']-rows[1]['CAN_L_original'])


@pytest.mark.parametrize('sequence,amplitude',[('',0),('2',0),('0'*129,0),('01',-1),('01',float('nan'))])
def test_invalid_signalling(sequence,amplitude):
    with pytest.raises(ValueError):differential(sequence,amplitude=amplitude)


def test_bounded_playhead_and_pause_reset():
    head=Playhead(3);head.tick();assert head.index==0
    head.playing=True;head.tick();assert head.index==1
    head.move(-1);assert head.index==0 and not head.playing
    head.move(100);assert head.index==2
    head.playing=True;head.tick();assert not head.playing
    head.reset();assert head.index==0
    with pytest.raises(ValueError):Playhead(4005)


def test_real_event_drives_topology_and_inspector():
    experiment=vehicle_experiment();event=inspect_event(experiment,0)
    assert event['payload_hex']==experiment['events'][0]['payload_hex']
    assert event['decoded']['speed_kmh']==65 and event['dlc']==8
    assert event['node'] not in event['receiving_nodes'] and 'Brake ECU' in event['receiving_nodes']
    assert len(event['receiving_nodes'])==4
    markup=topology_html(experiment,event,playing=True)
    assert event['payload_hex'] in markup and '120 Ω' in markup and 'prefers-reduced-motion' in markup
    assert 'data-node="BUS"' in markup
    with pytest.raises(ValueError):inspect_event(experiment,len(experiment['events']))


@pytest.mark.parametrize('value,expected',[(758601,'758.60 KB'),(9530318,'9.53 MB'),(462707,'462.71 KB'),(1000000000,'1.00 GB'),(0,'0.00 KB')])
def test_decimal_display_and_internal_preservation(value,expected):
    assert format_size(value)==expected
    original={'bytes':value,'limits':{'max_source_bytes':value}}
    shown=display_sizes(original)
    assert shown['size']==expected and shown['limits']['max_source_size']==expected
    assert original['bytes']==value
