"""Bounded offline candump/DBC investigation and sparse Recording adapter.

All raw payloads live once in a frame table. Observations reference that table;
there is no forward filling, frame merging, resampling or inferred compatibility.
"""
from dataclasses import asdict, dataclass
import hashlib
import math
from pathlib import Path
import re
from .codec import load_classical_dbc
from .artifacts import checked_source_metadata
from .recording import COLUMNS, CANONICAL_UNITS, DatasetProfile, Observation, Recording
from .quality import validate_recording
from .diagnostics import calculate_power

LINE = re.compile(rb'^\((\d+(?:\.\d+)?)\)\s+([A-Za-z0-9_.:-]{1,64})\s+([0-9a-fA-F]{3})#([0-9a-fA-F]*)\s*$')
CORE_SOURCE = {target: column for column,(target,unit) in COLUMNS.items()}


@dataclass
class CANConfig:
    max_frames: int = 10000  # scanned non-comment records, not just successful decodes
    max_preview_frames: int = 100
    max_line_bytes: int = 4096
    max_source_bytes: int = 128 * 1024 * 1024
    channel: str | None = None
    start_s: float | None = None
    end_s: float | None = None
    time_basis: str = 'relative'  # declaration, never inferred from magnitude
    dbc_frame_ids: tuple[int, ...] | None = None

    def __post_init__(self):
        for key in ('max_frames','max_preview_frames','max_line_bytes','max_source_bytes'):
            if type(getattr(self,key)) is not int or getattr(self,key)<1:
                raise ValueError(f'{key} must be a positive integer')
        if self.dbc_frame_ids is not None:
            if not isinstance(self.dbc_frame_ids,(tuple,list)) or not self.dbc_frame_ids or any(type(value) is not int or not 0 <= value <= 0x7ff for value in self.dbc_frame_ids) or len(set(self.dbc_frame_ids))!=len(self.dbc_frame_ids):
                raise ValueError('DBC selection requires unique standard frame IDs')
            self.dbc_frame_ids=tuple(self.dbc_frame_ids)
        if self.time_basis not in ('relative','unix'):
            raise ValueError('time_basis must be relative or unix')
        for value in (self.start_s,self.end_s):
            if value is not None and (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0):
                raise ValueError('time-window bounds must be finite nonnegative seconds')
        if self.start_s is not None and self.end_s is not None and self.start_s>self.end_s:
            raise ValueError('time window start exceeds end')
        if self.channel is not None and not re.fullmatch(r'[A-Za-z0-9_.:-]{1,64}',self.channel):
            raise ValueError('invalid channel selection')


@dataclass(frozen=True,slots=True)
class RawFrame:
    frame_index: int
    line_number: int
    byte_offset: int
    timestamp_text: str
    timestamp_s: float
    channel: str
    arbitration_id: int
    payload_hex: str


@dataclass(slots=True)
class FrameResult:
    frame: RawFrame
    status: str
    message: str | None
    signals: dict


@dataclass
class CANInvestigation:
    recording: Recording
    frames: list[FrameResult]
    definitions: dict
    coverage: dict
    configuration: dict
    source: dict
    dbc: dict
    validation: dict


def hash_stream(stream,limit):
    digest=hashlib.sha256(); count=0
    stream.seek(0)
    while chunk:=stream.read(min(1024*1024,limit-count+1)):
        if not isinstance(chunk,bytes):raise ValueError('CAN inputs must be binary streams')
        count+=len(chunk)
        if count>limit:raise ValueError(f'source exceeds explicit byte limit {limit}')
        digest.update(chunk)
    stream.seek(0)
    return digest.hexdigest(),count


def _definition(message):
    return {'name':message.name,'length':message.length,'frame_id':message.frame_id,
            'signals':{s.name:{'start_bit':s.start,'length':s.length,'byte_order':s.byte_order,
                'signed':s.is_signed,'scale':s.scale,'offset':s.offset,'unit':s.unit,
                'minimum':s.minimum,'maximum':s.maximum} for s in message.signals}}


