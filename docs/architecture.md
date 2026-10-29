# Schema and architecture

```text
Synthetic ECU -> python-can bus -> synthetic DBC codec --+
Classical candump log -> synthetic DBC codec -----------+-> TelemetrySample v1
CSV/JSON -> explicit column/unit normalization ---------+     |
                                                  validation
                                                      |
                                                JSON / CSV / UI
                                                      |
                                            future independent consumers
```

`telemetry.py` uses only the Python standard library. `io.py` imports CAN tools
only inside the raw-log loader. Consumers may import schema and table importers
without opening a bus. `codec.py` is deliberately specific to the original
synthetic protocol; a real vehicle requires its own verified DBC and mapping into
the common schema. `simulator.py` owns the original signal model; `receiver.py`
turns frames into sparse observations; `cli.py` owns transport lifetimes.

## Schema v1

| Field | Unit / meaning |
| --- | --- |
| `schema_version` | Integer 1 |
| `timestamp_s` | Required finite nonnegative seconds |
| `time_basis` | `relative` (one session's origin) or `unix` (UTC epoch seconds) |
| `source` | Nonempty provenance string; default `recorded-unspecified` for table imports |
| `speed_kmh` | km/h |
| `rpm` | Revolutions/minute; original synthetic engine signal, not an inferred EV motor signal |
| `battery_voltage_v` | Pack voltage, V |
| `battery_current_a` | Pack current, A; **positive discharge, negative charge/regen** |
| `soc_pct` | Percent, 0–100 |
| `battery_temperature_c` | Battery temperature, degrees Celsius |
| `ambient_temperature_c` | Ambient temperature, degrees Celsius |
| `power_kw` | Battery power, kW; positive discharge |
| `odometer_km` | km |
| `quality_flags` | List of strings; recomputed bounds flags plus preserved input flags |

Every signal is optional. A CAN engine observation has RPM/speed and no battery
values; a battery observation has temperature and no RPM/speed. No automatic
joining, resampling, differentiation, power calculation or forward filling is
performed. Do not treat nearby frame timestamps as simultaneous measurements.
An EV recording need not have RPM. Voltage, current and SOC in the bundled table
fixture are explicitly invented; they are not present in the original CAN frames.

Series timestamps must be nondecreasing and use one time basis. Equal timestamps
are allowed for independent observations. Clock reversals fail; no automatic
sorting or clock-reset correction hides recording problems. A relative session
cannot be joined to another solely on its numeric timestamps. Optional
`max_gap_s` flags gaps on the later observation. Absolute dates are not guessed
from timestamp magnitude. Strings/datetimes, timezones and clock synchronisation
require an explicit upstream adapter.

NaN, infinity, booleans and nonnumeric signals fail. Broad plausibility bounds
(e.g. SOC 0–100%, pack temperature -50–100 degC, pack voltage 0–1500 V) flag values
without silently clamping/dropping them. These are research screening heuristics,
not vehicle safety limits or sensor-validity claims. An observation without
signals is flagged `no_signals`. Input quality flags are retained, not trusted as
proof of correctness. Missing flags do not establish sensor calibration/accuracy.

## Unit normalization

Canonical input units are explicit in field names and the table above. Profiles
support milliseconds to seconds, m/s or mph to km/h, SOC fraction to percent,
mV to V, mA to A, Kelvin to Celsius, W to kW, and metres to km.
`A_charge_positive` reverses current polarity into positive discharge.
Profiles are JSON objects with `columns` (source -> canonical name) and/or `units`
(canonical name -> input unit). Unsupported conversions fail, including units
specified for a fully missing signal. No heuristic alias or magnitude detection
is used. Profile authors must establish signal meaning and polarity independently.

## Python API

```python
from can_lab.io import load_csv, export_json

with open('tests/fixtures/synthetic.csv', newline='') as recording:
    samples = load_csv(recording, max_gap_s=2)

with open('/tmp/telemetry.json', 'w') as destination:
    export_json(samples, destination)

# Downstream applications need only this standard-library module:
from can_lab.telemetry import TelemetrySample
sample = TelemetrySample(timestamp_s=0, speed_kmh=36, source='synthetic-example')
assert sample.soc_pct is None
```

## Verified synthetic DBC

`0x100` is standard ID 256, DLC 8. RPM is unsigned 16-bit big-endian in bytes
0–1 (DBC Motorola start bit 7, length 16). Speed is unsigned byte 2, km/h.
`0x200` is standard ID 512, DLC 8; temperature is unsigned byte 0, degC.
Other bytes are zero padding from the original sender. Scaling is 1 and offset 0.

Independent test vector `0BB8480000000000` means 3000 rpm, 72 km/h;
`2100000000000000` means 33 degC. Tests check exact encoded bytes as well as
decoding, so a symmetric encode/decode mistake cannot alone pass verification.
These definitions come from the original repository code, not an OEM DBC.
Unsigned temperature is intentional compatibility with that synthetic protocol.
