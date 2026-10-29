"""CLI adapter for decoded workbook analysis. No CAN transport is involved."""
import json
from .diagnostics import calculate_power
from .excel import load_xlsx
from .quality import QualityConfig, validate_recording, quality_summary
from .recorded_io import export_recording_json, export_annotated_csv, export_diagnostic_summary
from .recording import DatasetProfile


def analyze(args):
    try:
        profile = DatasetProfile(**json.loads(args.profile.read_text())) if args.profile else DatasetProfile()
        config = QualityConfig(**json.loads(args.quality_config.read_text())) if args.quality_config else QualityConfig()
    except TypeError as error:
        raise ValueError('profile and quality configuration must be JSON objects with supported fields') from error
    outputs = [(args.output_prefix.with_name(args.output_prefix.name + suffix), exporter)
               for suffix, exporter in [('.json', export_recording_json), ('.csv', export_annotated_csv),
                                        ('.diagnostics.json', export_diagnostic_summary)]]
    if any(path.exists() for path, _ in outputs):
        raise ValueError('an analysis output already exists; choose a new output prefix')
    recording = load_xlsx(args.input, profile=profile, sheet=args.sheet, max_rows=args.max_rows)
    validate_recording(recording, config)
    calculate_power(recording)
    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    for path, exporter in outputs:
        with path.open('x', encoding='utf-8', newline='') as stream:
            exporter(recording, stream)
    print(json.dumps(quality_summary(recording)))
    return 0
