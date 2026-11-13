"""Pure educational standard classical data-frame and ideal physical-layer models.

CRC-15/CAN: poly 0x4599, init 0, non-reflected, xorout 0. Input is SOF through
Data, unstuffed, MSB first. No extended, remote, FD, error or overload frames.
"""
import math


def bits(value,width):
    if type(value) is not int or not 0<=value<2**width:raise ValueError('Value does not fit bit width')
    return [int(bit) for bit in f'{value:0{width}b}']


def checked_bits(sequence):
    if not isinstance(sequence,(list,tuple,str)) or not sequence or len(sequence)>128:raise ValueError('Use 1–128 binary bits')
    if any(str(bit) not in ('0','1') for bit in sequence):raise ValueError('Sequence must contain only 0 or 1')
    return [int(bit) for bit in sequence]


def crc15(sequence):
    # Input lengths can exceed the physical-layer illustration limit.
    crc=0
    for bit in sequence:
        if type(bit) is not int or bit not in (0,1):raise ValueError('CRC input must be binary integers')
        feedback=(crc>>14)^bit
        crc=(crc<<1)&0x7fff
        if feedback:crc^=0x4599
    return crc


def stuff_bits(sequence):
    result=[];previous=None;count=0
    for index,bit in enumerate(sequence):
        if type(bit) is not int or bit not in (0,1):raise ValueError('Stuffing input must be binary integers')
        result.append({'bit':bit,'stuffed':False,'source_index':index})
        count=count+1 if bit==previous else 1;previous=bit
        if count==5:
            previous=1-bit;count=1
            result.append({'bit':previous,'stuffed':True,'source_index':None})
    return result


PURPOSES={
 'SOF':'Dominant 0 starts the frame and supports synchronization.',
 'Identifier':'11-bit message identity and arbitration priority, MSB first; not a destination address.',
 'RTR':'0 for this supported data frame; remote frames are not implemented.',
 'IDE':'0 selects standard format; extended format is not implemented.',
 'r0':'Reserved control bit, transmitted dominant in this supported format.',
 'DLC':'Four-bit code; this model supports values 0–8, equal to the payload byte count.',
 'Data':'Payload bytes, each transmitted MSB first. DBC signal byte order is a separate interpretation.',
 'CRC sequence':'CRC-15/CAN over unstuffed SOF through Data. Polynomial 0x4599, init/xorout 0, non-reflected.',
 'CRC delimiter':'Fixed recessive 1, outside the stuffed region.',
 'ACK slot':'Transmitter sends recessive. A correctly receiving simulated peer may drive dominant; this is not application acceptance.',
 'ACK delimiter':'Fixed recessive 1.',
 'EOF':'Seven recessive bits end the frame.',
 'Intermission':'Three recessive bits AFTER the frame; not part of the data frame.'}


def classical_frame(identifier,payload,*,dlc=None,acknowledged=True):
    if type(identifier) is not int or not 0<=identifier<=0x7ff:raise ValueError('Use a standard 11-bit ID')
    if not isinstance(payload,bytes) or len(payload)>8:raise ValueError('Classical payload must contain 0–8 bytes')
    dlc=len(payload) if dlc is None else dlc
    if type(dlc) is not int or not 0<=dlc<=8 or dlc!=len(payload):raise ValueError('Supported DLC 0–8 must equal the payload byte count')
    if type(acknowledged) is not bool:raise ValueError('ACK selection must be boolean')
    fields=[]
    def add(name,value,inside=True):
        fields.append({'name':name,'bits':value,'length':len(value),'purpose':PURPOSES[name],'inside_frame':inside})
    add('SOF',[0]);add('Identifier',bits(identifier,11));add('RTR',[0]);add('IDE',[0]);add('r0',[0]);add('DLC',bits(dlc,4))
    add('Data',[bit for byte in payload for bit in bits(byte,8)])
    crc_input=[bit for field in fields for bit in field['bits']];crc=crc15(crc_input)
    add('CRC sequence',bits(crc,15))
    stuffed=stuff_bits(crc_input+bits(crc,15))
    add('CRC delimiter',[1]);add('ACK slot',[0 if acknowledged else 1]);add('ACK delimiter',[1]);add('EOF',[1]*7)
    frame_bits=[bit for field in fields for bit in field['bits']]
    add('Intermission',[1]*3,False)
    tail=[bit for field in fields[8:] for bit in field['bits']]
    return {'identifier':identifier,'dlc':dlc,'payload_hex':payload.hex(' ').upper(),'fields':fields,
            'crc':crc,'crc_input':crc_input,'unstuffed_frame_bits':frame_bits,'stuffed_region':stuffed,
            'stuff_count':sum(item['stuffed'] for item in stuffed),'transmitted_with_intermission':[item['bit'] for item in stuffed]+tail,
            'acknowledged':acknowledged,'ack_transmitter_bit':1,'ack_evidence':'simulated receiver only',
            'supported':'Standard 11-bit classical data frame, DLC 0–8; no hardware capture or bit-timing claim'}


def arbitrate(identifiers):
    if not isinstance(identifiers,(list,tuple)) or not 2<=len(identifiers)<=4:raise ValueError('Use 2–4 standard data-frame contenders')
    if any(type(value) is not int or not 0<=value<=0x7ff for value in identifiers):raise ValueError('Use standard 11-bit IDs')
    if len(set(identifiers))!=len(identifiers):raise ValueError('Duplicate IDs are unsupported: identifier arbitration cannot resolve their differing payloads')
    encoded=[bits(value,11) for value in identifiers];active=set(range(len(identifiers)));steps=[]
    for column in range(11):
        sent={index:encoded[index][column] for index in sorted(active)}
        bus=min(sent.values());lost=[index for index,bit in sent.items() if bit==1 and bus==0]
        active.difference_update(lost)
        steps.append({'column':column,'identifier_bit':10-column,'sent':sent,'bus':bus,'lost':lost,'active':sorted(active)})
    return {'identifiers':list(identifiers),'bits':encoded,'steps':steps,'winner':identifiers[next(iter(active))],
            'scope':'Simultaneous standard data-frame identifier arbitration only; no occupancy or latency model'}


def differential(sequence,*,amplitude=0.0):
    sequence=checked_bits(sequence)
    if isinstance(amplitude,bool) or not isinstance(amplitude,(int,float)) or not math.isfinite(amplitude) or not 0<=amplitude<=1:
        raise ValueError('Illustrative common-mode amplitude must be 0–1 V')
    rows=[]
    for index,bit in enumerate(sequence):
        noise=amplitude*math.sin((index+1)*math.pi/4)
        high,low=(2.5,2.5) if bit else (3.5,1.5)
        rows.append({'index':index,'bit':bit,'state':'Recessive' if bit else 'Dominant',
            'CAN_H_original':high,'CAN_L_original':low,'noise':noise,'CAN_H':high+noise,'CAN_L':low+noise,
            'Vdiff':(high+noise)-(low+noise)})
    return rows
