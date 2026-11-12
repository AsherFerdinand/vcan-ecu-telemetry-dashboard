"""Deterministic bounded CAN reports, separate from full provenance exports."""
from dataclasses import asdict
import json
from . import __version__


def build_can_report(investigation):
    coverage=investigation.coverage
    return {'schema':'vcan-can-investigation-1','software_version':__version__,
            'status':'implemented; synthetic-fixture validated; real-vehicle validation blocked',
            'source':investigation.source,'dbc':investigation.dbc,'configuration':investigation.configuration,
            'coverage':coverage,'decoding_fraction_of_selected_frames':coverage['decoded_frames']/coverage['selected_frames'] if coverage['selected_frames'] else None,
            'dbc_definitions':investigation.definitions,
            'frame_preview':[asdict(frame) for frame in investigation.frames[:investigation.configuration['max_preview_frames']]],
            'mapping':investigation.recording.metadata['can_mapping'],
            'recording_observations':len(investigation.recording.observations),
            'temporal_alignment':investigation.recording.metadata['temporal_alignment'],
            'validation':investigation.validation,
            'evidence_levels':{'parser':'implemented; synthetic regression tests',
                'dbc_interpretation':'reference comparisons reported separately; library self-consistency is not independent evidence',
                'signal_plausibility':'DBC/profile declarations and research screening only',
                'independent_physical_accuracy':'not_established'},
            'limitations':['No compatible real recording/DBC with independent physical reference was selected.',
                'Standard-ID classical nonmultiplexed integer signals only; FD, RTR, error, extended and float/multiplexed DBC definitions are unsupported.',
                'No cross-frame alignment, resampling or invented battery measurements.',
                'Full frames live once in the Recording metadata table; observations reference table indices.',
                'A bounded scan is not a statement about complete-file decoding coverage.'],
    }


def export_can_json(investigation,stream):
    json.dump(build_can_report(investigation),stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')


def export_can_markdown(investigation,stream):
    report=build_can_report(investigation);coverage=investigation.coverage
    stream.write('# VCAN raw CAN investigation\n\n')
    stream.write('Status: **Implemented foundation; synthetic-fixture validated. Real-vehicle physical validation blocked.**\n\n')
    stream.write(f"Source SHA-256: `{investigation.source['sha256']}`\n\nDBC SHA-256: `{investigation.dbc['sha256']}`\n\n")
    stream.write('| Coverage | Count/status |\n| --- | --- |\n')
    for key in ('scanned_records','selected_frames','decoded_frames','unknown_id_frames','invalid_length_frames','malformed_records','unsupported_frames','decode_errors','limit_reached','complete_source_scanned'):
        stream.write(f'| {key} | {coverage[key]} |\n')
    stream.write('\n## Evidence\n\n```json\n'+json.dumps(investigation.validation,indent=2,sort_keys=True,allow_nan=False)+'\n```\n\n')
    stream.write('## Signal definitions\n\n| ID / message | Signal | Scale | Offset | Unit |\n| --- | --- | --- | --- | --- |\n')
    def text(value):return str(value).replace('|','\\|').replace('\n',' ')
    for identifier,message in investigation.definitions.items():
        for signal,definition in message['signals'].items():
            stream.write(f"| {identifier} / {text(message['name'])} | {text(signal)} | {definition['scale']} | {definition['offset']} | {text(definition['unit'])} |\n")
    stream.write('\n## Limitations\n\n')
    for item in report['limitations']:stream.write('- '+item+'\n')
