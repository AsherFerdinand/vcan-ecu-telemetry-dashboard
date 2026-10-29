# Automotive CAN & Telemetry Laboratory

Phase 1 and Phase 2 evolution of the existing Virtual CAN Bus ECU Telemetry Simulator.
The original Git history, sine-wave ECU model, standard CAN IDs, payload layout,
and `can_project/` entry points are preserved.

## Capabilities and boundaries

| Area | Original project | Phase 1 |
| --- | --- | --- |
| ECU | Synthetic RPM, speed, battery temperature at 100 Hz | Same model and two 8-byte frames; modular generator |
| Transport | Linux SocketCAN `vcan0` | SocketCAN retained; bounded in-process virtual-bus demo for portable development |
| Decoding | Hardcoded byte slices | Packaged `cantools` DBC verified against independent byte vectors |
| Data | Console output | CSV/JSON normalization and classical `candump -L` import; JSON/CSV export |
| Validation | Manual inspection | Explicit time bases, units, optional signals, quality flags, pytest, CI |
| Visualization | Terminal receiver | Optional Streamlit upload, plots, quality table, exports |

**All bundled fixtures and the DBC are synthetic.** No Volkswagen ID.3 or Porsche
Taycan signal definitions have been verified or implemented. Research access was
blocked in this environment; see [dataset investigation](docs/datasets.md).
The demo proves application communication using python-can's virtual transport;
it does not prove kernel SocketCAN support.

## Phase 2: real-world decoded telemetry and diagnostics

Select **Real-World EV Dataset** in the existing dashboard to upload `.xlsx`
measurements such as `vehicle#1.xlsx`. The new workflow preserves raw timestamps,
original source columns, dataset ID, declared units, file SHA-256, recording order,
and suspicious measurements. It adds configurable data-quality checks, vehicle
dynamics inspection, cell-temperature plots, signed battery power, and
play/pause/reset replay without CAN hardware or invented CAN identifiers.

**The actual workbook and its signal documentation were not available.** Support
is implemented against the supplied schema and synthetic tests. Source units,
charging-status codes and current polarity default to unverified. Numeric raw
values remain inspectable; normalization requires explicit unit declarations.
Signed power is `V × I / 1000` only when input units/values permit it. Unknown
polarity never receives charging/discharging labels. No energy/efficiency or
battery-health estimate is fabricated.

Generate and analyze a clearly synthetic workbook:

```bash
python examples/make_ev_fixture.py /tmp/synthetic-ev.xlsx
can-lab analyze-xlsx /tmp/synthetic-ev.xlsx \
  --profile /tmp/synthetic-ev.profile.json --output-prefix outputs/synthetic-ev
```

For `vehicle#1.xlsx`, select **Real-World EV Dataset**, upload your local file,
and configure the correct worksheet, dataset ID, time representation, source
units and optional documented current convention under **Source profile and
quality thresholds**. A profile JSON can supply those declarations. Do not reuse
the synthetic profile as evidence of real dataset units. Missing columns and
invalid values stay visible with quality flags; duplicate/reversed/irregular time,
SOC limits, voltage problems, possible -40 degC sentinels, discontinuities and
flatlines are diagnosed without deleting rows. Unknown/unordered time blocks timed
replay while diagnostics and exports remain available.

Download provenance-rich recording JSON, quality-annotated CSV and diagnostic
JSON from **Exports & Source**. CSV begins with a metadata comment; it is distinct
from Phase 1 canonical CSV. See [the Phase 2 technical guide](docs/real_world_telemetry.md)
for mapping, threshold definitions, replay semantics, export formats, source and
attribution verification requirements, resource limits and reproducible analysis.
No research dataset is committed or required at startup.

## Reproducible installation

