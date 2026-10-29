# v0.3 engineering analysis and validation

This release integrates the validated Phase 2 recording pipeline with optional
Phase 3 engineering analysis. It does not replace SocketCAN, the original ECU,
the verified synthetic DBC, schema-v1 importers, recorded-data replay, or raw-cell
preservation. It introduces no new runtime dependencies.

## Architecture

```text
Virtual ECU -> python-can -> synthetic DBC -> canonical telemetry / original UI

Decoded XLSX / recorded tables -> Phase 2 Recording + source profile + quality
                                              |
                         operating candidates / power / cell extrema
                                              |
                   gap-aware signed energy + possible-session summaries
                            /                 |                  \
                  engineering UI       JSON / Markdown        feature CSV
                                              |
                         future VEUS / health research consumers
```

The CAN simulator is synthetic. Imported Excel measurements are already decoded
vehicle telemetry; they are never represented as authentic OEM CAN frames.
Engineering modules use standard-library calculations and accept the existing
`Recording` abstraction. They import neither SocketCAN nor Streamlit/pandas.

## Calculations and evidence policy

### Operating candidates

`operating.py` computes a **causal trailing median** of declared/documented speed.
It then uses the backward derivative of that smoothed speed over actual elapsed
seconds, divided by 3.6 to convert km/h to m/s. During window warm-up it uses the
available partial window; this is a sampled estimate with smoothing delay, not a
high-bandwidth acceleration sensor. History resets at recording boundaries,
unusable speed/time, and intervals above the configured maximum (30 s by default).
Clock irregularities within that maximum are retained as warnings; nominal sample
frequency is never substituted for actual elapsed time.

Default candidates: stationary at speed <= 0.5 km/h; acceleration >= 0.15 m/s²;
deceleration <= -0.15 m/s²; approximately constant speed at |a| <= 0.05 m/s².
Intermediate/noisy motion remains unknown. A stationary point does not require a
derivative. Unusable inputs produce insufficient evidence. Thresholds and the
odd smoothing sample count (default 3) are configurable. These are research
screening choices, not verified vehicle operating limits.

Charging is attached only to explicit status-code labels with a profile source
reference. In the SCUT profile, code 1 means source-reported charging mode and
code 3 means driving mode. A reported mode is distinct from inferred dynamics or
a confirmed physical event. Candidates can overlap (charging and stationary).
Counts are observation counts, not time-weighted percentages.

Possible regeneration requires deceleration, moving speed, usable electrical
measurements, a specified current convention **and a dedicated `current_reference`**.
A negative current alone, or a sign convention without supporting reference, is
not enough. Even with that evidence the result is a candidate, not confirmed
regenerative-brake actuation. The SCUT profile remains unknown-polarity, therefore
its analysis produces no regenerative-braking candidates.

Flatline flags remain visible. A constant quantized speed/current/voltage may be
legitimate, so this heuristic alone does not suppress stationary analysis or
energy. Missing, out-of-range and other suspect physical inputs are excluded from
those calculations. Existing Phase 2 conservative flags are never erased.

### Electrical relationships and response

Signed power is `P_kW = V_pack * I_measured / 1000`, using the same original row.
The original Phase 2 calculator supplies the value and propagated input quality.
Plots/report distributions include quality-annotated numeric power; energy uses
stricter interval screening. Relationships pair screened same-row voltage/current
or voltage/speed. Pearson coefficients are descriptive; undefined/constant-series
correlations remain null. They are not internal-resistance estimates or evidence
of a causal voltage sag.

Candidate acceleration/deceleration events include start/end rows and times,
observed voltage endpoints and descriptive voltage change. Events are bounded by
candidate continuity and derivative resets; they do not cross possible sessions.
A single-observation event contains no independent before/after voltage evidence.

### Signed energy and distance

`energy.py` integrates piecewise-linear power using the trapezoidal rule:

`E_signed_kWh = Σ ((P[i-1] + P[i]) / 2) * dt_seconds / 3600`.