def _validate_mapping(mapping,database):
    if not isinstance(mapping,list):raise ValueError('signal mapping must be a list')
    targets=set(); result={}
    for item in mapping:
        if not isinstance(item,dict) or set(item)!={'frame_id','signal','target'}:
            raise ValueError('each mapping requires frame_id, signal and target')
        identifier=item['frame_id'];target=item['target'];name=item['signal']
        if type(identifier) is not int or not isinstance(name,str) or not isinstance(target,str):
            raise ValueError('invalid mapping types')
        if target not in CANONICAL_UNITS and target!='rpm':raise ValueError(f'unknown canonical target {target}')
        if target=='charging_status':raise ValueError('CAN status-code semantics require a separate verified profile; no automatic mapping')
        if target in targets:raise ValueError('multiple source signals cannot silently populate the same target')
        try:
            message=database.get_message_by_frame_id(identifier)
            signal=next(s for s in message.signals if s.name==name)
        except (KeyError,StopIteration) as error:raise ValueError('mapping references an absent DBC signal') from error
        expected='rpm' if target=='rpm' else CANONICAL_UNITS[target]
        # Explicit conventional spelling alias, not a magnitude-based conversion.
        declared_unit={'kph':'km/h'}.get(signal.unit,signal.unit)
        if declared_unit!=expected:
            raise ValueError(f'{name}: explicit canonical mapping requires DBC unit {expected!r}; got {signal.unit!r}')
        targets.add(target);result[identifier,name]=target
    return result


