"""Bounded teaching experiments over existing cantools and python-can primitives.

No wall-clock waits, production detector, arbitration timing model or source edits.
"""
from dataclasses import asdict, dataclass
from importlib.resources import files
import math
import re
from uuid import uuid4
import can
from .codec import SyntheticCodec, load_classical_dbc
from .simulator import frames

EXAMPLE_ID='0x257'
EXAMPLE_PAYLOAD='38 AD 21 03 0E 00 00 00'


def teaching_database():
    db=load_classical_dbc(files('can_lab').joinpath('data/education.dbc').read_text())
    # Original synthetic message objects and their verified bit definitions.
    db.messages.extend(SyntheticCodec().database.messages)
    db.refresh()
    return db


def signal_bits(signal):
    """DBC bit numbers in signal significance order (Intel LSB, Motorola MSB).

    Motorola uses sawtooth numbering: after bit 0 comes bit 15, not bit -1.
    This visual traversal never replaces the cantools decoder.
    """
    bit=signal.start;result=[]
    for _ in range(signal.length):
        result.append(bit)
        bit=bit+1 if signal.byte_order=='little_endian' else bit+15 if bit%8==0 else bit-1
    return result


def decode_teaching_frame(identifier, payload, signal_name):
    if not isinstance(identifier,str) or not re.fullmatch(r'(?:0[xX])?[0-9a-fA-F]{1,3}',identifier.strip()):
        raise ValueError('Enter a standard hexadecimal ID, e.g. 0x257')
    frame_id=int(identifier.strip(),16)
    if frame_id>0x7ff:raise ValueError('Classical teaching examples use standard 11-bit IDs (0x000–0x7FF)')
    if not isinstance(payload,str) or not re.fullmatch(r'[0-9a-fA-F\s]+',payload):
        raise ValueError('Payload must contain hexadecimal byte pairs separated optionally by spaces')
    compact=re.sub(r'\s','',payload)
    if len(compact)%2:raise ValueError('Payload has an incomplete hexadecimal byte')
    data=bytes.fromhex(compact)
    db=teaching_database()
    try:message=db.get_message_by_frame_id(frame_id)
    except KeyError as error:raise ValueError('This ID is not in the small offline teaching DBC; use Raw CAN Investigation for other definitions') from error
    if len(data)!=message.length:raise ValueError(f'This message requires exactly {message.length} payload bytes')
    try:signal=message.get_signal_by_name(signal_name)
    except KeyError as error:raise ValueError('Select a signal defined for this arbitration ID') from error
    raw=message.decode(data,decode_choices=False,scaling=False)[signal.name]
    physical=message.decode(data,decode_choices=False)[signal.name]
    return {'frame_id':frame_id,'message':message.name,'payload_hex':data.hex(' ').upper(),
            'bytes':list(data),'binary':[f'{value:08b}' for value in data],
            'signal':signal.name,'bits':signal_bits(signal),'start_bit':signal.start,
            'length':signal.length,'byte_order':signal.byte_order,'signed':signal.is_signed,
            'raw_integer':raw,'unsigned_integer':raw & ((1<<signal.length)-1),
            'scale':signal.scale,'offset':signal.offset,'physical':physical,'unit':signal.unit,
            'evidence':'KUKSA-derived teaching definition; Level 2 interpretation, not physical accuracy' if frame_id==0x257 else 'Authored synthetic teaching definition'}


@dataclass(frozen=True)
class Node:
    name: str
    frame_id: int
    period_ms: int
    enabled: bool=True
    payload_hex: str | None=None
    stop_ms: int | None=None
    phase_ms: int=0


