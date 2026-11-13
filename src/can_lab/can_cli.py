"""Explicit offline CAN investigation; files are created only on request."""
import json
from pathlib import Path
from .can_recording import CANConfig, investigate_candump
from .can_reports import export_can_json, export_can_markdown, build_can_report
from .artifacts import generated_output, build_manifest
from .recorded_io import export_recording_json
from .engineering import analyze_engineering
from .engineering_reports import export_engineering_json


def load_json_config(path):
    if path is None:return None
    path=Path(path)
    if path.stat().st_size>256*1024:raise ValueError('JSON configuration exceeds 256 KiB budget')
    return json.loads(path.read_text(encoding='utf-8'))


def run(args):
    mapping=load_json_config(args.mapping)
    references=load_json_config(args.references)
    provenance=load_json_config(args.provenance) if getattr(args,'provenance',None) else None
    if provenance is not None:
        if not isinstance(provenance,dict) or provenance.get('schema')!='vcan-source-manifest-1':
            raise ValueError('invalid source manifest schema')
        if not all(isinstance(provenance.get(key),dict) for key in ('source','dbc','expected_hashes')):
            raise ValueError('source manifest requires source, dbc and expected_hashes objects')
        if args.source_metadata or args.dbc_metadata:raise ValueError('use either provenance manifest or individual source metadata')
    config=CANConfig(max_frames=args.max_frames,max_preview_frames=min(args.preview_frames,args.max_frames),
        max_source_bytes=args.max_source_bytes,dbc_frame_ids=getattr(args,'dbc_frame_id',None),channel=args.channel,start_s=args.start_s,end_s=args.end_s,time_basis=args.time_basis)
    outputs=[]
    root=Path(args.output_root).absolute()
    if args.output_prefix:
        for suffix,exporter in [('.can.json',export_can_json),('.can.md',export_can_markdown)]:
            outputs.append((generated_output(str(args.output_prefix)+suffix,root),exporter,'can'))
        if args.include_recording:outputs.append((generated_output(str(args.output_prefix)+'.recording.json',root),export_recording_json,'recording'))
        if args.engineering_report:outputs.append((generated_output(str(args.output_prefix)+'.engineering.json',root),export_engineering_json,'engineering'))
        manifest_path=generated_output(str(args.output_prefix)+'.manifest.json',root)
    elif args.include_recording or args.engineering_report:
        raise ValueError('extra exports require an explicit output prefix')
    result=investigate_candump(args.input,args.dbc,mapping=mapping,config=config,
        source_metadata=provenance['source'] if provenance else load_json_config(args.source_metadata),dbc_metadata=provenance['dbc'] if provenance else load_json_config(args.dbc_metadata),references=references,expected_hashes=provenance.get('expected_hashes') if provenance else None)
    if provenance:
        hashes=provenance.get('expected_hashes',{})
        if hashes.get('source')!=result.source['sha256'] or hashes.get('dbc')!=result.dbc['sha256']:
            raise ValueError('source/DBC hash does not match the documented source manifest')
    analysis=None
    if args.engineering_report:
        if not result.recording.observations:raise ValueError('no decoded observations for engineering analysis')
        analysis=analyze_engineering(result.recording)
    for path,exporter,kind in outputs:
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('x',encoding='utf-8') as stream:
            if kind=='can':exporter(result,stream)
            elif kind=='recording':exporter(result.recording,stream)
            else:exporter(result.recording,analysis,stream)
    if outputs:
        def portable(path,placeholder):
            path=Path(path).absolute()
            try:return path.relative_to(Path.cwd()).as_posix()
            except ValueError:return '${'+placeholder+'}/'+path.name
        command=['python','-m','can_lab.cli','investigate-can',portable(args.input,'VCAN_DATA_DIR'),'--dbc',portable(args.dbc,'VCAN_DATA_DIR'),'--time-basis',config.time_basis,'--max-frames',str(config.max_frames)]
        for key in ('mapping','references','source_metadata','dbc_metadata','provenance'):
            if getattr(args,key):command+=['--'+key.replace('_','-'),portable(getattr(args,key),'VCAN_CONFIG_DIR')]
        command+=['--max-source-bytes',str(config.max_source_bytes),'--preview-frames',str(config.max_preview_frames)]
        for identifier in config.dbc_frame_ids or ():
            command+=['--dbc-frame-id',hex(identifier)]
        if config.channel:command+=['--channel',config.channel]
        if config.start_s is not None:command+=['--start-s',str(config.start_s)]
        if config.end_s is not None:command+=['--end-s',str(config.end_s)]
        if args.include_recording:command+=['--include-recording']
        if args.engineering_report:command+=['--engineering-report']
        command+=['--output-prefix','${VCAN_OUTPUT_ROOT}/reproduction','--output-root','${VCAN_OUTPUT_ROOT}']
        manifest=build_manifest(result,[p for p,_,_ in outputs],output_root=root,
            reproduction={'command':command,'configuration':result.configuration,
                          'note':'Replace path placeholders with hash-matching inputs; reapply channel/time/byte/preview limits from configuration. No absolute private paths are stored.'})
        with manifest_path.open('x',encoding='utf-8') as stream:json.dump(manifest,stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')
    report=build_can_report(result)
    print(json.dumps({'status':report['status'],'coverage':result.coverage,'validation':result.validation},sort_keys=True))
    return 2 if result.validation.get('failed',0) or result.validation.get('not_observed',0) else 0
