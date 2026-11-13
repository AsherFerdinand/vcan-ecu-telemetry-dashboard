import can
import pytest
from can_lab.cli import demo, main
from can_lab.io import load_json
from can_lab.receiver import receive
from can_lab.simulator import simulate


def test_virtual_ecu_communication():
    samples = demo(20)
    assert len(samples) == 40
    engines = [sample for sample in samples if sample.rpm is not None]
    batteries = [sample for sample in samples if sample.battery_temperature_c is not None]
    assert len(engines) == len(batteries) == 20
    assert (engines[0].rpm, engines[0].speed_kmh, batteries[0].battery_temperature_c) == (2500, 65, 32)
    assert len({sample.rpm for sample in engines}) > 1
    assert all(sample.time_basis == 'unix' and not sample.quality_flags for sample in samples)
    assert all(a.timestamp_s <= b.timestamp_s for a, b in zip(samples, samples[1:]))


def test_receive_timeout():
    with can.Bus(interface='virtual', channel='test-timeout') as bus:
        with pytest.raises(TimeoutError):
            list(receive(bus, count=1, timeout_s=.001))


@pytest.mark.parametrize('options', [{'steps': 0}, {'period_s': 0}, {'period_s': float('nan')}])
def test_bad_simulation_options(options):
    with pytest.raises(ValueError):
        simulate(None, **options)


def test_cli_pipeline_and_no_overwrite(tmp_path):
    output = tmp_path / 'demo.json'
    assert main(['demo', '--steps', '2', '--output', str(output)]) == 0
    with output.open() as stream:
        assert len(load_json(stream)) == 4
    before = output.read_bytes()
    assert main(['demo', '--steps', '1', '--output', str(output)]) == 1
    assert output.read_bytes() == before
    csv = tmp_path / 'telemetry.csv'
    assert main(['import', str(output), '--format', 'json', '--output', str(csv)]) == 0
    assert csv.read_text().startswith('timestamp_s,')


def test_cli_invalid_import(tmp_path):
    input_file = tmp_path / 'bad.csv'
    input_file.write_text('timestamp_s,speed_kmh\n1,0\n0,1')
    output = tmp_path / 'output.json'
    assert main(['import', str(input_file), '--format', 'csv', '--output', str(output)]) == 1
    assert not output.exists()
