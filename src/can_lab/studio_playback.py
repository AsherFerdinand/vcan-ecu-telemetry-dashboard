"""Bounded UI playhead over original deterministic events, independent of Streamlit."""
from dataclasses import dataclass
from .workbench import Node,network
from .codec import SyntheticCodec

NAMES=['Motor controller','Battery Management System','Vehicle Control Unit','Brake ECU','Instrument cluster']


def vehicle_experiment(duration_ms=1500):
    # Four actual publishers (the existing core cap), with Brake ECU as a passive
    # observer. Motor/BMS use the original synthetic engine/temperature protocol.
    experiment=network([Node(NAMES[0],0x100,100),Node(NAMES[1],0x200,200,phase_ms=10),
                    Node(NAMES[2],0x310,250,phase_ms=20),Node(NAMES[4],0x410,500,phase_ms=30)],duration_ms=duration_ms)
    experiment['studio_vehicle']=True
    return experiment


def inspect_event(experiment,index):
    if type(index) is not int or not 0<=index<len(experiment['events']):raise ValueError('Event index outside retained buffer')
    event=experiment['events'][index];decoded={}
    try:
        message=SyntheticCodec().database.get_message_by_frame_id(event['frame_id'])
        if message.length==len(bytes.fromhex(event['payload_hex'])):
            decoded=message.decode(bytes.fromhex(event['payload_hex']),decode_choices=False)
    except KeyError:pass
    observers=[node['name'] for node in experiment['nodes']]+(['Brake ECU'] if experiment.get('studio_vehicle') else [])
    return {**event,'dlc':len(event['payload_hex'])//2,'decoded':decoded,
            'receiving_nodes':[name for name in observers if name!=event['node']],
            'reception_policy':'One python-can receiver validates the event. Per-ECU reception is modeled shared-bus observability, no acceptance filtering; not individual receive queues or hardware ACK'}


@dataclass
class Playhead:
    length: int
    index: int=0
    playing: bool=False

    def __post_init__(self):
        if type(self.length) is not int or not 1<=self.length<=4004:raise ValueError('Playback buffer must contain 1–4004 items')

    def move(self,delta):
        if type(delta) is not int:raise ValueError('Playback step must be an integer')
        self.index=max(0,min(self.length-1,self.index+delta));self.playing=False

    def tick(self):
        if self.playing:
            self.index=min(self.length-1,self.index+1)
            if self.index==self.length-1:self.playing=False

    def reset(self):self.index=0;self.playing=False