At sign crossings it interpolates the zero and integrates the two triangular
areas separately. `positive_signed_kwh >= 0`, `negative_signed_kwh <= 0`, net is
their sum, and absolute throughput is positive minus negative. Neither component
is called charging/discharging energy without polarity evidence; this release
keeps measured-sign names in all cases for consistent reporting.

Intervals are excluded at recording boundaries, missing/invalid/duplicate clocks,
nonpositive dt, dt above `EnergyConfig.max_interval_s` (default 30), or unusable
voltage/current. No interpolation bridges an excluded interval. Coverage reports
candidate, included, excluded and flagged-included intervals, reason counts and
included duration. Inferred time and current uncertainty remain explicit.
A zero integral over zero accepted intervals does not establish zero consumption.

Distance comes from normalized odometer values, not an assumed speed integration.
Negative or excessively large deltas are rejected with a configurable screening
speed (350 km/h by default, not an OEM maximum). Session odometer change and
distance over accepted energy intervals are reported separately. A signed
kWh/km estimate is provided only if **every accepted energy interval** has a
usable distance delta and their total is positive. Otherwise it remains null.
It is never asserted as verified efficiency: sign, interval coverage, charging
modes, auxiliary loads, rounding and measurement definitions can remain uncertain.

### Cell indicators

`cells.py` subtracts normalized max/min cell voltage and temperature. Numeric
spreads are retained even when flagged, including negative spreads, zero input
voltages and suspected -40 degC sentinels. Those measurements can create artificial
large spreads; they are not automatically genuine imbalance or battery defects.

Cell outputs propagate both input flags. Temperature derivatives also retain
previous-endpoint flags. Trends/abrupt changes are not computed across boundaries
or intervals above the configured maximum. Default spread/rate thresholds are
screening heuristics; see `examples/engineering_config.json`. No SOH, capacity,
remaining-life, causal thermal model or battery-fault classifier is implemented.

### Possible sessions

The existing Phase 2 boundary evidence supplies stable possible-session IDs.
Each report includes original and normalized start/end times, duration/count,
speed/voltage/current/SOC/temperature ranges, SOC change, odometer distance,
quality counts, signed energy and coverage, state distributions, candidate events,
and source-reported charging-code intervals. Raw SOC change is explicitly in
source units when percent is unverified; normalized percent change remains null.
Possible segments are not confirmed trips or charging sessions. Their interval
coverage is not assumed complete. No session statistic crosses a boundary.

## Dashboard description

The existing source selector, generic uploads, virtual demo and replay survive.
The real-world workspace now contains:

- **Overview:** original source/quality counters, recording ranges, synchronized
  telemetry, possible-session count, and threshold settings.
- **Vehicle Dynamics:** original speed, smoothed acceleration, overlapping
  candidates, source-reported mode, evidence labels and warning samples.
- **Battery Electrical:** voltage/current/SOC/power, signed-energy coverage,
  whole-recording power histogram and same-row relationship scatter plots.
- **Battery Health Indicators:** cell extrema, spreads, annotated temperature
  trends and sensor-screening warnings, not a battery-health estimate.
- **Session Explorer:** per-session table and a selection linked to every shared
  row/time window. Selecting a session also changes the synchronized telemetry.
- **Diagnostics:** independent physical/metadata/time/missing dimensions, raw
  anomaly details, source uncertainty and downloadable engineering reports.
- **Recorded Replay:** Play/Pause/Reset/speed and current operating candidate,
  signed power, voltage/current/SOC and normalized maximum-cell temperature.
- **Exports & Source:** original recording exports, raw preview and provenance.

Whole-recording electrical/energy totals are labeled as such; session totals are
in Session Explorer. Scatter plots and feature previews follow the shared interval.
Rendering uses at most 1500 engineering points (2000 Phase 2 points); full analysis
and exports use all observations. Line groups are computed before sampling to
preserve breaks. Workbooks/engineering results are cached per source/config;
changing engineering thresholds does not re-import or repair the source workbook.
Reports/features are prepared only on demand. Screenshots are not fabricated;
these descriptions correspond to the tested Streamlit views.