def investigate_candump(source,dbc_source,*,mapping=None,config=None,source_metadata=None,dbc_metadata=None,references=None,expected_hashes=None):
    config=config or CANConfig()
    if expected_hashes is not None and (not isinstance(expected_hashes,dict) or set(expected_hashes)!={'source','dbc'} or any(not isinstance(v,str) or not re.fullmatch(r'[0-9a-f]{64}',v) for v in expected_hashes.values())):
        raise ValueError('expected hashes must contain exact source and DBC SHA-256 values')
    source_metadata=checked_source_metadata(source_metadata)
    dbc_metadata=checked_source_metadata(dbc_metadata)
    # Paths and seekable binary streams share the same bounded reader. Caller
    # streams are restored; source files are never rewritten or copied here.
    own_source=isinstance(source,(str,Path));own_dbc=isinstance(dbc_source,(str,Path))
    if not own_source and not all(hasattr(source,method) for method in ('read','readline','seek','tell')):
        raise ValueError('recording input must be a seekable binary stream or path')
    if not own_dbc and not all(hasattr(dbc_source,method) for method in ('read','seek','tell')):
        raise ValueError('DBC input must be a seekable binary stream or path')
    stream=open(source,'rb') if own_source else source
    dbc_stream=None; source_position=stream.tell();dbc_position=0
    try:
        dbc_stream=open(dbc_source,'rb') if own_dbc else dbc_source
        dbc_position=dbc_stream.tell()
        source_hash,source_bytes=hash_stream(stream,config.max_source_bytes)
        dbc_hash,dbc_bytes=hash_stream(dbc_stream,2*1024*1024)
        if expected_hashes is not None and (source_hash!=expected_hashes['source'] or dbc_hash!=expected_hashes['dbc']):
            raise ValueError('source/DBC hash does not match the documented source manifest')
        text=dbc_stream.read().decode('utf-8-sig')
        database=load_classical_dbc(text,frame_ids=config.dbc_frame_ids)
        if sum(len(m.signals) for m in database.messages)>10000:
            raise ValueError('DBC signal-definition budget exceeded')
        definitions={str(m.frame_id):_definition(m) for m in database.messages}
        mappings=_validate_mapping(mapping if mapping is not None else [],database)
        coverage={'scanned_records':0,'selected_frames':0,'decoded_frames':0,'unknown_id_frames':0,
                  'invalid_length_frames':0,'malformed_records':0,'decode_errors':0,
                  'channel_filtered':0,'time_filtered':0,'unsupported_frames':0,
                  'limit_reached':False,'complete_source_scanned':False,'identifiers':{},'examples':[]}
        frames=[];observations=[];channel=None;line_number=0;offset=0
        while True:
            if coverage['scanned_records']>=config.max_frames:
                coverage['limit_reached']=bool(stream.read(1))
                coverage['complete_source_scanned']=not coverage['limit_reached']
                break
            raw=stream.readline(config.max_line_bytes+1)
            if not raw:
                coverage['complete_source_scanned']=True;break
            line_number+=1;line_offset=offset;offset+=len(raw)
            if len(raw)>config.max_line_bytes:
                # Fail cleanly rather than treat fragments of an oversized line
                # as separate records or allocate an unbounded buffer.
                raise ValueError(f'line {line_number} exceeds explicit line-byte limit')
            if not raw.strip() or raw.lstrip().startswith(b'#'):continue
            coverage['scanned_records']+=1
            match=LINE.fullmatch(raw.strip())
            if match is None:
                key='unsupported_frames' if b'##' in raw or b'#R' in raw or re.search(rb'\s[0-9A-Fa-f]{8}#',raw) else 'malformed_records'
                coverage[key]+=1
                if len(coverage['examples'])<20:coverage['examples'].append({'line_number':line_number,'byte_offset':line_offset,'reason':key})
                continue
            stamp,bus,identifier,payload=match.groups()
            timestamp=float(stamp);identifier=int(identifier,16)
            if not math.isfinite(timestamp) or identifier>0x7ff or len(payload)%2 or len(payload)>16:
                coverage['malformed_records']+=1;continue
            bus=bus.decode()
            if config.channel and bus!=config.channel:
                coverage['channel_filtered']+=1;continue
            if (config.start_s is not None and timestamp<config.start_s) or (config.end_s is not None and timestamp>config.end_s):
                coverage['time_filtered']+=1;continue
            if channel is not None and bus!=channel:
                raise ValueError('multiple selected channels: select one explicitly; frames are not merged across buses')
            channel=bus
            frame=RawFrame(coverage['scanned_records'],line_number,line_offset,stamp.decode(),timestamp,bus,identifier,payload.decode().upper())
            coverage['selected_frames']+=1
            key=f'0x{identifier:03X}';coverage['identifiers'][key]=coverage['identifiers'].get(key,0)+1
            try:message=database.get_message_by_frame_id(identifier)
            except KeyError:
                coverage['unknown_id_frames']+=1;frames.append(FrameResult(frame,'unknown_id',None,{}));continue
            if len(payload)//2!=message.length:
                coverage['invalid_length_frames']+=1;frames.append(FrameResult(frame,'invalid_length',message.name,{}));continue
            try:
                values=message.decode(bytes.fromhex(frame.payload_hex),decode_choices=False)
                if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in values.values()):
                    raise ValueError('decoded nonfinite/nonnumeric signal')
            except Exception:
                coverage['decode_errors']+=1;frames.append(FrameResult(frame,'decode_error',message.name,{}));continue
            coverage['decoded_frames']+=1;frames.append(FrameResult(frame,'decoded',message.name,values))
            normalized={name:None for name in CANONICAL_UNITS}
            if 'rpm' in mappings.values():normalized['rpm']=None
            original={'time':frame.timestamp_text,'frame_ref':len(frames)-1}
            for name,value in values.items():
                target=mappings.get((identifier,name))
                if target:
                    normalized[target]=value
                    original[CORE_SOURCE.get(target,'engine_rpm')]=value
            observations.append(Observation(line_number,timestamp,original,normalized))
        source_info={'name':Path(source).name if own_source else Path(str(getattr(stream,'name','uploaded-candump.log'))).name,
                     **(source_metadata or {}),'sha256':source_hash,'bytes':source_bytes}
        dbc_info={'name':Path(dbc_source).name if own_dbc else Path(str(getattr(dbc_stream,'name','uploaded.dbc'))).name,
                  **(dbc_metadata or {}),'sha256':dbc_hash,'bytes':dbc_bytes}
        for info in (source_info,dbc_info):
            for key in ('url','revision','license','compatibility_status'):info.setdefault(key,None)
        signals={target:{'source_column':column,'source_unit':unit,'canonical_unit':unit,
                         'unit_status':'unverified','meaning_status':'not_mapped','present':False}
                 for column,(target,unit) in COLUMNS.items()}
        for (identifier,name),target in mappings.items():
            unit='rpm' if target=='rpm' else CANONICAL_UNITS[target]
            signals[target]={'source_column':CORE_SOURCE.get(target,'engine_rpm'),'source_unit':database.get_message_by_frame_id(identifier).get_signal_by_name(name).unit,'canonical_unit':unit,
                             'unit_status':'dbc_declared','meaning_status':'user_mapping_not_independent_physical_verification',
                             'present':True,'frame_id':identifier,'dbc_signal':name}
        metadata={'schema':'can-lab-recording-1','data_kind':'decoded_raw_can','source_filename':source_info['name'],
            'sha256':source_hash,'profile':{'dataset_id':source_info.get('dataset_id',source_info['name']),
                'time_unit':'s','time_basis':config.time_basis,'current_convention':'unknown','current_reference':'',
                'units':{},'reference':'DBC units and user-selected mappings are declarations, not independent vehicle validation'},
            'signals':signals,'additional_signals':['rpm'] if 'rpm' in mappings.values() else [],
            'normalized_time_basis':config.time_basis,'time_interpretation_status':'profile_declared_candump_seconds',
            'source_columns':['time','frame_ref']+list(dict.fromkeys(spec['source_column'] for spec in signals.values() if spec['present'])),
            'can_definitions':definitions,
            'can_dbc_scope':{'selected_frame_ids':list(config.dbc_frame_ids) if config.dbc_frame_ids else None,
                'note':'Original DBC bytes/hash retained; only explicitly selected messages are eligible for decoding. Unselected IDs count as unknown in this scope.'},
            'can_frames':[{**asdict(entry.frame),'status':entry.status,'message':entry.message,'decoded_signals':entry.signals} for entry in frames],
            'can_source':source_info,'can_dbc':dbc_info,'can_mapping':mapping or [],'can_references':references,
            'temporal_alignment':'one observation per decoded frame; no merge, fill, resampling or cross-frame simultaneity',
            'frame_reference':'Observation.raw.frame_ref indexes CANInvestigation.frames (zero-based); retain source file and source/DBC hashes',
            'warnings':['Recording/DBC physical compatibility is user-supplied and unverified.',
                        'Independent physical accuracy is not established by successful decoding.',
                        'Missing battery fields remain optional; no power from separate unsynchronised frames.']}
        recording=Recording(metadata,observations)
        validate_recording(recording)
        # Retain independent range screening after the general sparse validator.
        for row in observations:
            entry=frames[row.raw['frame_ref']]
            for name,value in entry.signals.items():
                target=mappings.get((entry.frame.arbitration_id,name))
                spec=definitions[str(entry.frame.arbitration_id)]['signals'][name]
                if target and spec['minimum'] is not None and spec['maximum'] is not None and spec['minimum']<spec['maximum'] and not spec['minimum']<=value<=spec['maximum']:
                    row.flag(target,'OUT_OF_RANGE','dbc_declared_range')
            if not any(value is not None for value in row.values.values()):row.flag('mapping','MISSING','no_selected_signal_in_frame')
        for row in observations:
            if 'rpm' in mappings.values() and row.values.get('rpm') is None:
                row.flag('rpm','MISSING','no_source_signal_in_frame')
        calculate_power(recording)
        result=CANInvestigation(recording,frames,definitions,coverage,asdict(config),source_info,dbc_info,{})
        result.validation=check_references(result,references) if references is not None else {'status':'not_supplied','physical_accuracy':'not_established'}
        return result
    finally:
        if own_source:stream.close()
        else:stream.seek(source_position)
        if dbc_stream is not None:
            if own_dbc:dbc_stream.close()
            else:dbc_stream.seek(dbc_position)


