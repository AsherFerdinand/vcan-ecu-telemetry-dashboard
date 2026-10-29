import io
import json
from pathlib import Path
import pytest
from can_lab.io import load_csv, load_json, load_candump, export_json, export_csv

FIXTURES = Path(__file__).parent / 'fixtures'


@pytest.mark.parametrize('filename,loader,count', [
    ('synthetic.csv', load_csv, 4), ('synthetic.json', load_json, 2),
    ('synthetic.log', load_candump, 4),
])
def test_fixtures(filename, loader, count):
    with (FIXTURES / filename).open() as stream:
        samples = loader(stream)
    assert len(samples) == count
    assert all('synthetic' in sample.source for sample in samples)
    if filename == 'synthetic.csv':
        assert samples[1].battery_voltage_v == 398
    else:
        assert all(sample.battery_voltage_v is None for sample in samples)


def test_mapping_and_conversions():
    profile = json.loads((FIXTURES / 'profile.json').read_text())
    with (FIXTURES / 'mapped.csv').open() as stream:
        samples = load_csv(stream, **profile)
    assert samples[1].timestamp_s == 1
    assert samples[0].speed_kmh == 36
    assert samples[0].soc_pct == 80
    assert samples[0].battery_current_a == 20
    assert samples[0].battery_temperature_c == pytest.approx(25)


@pytest.mark.parametrize('exporter,loader', [(export_json, load_json), (export_csv, load_csv)])
def test_export_round_trip(exporter, loader):
    samples = load_csv(io.StringIO('timestamp_s,speed_kmh,soc_pct\n0,36,101\n1,,80\n'))
    output = io.StringIO()
    exporter(samples, output)
    restored = loader(io.StringIO(output.getvalue()))
    assert [sample.to_dict() for sample in restored] == [sample.to_dict() for sample in samples]
    assert restored[1].speed_kmh is None
    assert restored[0].quality_flags == ['out_of_range:soc_pct']


@pytest.mark.parametrize('text', [
    '', 'timestamp_s,timestamp_s\n0,0', ',speed_kmh\n0,1',
    'timestamp_s,speed_kmh\n0,1,2', 'speed_kmh\n1',
    'timestamp_s,speed_kmh\n1,1\n0,2', 'timestamp_s,speed_kmh\n0,nan',
    'timestamp_s,mystery\n0,3', 'timestamp_s,schema_version\n0,2',
])
def test_bad_csv(text):
    with pytest.raises(ValueError):
        load_csv(io.StringIO(text))


@pytest.mark.parametrize('text', ['{}', '[]', '[null]', '[1]', '[{"timestamp_s": true}]', '[{"timestamp_s":0,"quality_flags":1}]'])
def test_bad_json(text):
    with pytest.raises(ValueError):
        load_json(io.StringIO(text))


@pytest.mark.parametrize('options', [
    {'units': []}, {'columns': []}, {'units': {'rpm': []}}, {'columns': {'a': []}},
    {'units': {'speed_kmh': 'unknown'}}, {'units': {'unknown': 's'}},
    {'columns': {'missing': 'timestamp_s'}},
    {'columns': {'a': 'timestamp_s', 'b': 'timestamp_s'}},
    {'columns': {'a': 'unknown'}},
])
def test_bad_profiles(options):
    with pytest.raises(ValueError):
        load_csv(io.StringIO('timestamp_s\n0'), **options)


@pytest.mark.parametrize('line', [
    '(1.0) vcan0 100#123', '(1.0) vcan0 300#0000000000000000',
    '(1.0) vcan0 100##10000000000000000', '(1.0) vcan0 100#R',
    '(1.0) vcan0 00000100#0000000000000000', 'not a frame',
    '(1.0) vcan0 100#00000000000000',
])
def test_bad_candump(line):
    with pytest.raises(ValueError):
        load_candump(io.StringIO(line))


def test_candump_values():
    with (FIXTURES / 'synthetic.log').open() as stream:
        samples = load_candump(stream)
    assert samples[0].rpm == 2500 and samples[0].speed_kmh == 65
    assert samples[1].battery_temperature_c == 32
    assert samples[2].rpm == 3000 and samples[2].speed_kmh == 72
    assert samples[0].time_basis == 'unix'


def test_candump_mixed_channels_and_clock_reversal():
    for lines in [
        '(1) can0 100#0000000000000000\n(2) can1 200#2000000000000000',
        '(2) can0 100#0000000000000000\n(1) can0 200#2000000000000000',
    ]:
        with pytest.raises(ValueError):
            load_candump(io.StringIO(lines))
