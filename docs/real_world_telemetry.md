> v0.3 integrates this preserved Phase 2 pipeline with operating-state, signed-energy, cell and session analysis. See [engineering_v0.3.md](engineering_v0.3.md) for the new calculations and reports.

# Phase 2: decoded EV recordings, diagnostics and replay

## Architecture

```text
.xlsx (read-only openpyxl row iterator; pandas datetime support)
  + DatasetProfile (dataset ID, declared input units, time representation, sign)
                 |
                 v
Recording: raw cells + original row order + normalized values + provenance
                 |
       configurable QualityConfig
                 |
     quality-aware power / vehicle dynamics
        /                |                    \
Streamlit views    RecordedDataSource       recording exports
                   + clocked Replay        JSON / annotated CSV / diagnostics
```

The existing synthetic ECU, SocketCAN entry points, DBC, `TelemetrySample` v1,
CSV/JSON/candump interfaces and portable demo remain intact. No CAN identifiers
are invented for imported workbooks. Excel contains already decoded measurements,
not raw CAN frames. Source filename alone does not establish a vehicle identity.

## Dataset status and attribution

The initial schema-only implementation has now been checked against the public
[Translab-SCUT source](https://github.com/Translab-SCUT/Electric-vehicle-operation-data)
at revision `f3bc3eb9132c46fc75e3e60662515dbaf7325c98`, including all **81,898**
observations from its `vehicle#1.zip` workbook. Earlier source-search attempts
were denied, but this supplied repository's README and raw archive were accessible.
The dataset remains outside Git. See `docs/validation.md` for its SHA-256,
full timestamp/quality results, and the exact scope of verification.

The README documents eight numerical source-column units and charging codes
1 (charging mode) / 3 (driving mode). It does not specify the timestamp encoding,
year, timezone, current polarity, or explicit SOC scale. The packaged
`src/can_lab/data/translab_scut_vehicle1_review.json` profile records exact pinned
source references for supported units/status labels. It leaves SOC/polarity
unknown and marks `MDDHHMMSS` time interpretation as inferred. Units are not
verified merely by plausibility of a signal's magnitude.

No dataset license permitting redistribution was established. Cite the primary
repository and revision when reproducing this review, and obtain its actual
license/attribution requirements and any paper/DOI before redistribution. No
license, authors, recording year, vehicle specification or current sign is invented.

## Source mapping

| Original column | Normalized recording field | Target unit / semantics |
| --- | --- | --- |
| `time` | `timestamp_s` | s; raw timestamp also retained |
| `vhc_speed` | `speed_kmh` | km/h |
| `charging_signal` | `charging_status` | Raw category retained; codes unverified, no labels inferred |
| `vhc_totalMile` | `odometer_km` | km |
| `hv_voltage` | `battery_voltage_v` | V |
| `hv_current` | `battery_current_measured_a` | A, **original measured polarity** |
| `bcell_soc` | `soc_pct` | % |
| `bcell_maxVoltage` | `cell_voltage_max_v` | V/cell |
| `bcell_minVoltage` | `cell_voltage_min_v` | V/cell |
| `bcell_maxTemp` | `cell_temperature_max_c` | degC |
| `bcell_minTemp` | `cell_temperature_min_c` | degC |

These are target units. Generic imports do not assume source units; the source-reviewed profile documents the eight numerical units listed above, leaving SOC scale unknown. Without a declaration,
numeric raw values can be inspected with `source units UNVERIFIED` labels; the
corresponding normalized values remain null. No missing voltage/current/SOC/RPM
is fabricated. Cell temperature extrema are not relabeled as pack-average
battery temperature. Unknown extra source columns are retained in `raw`.

### Profiles and time

`DatasetProfile.units` maps **original source names** to declared units. Supported
conversions include m/s or mph -> km/h, m -> km, mV -> V (pack and cells), mA -> A,
SOC fraction -> percent, K -> degC. Unsupported declarations fail explicitly.
Metadata records both declared source units and target units; declarations have
`unit_status: user_declared`; the cited preset uses `source_documented` for documented units/meanings. Other meanings remain explicitly unverified.

Default `time_unit: datetime` accepts native Excel dates and ISO-8601 strings,
not ambiguous numeric serial values. Native Excel dates are interpreted by
openpyxl using the workbook's date system. Relative datetime normalization uses
the first parsable timestamp as origin and preserves the original cell/type and
origin in metadata. Naive dates are not assigned an invented timezone.
`time_basis: unix` requires timezone-aware date strings. Numeric timestamps need
an explicit `time_unit` of `s`, `ms` or `us`, plus their `relative`/`unix` basis.
Negative, invalid and mixed-awareness times are flagged. No sorting or timestamp
repair hides clock resets. Equal timestamps are retained and flagged as duplicates.

A synthetic profile is generated by `examples/make_ev_fixture.py`. Its units and
polarity assumptions must **not** be applied blindly to `vehicle#1.xlsx`.

## Quality policy

| Flag | Meaning |
| --- | --- |
| `VALID` | No configured issue for this signal; not a calibration/safety guarantee |
| `MISSING` | Missing column/value or nonnumeric measurement; original cell retained |
| `OUT_OF_RANGE` | Outside configured normalized bounds, e.g. impossible SOC or zero cell voltage |
| `SUSPECT` | Unverified unit/category, possible -40 degC sentinel, discontinuity, flatline or inconsistent extrema |
| `TIMESTAMP_ERROR` | Unusable, duplicate, reversed or irregular timestamp |

`quality.py` is reusable without CAN/Streamlit. `QualityConfig` accepts configurable
`ranges`, `sentinels`, `max_rate_per_s`, `expected_interval_s`, interval tolerances,
`flatline_min_samples`, `flatline_tolerance`, and maximum cell-temperature spread.
Defaults are documented screening heuristics in the class, not OEM operating
limits. Bounds/rates are applied only to normalized values whose units are declared.
Unknown units are flagged, never checked against an assumed physical scale.

Sampling interval defaults to the median of positive adjacent intervals when at
least two are available. An explicit expected interval is preferable for known
recordings; median inference can miss systematically missing samples. Duplicate
and reversed timestamps are flagged separately. All samples in a flatline or a
duplicate group are marked, including the first. Constant values can be legitimate
(e.g. stationary speed); flags invite investigation, not deletion. A -40 degC
value is only a possible sensor sentinel, not conclusively invalid.

Summary categories overlap: a row can contain both missing and suspicious signals.
A valid observation has no flags across its signals/time/derived data. Per-signal
statistics include power after calculation. Unverified charging codes and current
polarity may therefore make every observation suspicious. This is explicit
uncertainty, not evidence that every raw measurement is wrong.

## Power and vehicle dynamics

`diagnostics.calculate_power` uses only voltage and current from **the same row**:

`P_signed_kw = battery_voltage_v * battery_current_measured_a / 1000`

Default `current_convention: unknown` retains signed electrical power and makes
no assertion about charging/discharging. Optional `positive_discharge` or
`positive_charge` must come from documented source knowledge. The calculation
always preserves the original measured polarity, even when a profile declares
one. It never infers the convention from current sign, voltage or charging codes.

Missing, nonnumeric, out-of-range or unit-unverified inputs yield null power.
Suspect but numeric input values may produce power with propagated input flags;
unknown polarity adds `SUSPECT`. Raw inputs are never deleted. Formula, units,
polarity, alignment and invalid-input policy are exported. The Phase 2 power module itself does not integrate energy. v0.3 adds separately qualified signed-energy analysis; verified efficiency, capacity and battery-health estimates remain unimplemented.

Acceleration is an adjacent backward difference of normalized speed:
`a = (speed_kmh[i] - speed_kmh[i-1]) / 3.6 / dt`.
It requires both endpoints' speeds and timestamps to pass configured checks;
duplicate/reversed/irregular time or suspect speed suppresses the derivative.
Stationarity uses an explicit configurable speed threshold. These are inspection
aids, not a filtered dynamics model or an implementation of VEUS.

## Replay

`RecordedDataSource` is a protocol; `RecordingSource` exposes original observations.
`Replay` uses an injected monotonic clock, original relative offsets, and a cursor.
It supports play/pause/reset, speed changes without time jumps, and emits all due
rows in original order, including equal-time rows. The UI refreshes replay controls
in a Streamlit fragment; it does not reparse the workbook on each tick. If several
rows are due between UI updates, every row is consumed in order while the metrics
show the latest due row (not a hard-real-time display of every sample).

Timed replay requires usable nondecreasing timestamps. Recordings with unknown
numeric time units, missing times or clock reversals remain available for full
quality analysis/export but cannot be replayed on a timed clock until explicitly
corrected outside the importer. No automatic repair, reordering, forward filling,
CAN encoding or hardware dependency is introduced.

## Exports and canonical compatibility

`recorded_io.py` writes:

- **Recording JSON**: `can-lab-recording-1` envelope with metadata and all original
  observations, raw cells/timestamps, normalized values, quality and derived values.
- **Annotated CSV**: one `# can-lab-recording-1 metadata=...` comment, followed by
  normalized columns and `raw_json`, `quality_json`, `derived_json` columns. The
  comment keeps dataset metadata once instead of repeating it per sample.
  Use `pandas.read_csv(..., comment='#')` for values or `load_annotated_csv` for
  complete round trips. The raw JSON column retains formula/text cells without
  evaluating them as spreadsheet formulas.
- **Diagnostic JSON**: source metadata, units, quality configuration/statistics,
  duration when trustworthy, and calculated power range.

These provenance-rich exports are distinct from the unchanged Phase 1 strict
schema-v1 array/CSV formats. `Recording.canonical_samples()` is an explicit bridge
for existing consumers: common verified-unit values map into `TelemetrySample`,
unknown current polarity leaves `battery_current_a` null, and documented
positive-charge current is inverted into Phase 1's positive-discharge convention.
Missing/negative/nonmonotonic timestamps fail rather than silently dropping rows.
Cell extrema and raw metadata remain in the recording envelope; use that envelope
when those signals are needed. No downstream simulation or health ML is included.

## Reproduce without the real dataset

From the repository root, use the pinned installation in the README:

```bash
python examples/make_ev_fixture.py /tmp/synthetic-ev.xlsx
can-lab analyze-xlsx /tmp/synthetic-ev.xlsx \
  --profile /tmp/synthetic-ev.profile.json \
  --output-prefix outputs/synthetic-ev
python -m pytest -ra
python -m streamlit run src/can_lab/dashboard.py --server.address 127.0.0.1 \
  --server.headless true --browser.gatherUsageStats false
```

Choose **Real-World EV Dataset**, upload the workbook, and upload its matching
profile under **Source profile and quality thresholds**. Or declare time units,
source units and polarity through the controls. The generated 60-row example
contains a deliberate -40 degC sentinel and constant segments; expect flags.

For the real workbook, select the desired worksheet (first by default), provide
its actual dataset ID/reference, verify and declare its units/time representation,
and leave current convention unknown unless documented. Inspect overview ranges,
quality diagnostics, electrical/thermal charts, replay and exports. The importer
never writes to the source workbook and records its SHA-256 for provenance.
CLI options include `--sheet`, `--max-rows`, `--quality-config`, and `--profile`;
output files refuse overwrites. `--output-prefix` takes a stem, not an extension.

## Resource limits and remaining verification

The importer hashes in chunks and streams openpyxl rows; it does not call
`pandas.read_excel` or retain a second full-workbook dataframe. One raw/normalized
recording and its quality flags remain in memory, O(rows × signals); this is not
an unlimited streaming analytics engine. Openpyxl may also retain shared strings
and archive metadata. An explicit row limit defaults to 250,000 and fails rather
than silently truncating; formatted empty rows within the worksheet dimensions
are retained and count toward that limit. Formula cells are retained as formulas,
flagged nonnumeric, and never evaluated.

The dashboard keeps a single imported recording per session, previews 200 rows,
and samples plots to at most 2000 points; full diagnostics/exports retain all rows.
Small anomalies may be absent from sampled plots. JSON/CSV exports are prepared
only on demand through temporary files; browser downloads still require transfer
buffers. Chart ranges include suspect observations. For substantially larger
recordings, a next milestone is chunked on-disk storage and indexed replay.

The public workbook format, supported units/status codes and full row count are now inspected. Timestamp encoding remains inferred; recording year/timezone, license, SOC scale and current polarity remain unverified. Native SocketCAN hardware/kernel validation is separate and remains
unclaimed. All Phase 2 automated tests use synthetic workbooks.

## Implementation files

| Files | Responsibility |
| --- | --- |
| `src/can_lab/recording.py`, `excel.py` | Recording envelope, explicit profile, canonical bridge, read-only workbook import |
| `src/can_lab/quality.py`, `diagnostics.py` | Configurable screening, summaries, power and vehicle dynamics |
| `src/can_lab/replay.py` | Recorded-data source interface and deterministic replay controller |
| `src/can_lab/recorded_io.py` | Provenance-rich JSON/CSV and diagnostic exports/readback |
| `src/can_lab/recorded_dashboard.py` | Recorded-data views, bounded plots, replay controls, export UI |
| `src/can_lab/dashboard.py`, `cli.py`, `workbook_cli.py` | Existing UI/CLI extension and workbook analysis command |
| `examples/make_ev_fixture.py` | Reproducible synthetic workbook/profile generator |
| `tests/test_recorded_telemetry.py`, `test_recorded_dashboard.py` | Phase 2 automated tests |
| `pyproject.toml`, `requirements-lock.txt`, `.github/workflows/tests.yml` | Optional Excel dependencies, version lock and CI |

See `docs/validation.md` for executed checks and remaining limitations.


## Source review: independent dimensions and synchronized intervals

`recording_review.py` provides independent dimensions under
`quality_summary(recording)["dimensions"]`, timestamp-representation inspection,
raw-step reports and possible boundary detection. It never treats a
`unit_unverified` or `status_codes_unverified` flag alone as physical invalidity.
Original conservative flags and combined counts are retained. Numerical
plausibility and physical heuristic suspicion can overlap (for example, a constant
finite temperature can be in range but trigger a flatline heuristic).
Unverified numeric time is separate from invalid clock values. A cadence gap can
be an anomaly without making its parsed timestamp invalid.

Use the explicit SCUT preset checkbox in the UI, or:

```bash
can-lab analyze-xlsx '/path/to/vehicle#1.xlsx' \
  --profile src/can_lab/data/translab_scut_vehicle1_review.json \
  --output-prefix outputs/vehicle1-review
```

For a custom profile, `time_unit: "MDDHHMMSS"` splits the final eight digits as
DD/HH/MM/SS and the leading one/two digits as month. It validates component ranges
and calendar month lengths. Elapsed seconds are measured from the first parsable
value without a synthetic year, timezone or Unix origin. Negative/resets are not
repaired. February-crossing elapsed intervals require an explicit
`calendar_leap` choice if their length is otherwise ambiguous; year rollover is
not silently inferred. Within the reviewed April recording that ambiguity does
not arise. The source README does not prove this encoding, so every such import
retains `time_interpretation_status: inferred_yearless_encoding` and raw times.

The preset uses source-documented units/status codes with exact README URLs via
`unit_references`, `status_codes`, and `status_reference`. Unknown/unlisted status
codes remain metadata warnings. Numeric SOC is shown in source units, not
silently assumed percent. The measured current remains in original polarity.

Shared row/time sliders and possible-segment selection control every chart,
including the synchronized overview. `recording_plots.py` creates line groups
before display sampling, so missing values and inferred boundaries cannot be
bridged by downsampling. Row-index fallback is clearly labeled NOT time and draws
points without continuity assertions. Possible gap boundaries use configurable
`session_gap_s` or `session_gap_factor` (default 10 times nominal interval); they
are not proven trips. Optional `raw_max_step` thresholds use explicitly configured
source units, not guessed per-second rates. Raw step reports include elapsed
interval/boundary context where possible.

Full diagnostics are cached per import/profile/configuration; interval changes do
not reparse the workbook. Only bounded plot data is duplicated for display.
Exports retain the original cells and now include independent summaries,
timestamp evidence, anomaly statistics and source references in diagnostic JSON.
