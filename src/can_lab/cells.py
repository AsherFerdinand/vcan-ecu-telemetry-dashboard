"""Cell-extrema measurements and screening hints, never confirmed battery defects."""
from dataclasses import dataclass
from .engineering_common import boundary_indices, finite, interval_reason


@dataclass
class CellConfig:
    max_voltage_spread_v: float = 0.25
    max_temperature_spread_c: float = 20.0
    max_voltage_spread_rate_v_s: float = 0.1
    max_temperature_rate_c_s: float = 5.0
    max_trend_interval_s: float = 30.0

    def __post_init__(self):
        if any(not finite(v) or v <= 0 for v in vars(self).values()):
            raise ValueError('cell screening thresholds must be finite and positive')


@dataclass(slots=True)
class CellPoint:
    row_number: int
    voltage_spread_v: float | None
    temperature_spread_c: float | None
    max_temperature_rate_c_s: float | None
    min_temperature_rate_c_s: float | None
    voltage_quality: tuple[str, ...]
    temperature_quality: tuple[str, ...]


def _input_flags(row, signals):
    return [f"input:{signal}:{issue['status']}:{issue['reason']}"
            for signal in signals for issue in row.quality.get(signal, [])]


def analyze_cells(recording, config=None):
    config = config or CellConfig()
    boundaries = boundary_indices(recording)
    rows = recording.observations
    result = []
    previous_spread = None
    for i,row in enumerate(rows):
        voltages = [row.values.get(name) for name in ('cell_voltage_max_v','cell_voltage_min_v')]
        temperatures = [row.values.get(name) for name in ('cell_temperature_max_c','cell_temperature_min_c')]
        voltage_flags = _input_flags(row, ('cell_voltage_max_v','cell_voltage_min_v'))
        temperature_flags = _input_flags(row, ('cell_temperature_max_c','cell_temperature_min_c'))
        v_spread = voltages[0]-voltages[1] if all(finite(v) for v in voltages) else None
        t_spread = temperatures[0]-temperatures[1] if all(finite(v) for v in temperatures) else None
        if v_spread is None:
            voltage_flags.append('missing_or_unverified_normalized_inputs')
        elif v_spread < 0:
            voltage_flags.append('negative_voltage_spread')
        elif v_spread > config.max_voltage_spread_v:
            voltage_flags.append('voltage_spread_exceeds_screening_threshold')
        if any(v == 0 for v in voltages):
            voltage_flags.append('zero_cell_voltage')
        if t_spread is None:
            temperature_flags.append('missing_or_unverified_normalized_inputs')
        elif t_spread < 0:
            temperature_flags.append('negative_temperature_spread')
        elif t_spread > config.max_temperature_spread_c:
            temperature_flags.append('temperature_spread_exceeds_screening_threshold')
        if any(v == -40 for v in temperatures):
            temperature_flags.append('possible_minus40_temperature_sentinel')
        rates = [None,None]
        if i and interval_reason(rows[i-1],row,i,boundaries,config.max_trend_interval_s) is None:
            dt = row.timestamp_s-rows[i-1].timestamp_s
            if v_spread is not None and previous_spread is not None and abs(v_spread-previous_spread)/dt > config.max_voltage_spread_rate_v_s:
                voltage_flags.append('abrupt_voltage_spread_change')
            for j,name in enumerate(('cell_temperature_max_c','cell_temperature_min_c')):
                before,after=rows[i-1].values.get(name),row.values.get(name)
                if finite(before) and finite(after):
                    rates[j]=(after-before)/dt
                    if abs(rates[j])>config.max_temperature_rate_c_s:
                        temperature_flags.append(f'abrupt_temperature_change:{name}')
                    # The previous endpoint's anomaly also taints a derivative.
                    temperature_flags.extend(f"previous_input:{name}:{issue['status']}:{issue['reason']}" for issue in rows[i-1].quality.get(name, []))
        result.append(CellPoint(row.row_number,v_spread,t_spread,*rates,tuple(voltage_flags),tuple(temperature_flags)))
        previous_spread=v_spread
    return result
