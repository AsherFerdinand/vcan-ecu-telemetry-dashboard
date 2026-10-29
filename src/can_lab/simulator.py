"""Original sine-wave ECU model; no recorded vehicle data is needed."""
import math
import time
from .codec import SyntheticCodec


def synthetic_signals(step):
    return {
        'rpm': int(1000 + 3000 * (0.5 + 0.5 * math.sin(step * 0.05))),
        'speed_kmh': int(30 + 70 * (0.5 + 0.5 * math.sin(step * 0.02))),
        'battery_temperature_c': int(25 + 15 * (0.5 + 0.5 * math.sin(step * 0.01))),
    }


def frames(step, codec=None):
    codec = codec or SyntheticCodec()
    values = synthetic_signals(step)
    return (
        codec.encode('EngineData', {key: values[key] for key in ('rpm', 'speed_kmh')}),
        codec.encode('BatteryData', {'battery_temperature_c': values['battery_temperature_c']}),
    )


def simulate(bus, *, steps=None, period_s=0.01):
    if steps is not None and steps < 1:
        raise ValueError('steps must be positive')
    if not math.isfinite(period_s) or period_s <= 0:
        raise ValueError('period_s must be finite and positive')
    codec = SyntheticCodec()
    step = 0
    deadline = time.monotonic()
    while steps is None or step < steps:
        for message in frames(step, codec):
            bus.send(message)
        step += 1
        deadline += period_s
        time.sleep(max(0, deadline - time.monotonic()))
