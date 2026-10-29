# Virtual ECU & CAN Lab — Automotive Telemetry, Diagnostics & Test Automation

v0.3: Phase 1, Phase 2 and Phase 3 evolution of the existing Virtual CAN Bus ECU Telemetry Simulator.
The original Git history, sine-wave ECU model, standard CAN IDs, payload layout,
and `can_project/` entry points are preserved.

## Two operating modes

**Virtual CAN Laboratory** retains the original synthetic ECU model, python-can
communication, SocketCAN workflow, verified synthetic DBC and portable virtual demo.

**Real-World EV Diagnostics** imports already decoded telemetry. It now adds
candidate operating states, signed power/energy with explicit coverage, cell
spreads and sensor-screening indicators, possible sessions and engineering reports.
Excel measurements are never presented as authentic OEM CAN frames.

```text
Synthetic ECU -> CAN transport -> synthetic DBC -> canonical telemetry
Decoded recordings -> provenance + quality -> engineering analysis -> UI / reports
```

The [v0.3 engineering guide](docs/engineering_v0.3.md) documents architecture,
math, defaults, file responsibilities, dashboard views and reproduction steps.
The [validation record](docs/validation.md) contains executed tests and full SCUT
workbook results. No SOH/ML model, confirmed battery-defect classifier or verified
vehicle-efficiency claim is included.

## v0.3 engineering workflow

With the pinned environment below installed:

```bash
python examples/make_ev_fixture.py /tmp/synthetic-v03.xlsx
can-lab report-xlsx /tmp/synthetic-v03.xlsx \
  --profile /tmp/synthetic-v03.profile.json \
  --engineering-config examples/engineering_config.json \
  --output-prefix outputs/synthetic-v03 --include-features
```

Reports include provenance, measurement coverage, candidate dynamics, electrical
relationships, signed-energy coverage, cell diagnostics, possible-session
statistics and limitations. JSON is machine-readable, Markdown is human-readable,
and optional CSV contains annotated engineering features. Existing recording
exports remain available. No PDF or additional plotting dependency is required.

The real-world dashboard offers Overview, Vehicle Dynamics, Battery Electrical,
Battery Health Indicators, Session Explorer, Diagnostics, Recorded Replay, and
source exports. Shared time/session selection controls synchronized telemetry;
replay also shows current operating candidates, power and temperature.

Energy is integrated only over usable adjacent intervals within a configurable
maximum (30 s by default), never across detected boundaries. Positive/negative
signed components are not charging/discharging labels. Regeneration candidates
require a dedicated current-polarity reference, not just negative current. Session
SOC change remains in raw source units when its percentage scale is unknown.
Distance-qualified signed kWh/km is withheld when interval coverage does not match
and is never presented as verified efficiency. Thresholds are research screening
heuristics, not OEM specifications.

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

The public `vehicle#1.xlsx` has now been checked across all **81,898** rows.
Its source README documents most units and charging codes, but not the year,
timezone, current polarity, SOC scale or exact timestamp encoding. The configurable
`MDDHHMMSS` interpretation fits every calendar value and the supplied minute
rollover; it remains explicitly **inferred** and never invents a year. See the
[full source review](docs/validation.md#public-vehicle1-source-review-and-qualityvisualization-correction).

In the dashboard, enable **Use source-reviewed SCUT profile (timestamp encoding
remains inferred)** for this specific public workbook. It provides elapsed time,
source-documented units/status labels, and 10-second cadence screening. SOC units
and current polarity remain unknown. Without this explicit selection, numeric
raw timestamps retain the unverified-time fallback. Physical, metadata, time and
missing-data counts are independent; legacy conservative flags remain available.
Shared interval/possible-segment controls synchronize plots and break lines at
possible recording boundaries. Yearless calendar parsing is not a Unix decoder.

Signed power is `V × I / 1000` only when input units/values permit it. Unknown
polarity never receives charging/discharging sign labels. No verified-efficiency or battery-health estimate is asserted; v0.3 adds qualified signed energy over accepted intervals.

Generate and analyze a clearly synthetic workbook:

```bash
python examples/make_ev_fixture.py /tmp/synthetic-ev.xlsx
can-lab analyze-xlsx /tmp/synthetic-ev.xlsx \
  --profile /tmp/synthetic-ev.profile.json --output-prefix outputs/synthetic-ev
```

For a compatible local `vehicle#1.xlsx`, select **Real-World EV Dataset**, upload your local file,
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