def check_references(investigation,references):
    if not isinstance(references,dict) or references.get('dbc_sha256')!=investigation.dbc['sha256']:
        raise ValueError('reference evidence must bind the exact DBC SHA-256')
    if references.get('evidence_kind') not in ('synthetic_manual_vectors','documented_dbc_vectors','independent_reference_measurements'):
        raise ValueError('reference evidence kind must be explicit')
    if not isinstance(references.get('source'),str) or not references['source']:
        raise ValueError('reference source/method must be documented')
    from pathlib import PureWindowsPath
    text=references['source']
    if any(Path(token).is_absolute() or PureWindowsPath(token).is_absolute() for token in text.split()):
        raise ValueError('reference source must not expose absolute private paths')
    if text.startswith('https://'):checked_source_metadata({'url':text})
    vectors=references.get('vectors')
    if not isinstance(vectors,list) or not vectors:raise ValueError('reference vectors must be nonempty')
    results=[]
    if len(vectors)>1000:raise ValueError('reference budget exceeds 1000 vectors')
    for vector in vectors:
        if not isinstance(vector,dict):raise ValueError('reference vector must be an object')
        expected=vector.get('expected');tolerance=vector.get('absolute_tolerance')
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in (expected,tolerance)) or tolerance<0:
            raise ValueError('reference values/tolerances must be finite; tolerance nonnegative')
        observed=[entry for entry in investigation.frames if entry.status=='decoded' and entry.frame.arbitration_id==vector.get('frame_id') and entry.frame.payload_hex==str(vector.get('payload_hex')).upper()]
        if not observed:
            results.append({'signal':vector.get('signal'),'status':'not_observed'});continue
        entry=observed[0];name=vector.get('signal')
        if name not in entry.signals:raise ValueError('reference signal absent from matched frame')
        definition=investigation.definitions[str(entry.frame.arbitration_id)]['signals'][name]
        if vector.get('unit')!=definition['unit']:raise ValueError('reference/DBC unit mismatch')
        actual=entry.signals[name];error=abs(actual-expected)
        results.append({'signal':name,'frame_ref':investigation.frames.index(entry),'expected':expected,'observed':actual,
                        'absolute_error':error,'absolute_tolerance':tolerance,'unit':definition['unit'],
                        'status':'pass' if error<=tolerance else 'fail'})
    return {'status':'checked','evidence_kind':references['evidence_kind'],'source':references['source'],
            'results':results,'passed':sum(r['status']=='pass' for r in results),
            'failed':sum(r['status']=='fail' for r in results),'not_observed':sum(r['status']=='not_observed' for r in results),
            'physical_accuracy':'not_established','interpretation':'Reference comparisons do not authenticate vehicle provenance, calibration or recording/DBC compatibility.'}
