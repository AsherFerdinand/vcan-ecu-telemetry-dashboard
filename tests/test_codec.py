import can
from cantools.database.errors import EncodeError
import pytest
from can_lab.codec import SyntheticCodec
from can_lab.simulator import frames, synthetic_signals


@pytest.fixture
def codec():
    return SyntheticCodec()


def test_independent_original_engine_vector(codec):
    # Hand-computed big-endian 0x0BB8 = 3000 rpm; 0x48 = 72 km/h.
    sample = codec.decode(can.Message(timestamp=12, arbitration_id=0x100,
                          data=bytes.fromhex('0BB8480000000000'), is_extended_id=False))
    assert (sample.rpm, sample.speed_kmh, sample.timestamp_s) == (3000, 72, 12)
    assert sample.battery_temperature_c is None
    assert codec.encode('EngineData', {'rpm': 3000, 'speed_kmh': 72}).data.hex() == '0bb8480000000000'


def test_independent_battery_vector(codec):
    sample = codec.decode(can.Message(timestamp=1, arbitration_id=0x200,
                          data=bytes.fromhex('2100000000000000'), is_extended_id=False))
    assert sample.battery_temperature_c == 33
    assert sample.rpm is None


@pytest.mark.parametrize('kwargs', [
    {'arbitration_id': 0x300}, {'is_extended_id': True},
    {'is_remote_frame': True}, {'is_error_frame': True}, {'is_fd': True},
    {'data': bytes(7)}, {'data': bytes(9)}, {'dlc': 7},
])
def test_invalid_frames_rejected(codec, kwargs):
    params = dict(timestamp=0, arbitration_id=0x100, data=bytes(8), is_extended_id=False)
    params.update(kwargs)
    with pytest.raises(ValueError):
        codec.decode(can.Message(**params))


def test_original_generator_preserved(codec):
    engine, battery = frames(0, codec)
    assert engine.data.hex() == '09c4410000000000'  # 2500 rpm, 65 km/h
    assert battery.data.hex() == '2000000000000000'  # 32 degC
    for step in range(1000):
        signals = synthetic_signals(step)
        assert 1000 <= signals['rpm'] <= 4000
        assert 30 <= signals['speed_kmh'] <= 100
        assert 25 <= signals['battery_temperature_c'] <= 40


def test_invalid_encode_rejected(codec):
    with pytest.raises(EncodeError):
        codec.encode('EngineData', {'rpm': 70000, 'speed_kmh': 60})
