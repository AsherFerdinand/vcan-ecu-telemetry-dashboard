"""Quality-aware calculations; no energy or efficiency inference."""
import math


def calculate_power(recording):
    convention = recording.metadata['profile']['current_convention']
    definition = {
        'formula': 'battery_voltage_v * battery_current_measured_a / 1000',
        'unit': 'kW', 'current_convention': convention,
        'sign_interpretation': 'unverified; no charging/discharging assertion' if convention == 'unknown' else convention,
        'input_alignment': 'voltage and current from the same original observation only',
        'invalid_policy': 'missing, nonnumeric, OUT_OF_RANGE, or unverified-unit inputs yield null; other suspect inputs retained and flagged',
    }
    recording.metadata['derived_signals'] = {'signed_power_kw': definition}
    for row in recording.observations:
        quality = []
        for signal in ('battery_voltage_v', 'battery_current_measured_a'):
            quality.extend(dict(issue, input_signal=signal) for issue in row.quality.get(signal, []))
        voltage = row.values.get('battery_voltage_v')
        current = row.values.get('battery_current_measured_a')
        invalid = voltage is None or current is None or any(item['status'] in ('MISSING', 'OUT_OF_RANGE') or item['reason'] == 'unit_unverified' for item in quality)
        value = None if invalid else voltage * current / 1000
        if value is not None and not math.isfinite(value):
            value = None
            quality.append({'status': 'OUT_OF_RANGE', 'reason': 'nonfinite_calculated_power'})
        if convention == 'unknown':
            quality.append({'status': 'SUSPECT', 'reason': 'current_polarity_unverified'})
        row.derived['signed_power_kw'] = {'value': value, 'unit': 'kW', 'quality': quality or [{'status': 'VALID', 'reason': 'inputs_pass_configured_checks'}]}
    return recording


def iter_vehicle_dynamics(recording, stationary_speed_kmh=0.5):
    """Backward difference; invalid/suspect endpoints or clock anomalies yield null."""
    if not math.isfinite(stationary_speed_kmh) or stationary_speed_kmh < 0:
        raise ValueError('stationary threshold must be finite and nonnegative')
    previous = None
    for row in recording.observations:
        speed = row.values.get('speed_kmh')
        usable = speed is not None and row.statuses('speed_kmh') == {'VALID'}
        acceleration = None
        if previous is not None and usable and previous.statuses('speed_kmh') == {'VALID'}:
            before = previous.values.get('speed_kmh')
            if before is not None and previous.timestamp_s is not None and row.timestamp_s is not None:
                dt = row.timestamp_s - previous.timestamp_s
                if dt > 0 and row.statuses('timestamp_s') == previous.statuses('timestamp_s') == {'VALID'}:
                    acceleration = (speed - before) / 3.6 / dt
        yield {'row_number': row.row_number, 'timestamp_s': row.timestamp_s,
               'acceleration_m_s2': acceleration,
               'stationary': abs(speed) <= stationary_speed_kmh if usable else None}
        previous = row


def vehicle_dynamics(recording, stationary_speed_kmh=0.5):
    return list(iter_vehicle_dynamics(recording, stationary_speed_kmh))
