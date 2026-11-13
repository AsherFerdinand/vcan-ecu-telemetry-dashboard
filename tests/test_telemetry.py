import pytest
from can_lab.telemetry import TelemetrySample, convert, validate_series


@pytest.mark.parametrize('kwargs', [
    {'timestamp_s': -1}, {'timestamp_s': float('nan')}, {'timestamp_s': True},
    {'speed_kmh': float('inf')}, {'rpm': 'bad'}, {'time_basis': 'unknown'},
    {'schema_version': 2}, {'schema_version': True}, {'source': ''},
    {'quality_flags': 'bad'}, {'quality_flags': [1]},
])
def test_invalid_sample(kwargs):
    params = {'timestamp_s': 0}
    params.update(kwargs)
    with pytest.raises(ValueError):
        TelemetrySample(**params)


def test_optional_and_quality():
    sample = TelemetrySample(0, soc_pct=101, battery_current_a=-10)
    assert sample.rpm is None and sample.speed_kmh is None
    assert sample.quality_flags == ['out_of_range:soc_pct']
    assert TelemetrySample(0).quality_flags == ['no_signals']


def test_timestamp_policy():
    assert len(validate_series([TelemetrySample(0), TelemetrySample(0)])) == 2
    with pytest.raises(ValueError, match='nondecreasing'):
        validate_series([TelemetrySample(1), TelemetrySample(0)])
    with pytest.raises(ValueError, match='mixed'):
        validate_series([TelemetrySample(0), TelemetrySample(1, time_basis='unix')])
    samples = validate_series([TelemetrySample(0), TelemetrySample(2)], max_gap_s=1)
    assert 'timestamp_gap' in samples[1].quality_flags
    assert 'timestamp_gap' not in samples[0].quality_flags


@pytest.mark.parametrize('gap', [0, -1, float('inf'), float('nan')])
def test_invalid_gap(gap):
    with pytest.raises(ValueError):
        validate_series([], max_gap_s=gap)


@pytest.mark.parametrize('field,unit,value,expected', [
    ('timestamp_s', 'ms', 1000, 1), ('speed_kmh', 'm/s', 10, 36),
    ('speed_kmh', 'mph', 10, 16.09344), ('soc_pct', 'fraction', .8, 80),
    ('battery_voltage_v', 'mV', 400000, 400), ('battery_current_a', 'mA', 1000, 1),
    ('battery_current_a', 'A_charge_positive', -20, 20),
    ('battery_temperature_c', 'K', 298.15, 25), ('ambient_temperature_c', 'K', 273.15, 0),
    ('power_kw', 'W', 1000, 1), ('odometer_km', 'm', 1000, 1),
])
def test_units(field, unit, value, expected):
    assert convert(value, field, unit) == pytest.approx(expected)


def test_wrong_units_fail():
    with pytest.raises(ValueError):
        convert(1, 'rpm', 'mph')
