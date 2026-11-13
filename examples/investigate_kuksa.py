"""Explicit external-data investigation. No downloads, source copies or full exports.

Run from the repository root; see docs/kuksa_investigation.md. Expected values
were manually calculated from documented DBC bits, not independently measured.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
from can_lab.artifacts import build_manifest, generated_output, format_size
from can_lab.can_recording import CANConfig, investigate_candump, check_references
from can_lab.can_reports import export_can_json, export_can_markdown, signal_summary
from can_lab.engineering import analyze_engineering
from can_lab.recording_review import dimension_summary


def investigate(data_directory, output_prefix, output_root):
    root=Path(__file__).resolve().parents[1]
    manifest=json.loads((root/'data/manifests/kuksa_model3.json').read_text())
    mapping=json.loads((root/'data/manifests/kuksa_mapping.json').read_text())
    paths={suffix:generated_output(str(output_prefix)+suffix,output_root)
           for suffix in ('.can.json','.can.md','.summary.json','.manifest.json')}
    config=CANConfig(max_frames=10000,max_preview_frames=6,channel='elmcan',time_basis='unix',
                     dbc_frame_ids=(0x118,0x257,0x266))
    result=investigate_candump(Path(data_directory)/'candump.log',Path(data_directory)/'Model3CAN.dbc',
        mapping=mapping,config=config,source_metadata=manifest['source'],dbc_metadata=manifest['dbc'],
        expected_hashes=manifest['expected_hashes'])
    # Source hashes bind line references to the exact public file. Copy only the
    # three matching payloads into local evidence metadata, not a second log.
    frames={entry.frame.line_number:entry for entry in result.frames}
    vectors=[]
    for line,name,expected,unit in [(9989,'DI_accelPedalPos',12.8,'%'),
                                   (9995,'RearPower266',4.5,'kW'),
                                   (9997,'DI_vehicleSpeed',3.04,'kph')]:
        frame=frames[line].frame
        vectors.append({'frame_id':frame.arbitration_id,'payload_hex':frame.payload_hex,
                        'signal':name,'expected':expected,'absolute_tolerance':1e-10,'unit':unit})
    references={'dbc_sha256':result.dbc['sha256'],'evidence_kind':'documented_dbc_vectors',
        'source':'Manual byte arithmetic at source lines 9989/9995/9997, documented in docs/kuksa_investigation.md; DBC interpretation only, not physical measurement',
        'vectors':vectors}
    result.validation=check_references(result,references)
    result.recording.metadata['can_references']=references
    signals=signal_summary(result)
    analysis=analyze_engineering(result.recording)
    summary={'evidence_level_demonstrated':2,'independent_physical_validation':'blocked',
        'timestamp_basis':'unix declared for investigation; clock authenticity/date attribution unresolved',
        'first_timestamp':result.frames[0].frame.timestamp_text,'last_timestamp':result.frames[-1].frame.timestamp_text,
        'span_s':result.frames[-1].frame.timestamp_s-result.frames[0].frame.timestamp_s,
        'timestamp_reversals':sum(result.frames[index].frame.timestamp_s < result.frames[index-1].frame.timestamp_s for index in range(1,len(result.frames))),
        'coverage':result.coverage,'signals':signals,'reference_checks':result.validation,
        'quality':dimension_summary(result.recording),
        'engineering':{'energy':analysis.energy,'state_counts':dict(Counter(state for point in analysis.operating for state in point.candidates)),
                       'uncertainties':analysis.uncertainties,
                       'limitations':['Only speed is mapped; negative values retained and screened by existing nonnegative-speed policy.',
                         'Sparse observations reset derivative history; no cross-frame alignment or acceleration/energy inference.',
                         'Rear motor power is not battery power and is not mapped to a battery signal.']}}
    for suffix,exporter in (('.can.json',export_can_json),('.can.md',export_can_markdown)):
        paths[suffix].parent.mkdir(parents=True,exist_ok=True)
        with paths[suffix].open('x',encoding='utf-8') as stream:exporter(result,stream)
    with paths['.summary.json'].open('x',encoding='utf-8') as stream:
        json.dump(summary,stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')
    run=build_manifest(result,[paths[key] for key in ('.can.json','.can.md','.summary.json')],output_root=output_root,
        repository_root=root,reproduction={'command':['python','examples/investigate_kuksa.py','--data-dir','${VCAN_DATA_DIR}',
            '--output-prefix','${VCAN_OUTPUT_ROOT}/kuksa','--output-root','${VCAN_OUTPUT_ROOT}'],
            'script_configuration':'fixed first 10000 original records; exact input hashes and three explicit DBC IDs'})
    with paths['.manifest.json'].open('x',encoding='utf-8') as stream:
        json.dump(run,stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')
    print(json.dumps({'coverage':result.coverage,'passed':result.validation['passed'],
                      'physical_accuracy':'not_established','output_size':format_size(sum(path.stat().st_size for path in paths.values()))}))
    return result,summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,required=True)
    parser.add_argument('--output-prefix',type=Path,required=True)
    parser.add_argument('--output-root',type=Path,default=Path('outputs'))
    args=parser.parse_args()
    result,_=investigate(args.data_dir,args.output_prefix,args.output_root)
    raise SystemExit(2 if result.validation.get('failed') or result.validation.get('not_observed') else 0)