## Reproduce

Python 3.12, from repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install --no-build-isolation --no-deps -e .
python -m pip check
python -m pytest -ra
can-lab demo --steps 100
python -m streamlit run src/can_lab/dashboard.py --server.address 127.0.0.1 \
  --server.headless true --browser.gatherUsageStats false
```

Without real data:

```bash
python examples/make_ev_fixture.py /tmp/synthetic-v03.xlsx
can-lab report-xlsx /tmp/synthetic-v03.xlsx \
  --profile /tmp/synthetic-v03.profile.json \
  --engineering-config examples/engineering_config.json \
  --output-prefix outputs/synthetic-v03 --include-features
```

The original `analyze-xlsx` command still writes recording JSON/CSV/diagnostic
JSON and now adds engineering JSON/Markdown; existing stdout quality keys remain
present with an additive `engineering` summary. `report-xlsx` avoids full recording
exports when only reports are needed. `--include-features` adds per-observation
engineering CSV. Commands refuse to overwrite existing outputs.

For a local copy of the public SCUT workbook:

```bash
can-lab report-xlsx '/path/to/vehicle#1.xlsx' \
  --profile src/can_lab/data/translab_scut_vehicle1_review.json \
  --quality-config examples/scut_quality.json \
  --engineering-config examples/engineering_config.json \
  --output-prefix outputs/vehicle1-v03 --include-features
```

In Streamlit select Real-World EV Dataset, upload the workbook and enable the
source-reviewed SCUT preset. Engineering JSON sections (`operating`, `energy`,
`cells`) can be overridden under Source profile and quality thresholds. The
SCUT preset establishes no current polarity or normalized SOC scale.

## Reports, tests and remaining evidence

`engineering_reports.py` exports provenance-rich report JSON, human-readable
Markdown and optional feature CSV. Raw source data remains in original recording
exports. Report `data_categories` distinguish measured/derived/inferred/
source-reported/unverified values. CSV has one JSON metadata preamble and includes
original row/time, power/input flags, acceleration/candidates and cell flags.
There is no PDF dependency. Existing recording CSV/JSON round trips are unchanged.

Tests use synthetic fixtures with analytical answers, including sign-crossing
power, acceleration/deceleration/noise, gaps, duplicate timestamps, polarity
requirements, invalid measurements, cell spreads and session-energy consistency.
All existing CAN/DBC, importer, timestamp, replay and interchange tests remain.
Full public-workbook findings and exact executed counts are in `docs/validation.md`.
CI requires no real dataset and runs both recording and engineering CLI workflows.

Source attribution: [SCUT repository](https://github.com/Translab-SCUT/Electric-vehicle-operation-data),
reviewed revision `f3bc3eb9132c46fc75e3e60662515dbaf7325c98`; profile references pin
its README. `MDDHHMMSS` is inferred from full calendar/cadence consistency, not
documented by that README. Year/timezone, current polarity, SOC scale, sentinel
semantics, calibrated thresholds and confirmed trip IDs remain unresolved. No
license permitting dataset redistribution was established; no workbook/archive
is committed. Native/hardware CAN validation is not claimed.

## File map

| Module | Responsibility |
| --- | --- |
| `engineering_common.py` | Shared input/interval/status-evidence rules |
| `operating.py` | Smoothed dynamics and operating candidates |
| `energy.py` | Signed, gap-aware integration and matched-distance qualification |
| `cells.py` | Cell spreads/trends and propagated screening flags |
| `engineering.py` | Electrical statistics, session assembly and analysis config |
| `engineering_reports.py` | JSON/Markdown/feature CSV reports |
| `engineering_dashboard.py` | Bounded engineering views and session/report controls |
| Existing `recorded_dashboard.py`, `workbook_cli.py`, `cli.py` | Additive UI/CLI integration |
| `tests/test_engineering.py`, existing dashboard tests | Analytical and integration regression coverage |