def network(nodes, *, duration_ms=1000, jitter_ms=0, jitter_node=None, jump_node=None, jump_at_ms=500, jump_kmh=60):
    """Release timeline with immediate python-can virtual delivery, not wire timing.

    Equal-time releases are sorted by ID solely for presentation. Actual CAN
    arbitration, retries, frame occupancy, bitrate and receiver clocks are unmodelled.
    All times are logical integer milliseconds, not VirtualBus wall timestamps.
    """
    if type(duration_ms) is not int or not 100<=duration_ms<=10000:raise ValueError('Duration must be 100–10000 ms')
    if not isinstance(nodes,(tuple,list)) or not 1<=len(nodes)<=4:raise ValueError('Configure one to four educational ECUs')
    if type(jitter_ms) is not int or not 0<=jitter_ms<=500:raise ValueError('Jitter must be 0–500 ms')
    if type(jump_at_ms) is not int or jump_at_ms<0 or (jump_node is not None and jump_at_ms>duration_ms):raise ValueError('Jump time must be within the simulation')
    if type(jump_kmh) is not int or not 0<=jump_kmh<=255:raise ValueError('Synthetic speed change must be 0–255 km/h')
    if any(not isinstance(node,Node) for node in nodes):raise ValueError('Node configurations must be Node objects')
    names=[node.name for node in nodes]
    if any(not isinstance(name,str) or not name.strip() for name in names) or len(set(names))!=len(names):raise ValueError('ECU names must be unique and nonempty')
    if len(set(node.frame_id for node in nodes))!=len(nodes):raise ValueError('Use distinct message IDs; same-ID data collisions are not modelled')
    for node in nodes:
        if type(node.frame_id) is not int or not 0<=node.frame_id<=0x7ff:raise ValueError('Use standard 11-bit IDs')
        if type(node.period_ms) is not int or not 10<=node.period_ms<=2000:raise ValueError('Periods must be 10–2000 ms')
        if type(node.enabled) is not bool:raise ValueError('Enable flag must be boolean')
        if type(node.phase_ms) is not int or not 0<=node.phase_ms<=2000:raise ValueError('Release phase must be 0–2000 ms')
        if node.stop_ms is not None and (type(node.stop_ms) is not int or not 0<=node.stop_ms<=duration_ms):raise ValueError('Stop time must be within simulation')
        if node.name==jitter_node and jitter_ms>=node.period_ms:raise ValueError('Jitter must be smaller than the selected node period')
        if node.payload_hex is not None:
            if not re.fullmatch(r'(?:[0-9A-Fa-f]{2}){1,8}',node.payload_hex):raise ValueError('Payload override needs 1–8 hexadecimal bytes, without spaces')
        if jump_node==node.name and (node.frame_id!=0x100 or node.payload_hex is not None):raise ValueError('Speed discontinuity requires original 0x100 synthetic message, without payload override')
    if jitter_node is not None and jitter_node not in names:raise ValueError('Unknown jitter node')
    if jump_node is not None and jump_node not in names:raise ValueError('Unknown jump node')
    schedule=[];codec=SyntheticCodec()
    for node in nodes:
        if not node.enabled:continue
        for step,release in enumerate(range(node.phase_ms,duration_ms+1,node.period_ms)):
            if node.stop_ms is not None and release>=node.stop_ms:continue
            timestamp=release+(jitter_ms if node.name==jitter_node and step%2 else 0)
            if timestamp>duration_ms:continue
            original=frames(step,codec)[1 if node.frame_id==0x200 else 0]
            payload=bytes.fromhex(node.payload_hex) if node.payload_hex is not None else bytes(original.data)
            if jump_node==node.name and release>=jump_at_ms:
                values=codec.database.get_message_by_name('EngineData').decode(payload)
                values['speed_kmh']=min(255,values['speed_kmh']+jump_kmh)
                payload=bytes(codec.encode('EngineData',values).data)
            schedule.append((timestamp,node.frame_id,node.name,step,release,payload))
    if len(schedule)>4004:raise ValueError('Experiment exceeds frame budget')
    schedule.sort(key=lambda row:(row[0],row[1],row[2]))
    channel='vcan-teaching-'+uuid4().hex
    events=[];last={}
    with can.Bus(interface='virtual',channel=channel,receive_own_messages=False) as sender, can.Bus(interface='virtual',channel=channel) as receiver:
        for index,(timestamp,identifier,name,step,release,payload) in enumerate(schedule):
            sender.send(can.Message(arbitration_id=identifier,data=payload,is_extended_id=False,check=True))
            received=receiver.recv(timeout=0)
            if received is None or bytes(received.data)!=payload:raise RuntimeError('Virtual bus did not deliver the scheduled frame')
            # Decode original supported messages through the original codec only.
            speed=None
            if identifier in (0x100,0x200) and len(payload)==8:
                received.timestamp=timestamp/1000
                speed=codec.decode(received,time_basis='relative').speed_kmh
            events.append({'index':index,'node':name,'frame_id':identifier,'timestamp_ms':timestamp,
                'nominal_release_ms':release,'sequence':step,'payload_hex':payload.hex().upper(),
                'interval_ms':timestamp-last[name] if name in last else None,'speed_kmh':speed})
            last[name]=timestamp
    counts={node.name:sum(event['node']==node.name for event in events) for node in nodes}
    return {'nodes':[asdict(node) for node in nodes],'duration_ms':duration_ms,'events':events,'counts':counts,
            'ground_truth':{'jitter_node':jitter_node,'jitter_ms':jitter_ms,'jump_node':jump_node,'jump_at_ms':jump_at_ms,'jump_kmh':jump_kmh},
            'assumptions':'Scheduled release timeline over python-can virtual transport. Equal releases sorted by ID for display; no bit-level arbitration, bandwidth, collision or wire-delay simulation.'}