Use **Python 3.12** for the tested, pinned development environment. From the
repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install --no-build-isolation --no-deps -e .
python -m pip check
python -m pytest -ra
```

`requirements-lock.txt` pins the tested development and UI dependencies,
including build tools and pandas/openpyxl Excel support, for Python 3.12. It is a version lock, not an artifact hash
lock. For a smaller runtime installation without tests/UI, use
`python -m pip install .`; for flexible development resolution use
`python -m pip install -e '.[dev,ui]'` (UI includes Excel support);
`python -m pip install -e '.[excel]'` installs only the workbook extra. These alternatives are not locked.
No application credentials or external services are required.

## Portable ECU communication

```bash
mkdir -p outputs
can-lab demo --steps 100 --output outputs/demo.json
```

This creates separate sender and receiver bus instances on a private in-process
virtual channel, sends both original frame types, decodes via the DBC, and
exports 200 sparse telemetry observations. It terminates and releases both buses.
It works without root or a CAN-capable kernel. python-can `virtual` buses do
**not** communicate between independent processes; use SocketCAN below for that.
Output commands refuse to overwrite existing files; select a new output path
for repeated runs.

## Linux SocketCAN workflow

Requires a Linux kernel with CAN_RAW/vcan support, `iproute2`, `kmod`, and network
administration privileges. In an appropriately privileged host/container:

```bash
sudo modprobe vcan
# Create only if vcan0 does not already exist:
sudo ip link add dev vcan0 type vcan
sudo ip link set dev vcan0 up
```

From the repository root, with the installed environment active, use two terminals:

```bash
# Terminal 1: prints decoded schema samples; waits up to 5 seconds per frame
can-lab receive --channel vcan0
# Terminal 2: original 100 Hz synthetic ECU
can-lab simulate --channel vcan0
```

Start the sender promptly, or start it before the receiver. Ctrl+C stops either
process. For bounded capture: `can-lab receive --count 200 --output outputs/live.json`.
The original commands also remain available after installation:
`python can_project/ecu_simulator.py` and
`python can_project/dashboard_receiver.py`. Bus failures now exit nonzero.
Do not connect this synthetic transmitter to a physical vehicle network.

The onboarding host lacks CAN socket support and CAP_NET_ADMIN, so native
SocketCAN execution could not be validated here. That is a host limitation.

## Import, transform and export

```bash
can-lab import tests/fixtures/synthetic.csv --format csv --output outputs/normalized.json
can-lab import tests/fixtures/synthetic.json --format json --output outputs/normalized.csv
can-lab import tests/fixtures/synthetic.log --format candump --output outputs/can.json
can-lab import tests/fixtures/mapped.csv --format csv \
  --profile tests/fixtures/profile.json --source synthetic-mapped-fixture \
  --time-basis relative --max-gap-s 2 --output outputs/converted.json
```

CSV uses a header and one sample per row; JSON uses an array of sample objects.
Canonical field names/units are accepted directly. A profile explicitly maps
source column names to schema names and specifies input units; it selects only
those columns. Without a profile, unknown fields fail rather than being silently
dropped. No units, current polarity, timestamp basis, or vehicle identity are
inferred. Profiles must reflect the recording's documentation.

The raw log importer accepts **classical data-frame `candump -L`** lines such as
`(1700000000.000000) vcan0 100#09C4410000000000`. It decodes only the bundled
synthetic protocol, rejects unknown IDs, malformed frames, FD/RTR/error/extended
frames, and mixed channels. It is not a general vehicle log decoder. Select an
appropriate `--time-basis` if the log contains relative timestamps; the candump
default is Unix, CSV/JSON default is relative unless per-row metadata is present.
Per-row metadata takes precedence over defaults.

See [schema and architecture](docs/architecture.md) for API examples, units,
validation policy and extension boundaries. Missing signals remain `null` in JSON
and blank in CSV. Export preserves timestamps, source, flags and time basis.
These commands load their input into memory; they target research-size recordings,
not unlimited-duration captures.

## Telemetry visualization

With UI dependencies installed:

```bash
python -m streamlit run src/can_lab/dashboard.py --server.address 127.0.0.1 \
  --server.headless true --browser.gatherUsageStats false
```

Use the local Streamlit interface on a machine where you can access its port.
Choose Virtual ECU Simulation to generate a sample or upload
`tests/fixtures/synthetic.csv` / canonical JSON/CSV exports. Choose Imported CAN Log for a supported
synthetic `.log` file. Choose the recording's time basis, inspect flags, select
signals for separate unit-specific plots, and download standardized JSON/CSV.
Plots connect observed points without filling missing fields; they are not a
synchronized vehicle-state estimate. Vehicle-specific CSV/JSON tables must first be
normalized with an explicit CLI profile. Excel workbooks have the separate
Real-World EV Dataset workflow described above. This UI is for local development;
authentication and remote deployment are outside this phase.

## Validation and next steps

`python -m pytest -ra` covers independent known CAN vectors, original synthetic
signals, malformed frames, real virtual-bus transmission/reception, import errors,
unit/polarity conversions, timestamp ordering, optional signals, quality flags,
export round trips, CLI behavior and Streamlit rendering with a synthetic upload.
GitHub Actions runs the suite and a bounded demo on Python 3.12 without root.

Next: obtain a licensed, documented vehicle recording and signal dictionary;
validate its mapping and current polarity against reference values; then add an
adapter and recorded golden tests. Validate SocketCAN on a capable Linux host.
Future VEUS and EV Battery Health ML projects can consume `TelemetrySample` or
its exports without coupling to CAN or vehicle file formats. Neither downstream
application is implemented here.

See [repository audit](docs/repository-audit.md) for removed environment files and
historical exposure limitations.
