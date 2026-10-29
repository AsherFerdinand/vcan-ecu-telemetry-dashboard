"""CLI entry points; CAN transports are confined to live communication commands."""
import argparse
import json
from pathlib import Path
import sys
from can import CanError
from .telemetry import validate_series
from .io import export_csv, export_json, load_candump, load_csv, load_json


def positive_int(value):
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError('must be positive')
    return result


def save(samples, path):
    exporter = {'.json': export_json, '.csv': export_csv}.get(path.suffix.lower())
    if exporter is None:
        raise ValueError('output extension must be .json or .csv')
    samples = validate_series(samples)
    # Validate before touching an output; refuse to overwrite existing datasets.
    with path.open('x', encoding='utf-8', newline='') as stream:
        exporter(samples, stream)


def demo(steps):
    """Bounded end-to-end communication using two real python-can virtual buses."""
    import uuid
    import can
    from .simulator import simulate
    from .receiver import receive
    channel = f'can-lab-{uuid.uuid4()}'
    with can.Bus(interface='virtual', channel=channel) as receiver:
        with can.Bus(interface='virtual', channel=channel) as sender:
            simulate(sender, steps=steps)
            return list(receive(receiver, count=steps * 2))


def main(argv=None):
    parser = argparse.ArgumentParser(description='Automotive CAN & Telemetry Laboratory')
    commands = parser.add_subparsers(dest='command', required=True)
    demo_parser = commands.add_parser('demo', help='bounded in-process virtual CAN communication')
    demo_parser.add_argument('--steps', type=positive_int, default=100)
    demo_parser.add_argument('--output', type=Path)
    importer = commands.add_parser('import', help='normalize recorded or synthetic telemetry')
    importer.add_argument('input', type=Path)
    importer.add_argument('--format', choices=['csv', 'json', 'candump'], required=True)
    importer.add_argument('--output', type=Path, required=True)
    importer.add_argument('--time-basis', choices=['relative', 'unix'])
    importer.add_argument('--source')
    importer.add_argument('--profile', type=Path, help='JSON object with columns and units mappings')
    importer.add_argument('--max-gap-s', type=float)
    workbook = commands.add_parser('analyze-xlsx', help='quality-annotated decoded EV workbook analysis')
    workbook.add_argument('input', type=Path)
    workbook.add_argument('--profile', type=Path)
    workbook.add_argument('--quality-config', type=Path)
    workbook.add_argument('--sheet')
    workbook.add_argument('--max-rows', type=positive_int, default=250000)
    workbook.add_argument('--output-prefix', type=Path, required=True)
    for name in ('simulate', 'receive'):
        command = commands.add_parser(name)
        command.add_argument('--interface', default='socketcan', choices=['socketcan'])
        command.add_argument('--channel', default='vcan0')
        if name == 'simulate':
            command.add_argument('--steps', type=positive_int)
        else:
            command.add_argument('--count', type=positive_int)
            command.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'analyze-xlsx':
            from .workbook_cli import analyze
            return analyze(args)
        if args.command == 'demo':
            samples = demo(args.steps)
        elif args.command == 'import':
            options = {'max_gap_s': args.max_gap_s}
            if args.time_basis:
                options['time_basis'] = args.time_basis
            if args.source:
                options['source'] = args.source
            if args.profile:
                if args.format == 'candump':
                    raise ValueError('column profiles do not apply to CAN logs')
                profile = json.loads(args.profile.read_text())
                if not isinstance(profile, dict) or set(profile) - {'columns', 'units'}:
                    raise ValueError('profile must contain only columns and/or units')
                options.update(profile)
            loader = {'csv': load_csv, 'json': load_json, 'candump': load_candump}[args.format]
            with args.input.open(encoding='utf-8-sig', newline='') as stream:
                samples = loader(stream, **options)
        else:
            import can
            from .simulator import simulate
            from .receiver import receive
            with can.Bus(interface=args.interface, channel=args.channel) as bus:
                if args.command == 'simulate':
                    simulate(bus, steps=args.steps)
                    return 0
                if args.output and args.count is None:
                    raise ValueError('--output requires bounded --count')
                if args.output:
                    samples = list(receive(bus, count=args.count))
                else:
                    for sample in receive(bus, count=args.count):
                        print(json.dumps(sample.to_dict()), flush=True)
                    return 0
        if args.output:
            save(samples, args.output)
        print(f'Processed {len(samples)} samples; {sum(bool(s.quality_flags) for s in samples)} flagged.')
        return 0
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, TimeoutError, CanError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
