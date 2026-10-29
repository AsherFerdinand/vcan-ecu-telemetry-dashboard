"""CLI adapter for decoded workbook analysis. No CAN transport is involved."""
import json
from .diagnostics import calculate_power
from .excel import load_xlsx
from .quality import QualityConfig, validate_recording, quality_summary
from .recorded_io import export_recording_json, export_annotated_csv, export_diagnostic_summary
from .recording import DatasetProfile
from .engineering import EngineeringConfig, analyze_engineering
from .engineering_reports import export_engineering_json, export_engineering_markdown, export_engineering_csv


def analyze(args):
    try:
        profile = DatasetProfile(**json.loads(args.profile.read_text())) if args.profile else DatasetProfile()
        config = QualityConfig(**json.loads(args.quality_config.read_text())) if args.quality_config else QualityConfig()
    except TypeError as error:
        raise ValueError('profile and quality configuration must be JSON objects with supported fields') from error
    engineering_config = EngineeringConfig.from_dict(json.loads(args.engineering_config.read_text())) if getattr(args,'engineering_config',None) else EngineeringConfig()
    outputs = [(args.output_prefix.with_name(args.output_prefix.name + suffix), exporter)
               for suffix, exporter in [('.json', export_recording_json), ('.csv', export_annotated_csv),
                                        ('.diagnostics.json', export_diagnostic_summary)]]
    if args.command == 'report-xlsx':
        outputs = []
    engineering_outputs = [(args.output_prefix.with_name(args.output_prefix.name + suffix), exporter) for suffix,exporter in [('.engineering.json',export_engineering_json),('.engineering.md',export_engineering_markdown)]]
    if getattr(args,'include_features',False):
        engineering_outputs.append((args.output_prefix.with_name(args.output_prefix.name+'.features.csv'),export_engineering_csv))
    if any(path.exists() for path, _ in outputs + engineering_outputs):
        raise ValueError('an analysis output already exists; choose a new output prefix')
    recording = load_xlsx(args.input, profile=profile, sheet=args.sheet, max_rows=args.max_rows)
    validate_recording(recording, config)
    calculate_power(recording)
    analysis = analyze_engineering(recording,engineering_config)
    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    for path, exporter in outputs:
        with path.open('x', encoding='utf-8', newline='') as stream:
            exporter(recording, stream)
    for path,exporter in engineering_outputs:
        with path.open('x',encoding='utf-8',newline='') as stream:
            exporter(recording,analysis,stream)
    print(json.dumps({**quality_summary(recording),'engineering':{'possible_sessions':len(analysis.sessions),'signed_net_kwh':analysis.energy['signed_net_kwh']}}))
    return 0