def fault_findings(experiment, *, missing_factor=2.5, timing_tolerance_ms=10, rate_threshold_kmh_s=100):
    """Deterministic teaching rules with exact input event references, not v0.5."""
    for value in (missing_factor,timing_tolerance_ms,rate_threshold_kmh_s):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:raise ValueError('Thresholds must be finite and positive')
    findings=[]
    for node in experiment['nodes']:
        if not node['enabled']:continue
        rows=[event for event in experiment['events'] if event['node']==node['name']]
        period=node['period_ms'];threshold=period*missing_factor
        # Inspect internal gaps and the final silence interval against the actual
        # observation horizon, with an explicit schedule origin for zero arrivals.
        pairs=list(zip(rows,rows[1:]))+[(rows[-1] if rows else None,None)]
        for before,after in pairs:
            start=before['timestamp_ms'] if before else node.get('phase_ms',0)
            end=after['timestamp_ms'] if after else experiment['duration_ms']
            gap=end-start
            if gap>threshold:
                findings.append({'kind':'missing_message','node':node['name'],'expected_period_ms':period,
                    'last_received_ms':before['timestamp_ms'] if before else None,'observed_until_ms':end,
                    'interval_ms':gap,'threshold_ms':threshold,'exceeded':True,
                    'evidence_indices':[event['index'] for event in (before,after) if event is not None]})
        for before,after in zip(rows,rows[1:]):
            delta=after['timestamp_ms']-before['timestamp_ms'];deviation=abs(delta-period)
            findings.append({'kind':'timing','node':node['name'],'interval_ms':delta,'expected_period_ms':period,
                'deviation_ms':deviation,'threshold_ms':timing_tolerance_ms,'exceeded':deviation>timing_tolerance_ms,
                'evidence_indices':[before['index'],after['index']]})
            if before['speed_kmh'] is not None and after['speed_kmh'] is not None and delta>0:
                rate=(after['speed_kmh']-before['speed_kmh'])/(delta/1000)
                findings.append({'kind':'signal_rate','node':node['name'],'previous_kmh':before['speed_kmh'],
                    'current_kmh':after['speed_kmh'],'interval_ms':delta,'rate_kmh_s':rate,
                    'threshold_kmh_s':rate_threshold_kmh_s,'exceeded':abs(rate)>rate_threshold_kmh_s,
                    'evidence_indices':[before['index'],after['index']]})
    return findings
