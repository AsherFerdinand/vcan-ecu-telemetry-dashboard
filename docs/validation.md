# Phase 1 validation record

Executed on 2026-10-23, Linux cloud container, Python 3.12.14.

- Editable installation: `python -m pytest -ra`: **90 passed**, no skipped tests.
- Clean virtual environment installed from `requirements-lock.txt`, then built
  wheel installed with `--no-deps`: **90 passed**, no skipped tests. Tests ran
  from outside the checkout; the codec loaded the DBC from the installed package.
- `pip check`: no broken requirements in both environments.
- `can-lab demo --steps 100`: **200 decoded samples**, no quality flags.
- README CSV, JSON, candump and mapped-unit import commands: all succeeded;
  standardized JSON and CSV outputs were produced in ignored `outputs/`.
- Fresh-wheel `can-lab demo --steps 10`: **20 decoded samples**.
- Streamlit server: HTTP health `200 ok` and root HTML response verified;
  server stopped after validation. AppTest verified empty UI and synthetic CSV
  upload, four-row data table, signal selection, and no application exceptions.
- Compatibility scripts on this host: both correctly exit status 1 on native
  CAN initialization failure, rather than reporting a false successful run.
- `git diff --check` and staged diff check passed.
- Original HEAD remains `d04f388b25a4b46d1175f33e5bd69ce0d40eb7fc`;
  no commit, history rewrite or push was performed.

## Not verified

- Native SocketCAN: kernel CAN socket family unavailable; `vcan0` creation denied
  due to missing network administration capability. Portable virtual transport
  is verified separately and does not resolve this host limitation.
- Real ID.3/Taycan recordings: discovery requests were denied by the egress proxy;
  no vehicle-specific adapter or signal claims were made.
- GitHub Actions: workflow added, equivalent local suite passed; remote Actions
  execution will occur after the changes are committed and pushed.
- Fresh cloud publication/restoration: configuration draft saves do not publish
  or validate a restored task.

# Phase 2 validation record

Executed on 2026-10-29, Python 3.12.14, package version 0.2.0.

- Complete editable-checkout suite: **143 passed**, no skipped tests.
- Clean environment installed from the updated version lock, with the built
  0.2.0 wheel installed (not editable): **143 passed**, no skipped tests.
  Tests ran from outside the checkout and used the installed package.
- All 90 Phase 1 regression tests remain included and passing. The 53 additional
  tests cover workbook/provenance/mapping, invalid/missing cells, time anomalies,
  configurable signal screening, power and propagated flags, dynamics, replay,
  rich export round trips, CLI analysis and real-world/virtual UI controls.
- The representative **synthetic** 60-row workbook generator and analysis CLI
  succeeded; recording JSON/annotated CSV round trips preserved raw timestamps,
  original columns, dataset ID, declared units, quality and calculated power.
  The deliberate -40 degC value was retained and flagged. This was not the actual
  research workbook and is not evidence of that dataset's units/sign convention.
- Installed-wheel virtual ECU demo: **200 observations**, 100 engine frames and
  100 battery frames, no quality flags.
- Dashboard startup without a workbook: HTTP health and HTML responses passed.
  Streamlit AppTest exercised Excel upload, declared units, power, suspicious
  temperatures, Play/Pause/Reset, invalid-time replay blocking, exports and
  simulation generation. The validation server was stopped afterward.
- `pip check` passed in both environments. Only openpyxl and its et-xmlfile
  dependency were added to the existing pinned dependency set; pandas was already
  installed by the UI. Excel remains an optional package extra for CAN-only use.
- No non-ignored file over 1 MB and no non-ignored research `.xlsx` workbook were
  found. The generator creates files only at the requested local path.
- No lint/formatter configuration was present. Unstaged and staged
  `git diff --check` passed. CI now also generates and analyzes the synthetic
  workbook after running tests and the virtual demo; remote CI has not run here.

Actual `vehicle#1.xlsx`, primary dataset documentation/license/current polarity,
and hardware CAN validation remain pending. Source discovery attempts returned
proxy 403 responses. The original Git HEAD and history remain unchanged; changes
are local and uncommitted. Environment configuration saves do not establish a new
published/restored cloud environment.

# Public vehicle#1 source review and quality/visualization correction

2026-10-29. This review supersedes the earlier real-workbook-access limitation.
The user's browser-uploaded bytes were not accessible in this process, but the
public upstream archive was downloaded successfully and its workbook matches
all user-supplied first-ten timestamps, final timestamp and observation count.

## Source and scope of verification

- Source: https://github.com/Translab-SCUT/Electric-vehicle-operation-data
- Inspected revision: `f3bc3eb9132c46fc75e3e60662515dbaf7325c98`.
- Archive: `vehicle#1.zip` at that revision; workbook SHA-256:
  `3d0f39c947ecb08867e01e49dfe83995552a5f9fb69580910ea71f8be12e34b3`.
- The workbook was retained only under `/tmp/ev-source-review/`; neither the
  dataset nor archive is included in Git. No license permitting redistribution
  was established; no redistribution permission is inferred from public access.
- README documents speed km/h, mileage km, pack voltage V, pack current A,
  maximum/minimum cell voltage V, cell temperature degC, and charging codes
  1 = charging mode, 3 = driving mode. It lists vehicle#1's nominal cadence as
  0.1 Hz (10 seconds). The source-reviewed profile cites that exact README.
- README describes `Time` only as acquisition timestamp. It does **not** document
  its encoding, recording year/timezone, current polarity, or explicit SOC unit.
  The profile therefore leaves SOC scale and current polarity unverified and
  labels the time interpretation **inferred**, not source-verified. Vehicle
  specifications in that repository are not imported into screening thresholds.

## Full-workbook timestamp results

All **81,898** observations were parsed and validated with the explicitly selected
`MDDHHMMSS` interpretation. All source time cells are integers formatted `General`.
First time: `401042909`; final time: `430235734`. The first ten inferred elapsed
values are `0, 10, 20, 30, 40, 50, 60, 70, 80, 90` seconds. The `...2959` ->
`...3009` minute rollover is 10 seconds, not its raw integer difference of 50.

| Check | Result |
| --- | ---: |
| Calendar/time-component parse failures | 0 |
| Duplicate timestamps | 0 |
| Backwards clocks | 0 |
| Usable inferred elapsed timestamps | 81,898 |
| Inferred recording span, including gaps | 2,575,705 s (29 days, 19:28:25) |
| Adjacent intervals | 81,897 |
| Exactly 10-second intervals | 77,132 |
| Intervals differing from 10 seconds | 4,765 |
| Intervals outside the configured ±20% (±2 s) tolerance | 4,755 |
| Minimum / maximum interval | 7 s / 179,523 s |
| Possible boundaries at gaps greater than 100 s | 699 |

These establish calendar/cadence consistency across the full public workbook,
not documentary proof of the encoding or an actual year. No artificial year,
UTC offset or epoch is attached. Possible boundaries are configurable heuristics,
not confirmed trip identities. Year rollover and February/leap ambiguity are not
silently resolved. The parser rejects invalid calendar/time components and
requires an explicit leap-calendar choice for ambiguous February-crossing deltas.

## Independent quality counts

With the packaged source-review profile, expected interval 10 s, and other default
screening settings:

| Dimension | Observations |
| --- | ---: |
| Imported | 81,898 |
| Numerically plausible under available range checks | 81,762 |
| Physically suspicious under conservative heuristics | 76,867 |
| Metadata-unverified | 81,898 |
| Timestamp-invalid values/clocks | 0 |
| Timestamp cadence anomalies (overlaps usable timestamps) | 4,755 |
| Missing/nonnumeric observations | 0 |

These are **overlapping dimensions**, not a partition or an accuracy claim.
Numerically plausible means available finite values with no detected normalized
range violation. Flatline/jump/sentinel heuristics may overlap numerical
plausibility. Physical-suspicion counts remain high mainly because repeated
quantized temperature/other values trigger the pre-existing configurable flatline
heuristic; constant readings are not proof of a sensor fault. Metadata uncertainty
no longer automatically becomes physical invalidity. All SOC physical checks
remain incomplete until its scale is documented. Source units for the other
8 numerical columns are now documented; the remaining global metadata count
reflects SOC scale, inferred time interpretation and unknown current polarity.
Legacy combined conservative counts/flags remain available for compatibility.

Verified source ranges: pack voltage **322–389 V**, measured current
**−200.2–185.5 A**; SOC raw range **20–98**, scale unverified. No charging/power
polarity is inferred from those ranges or from charging codes.

Anomalies retained and reported:

- **6** minimum-cell temperature values of **−40 degC**, flagged as possible
  sentinels, not confirmed sensor failures. Maximum-cell temperature has none.
- **136** zero minimum-cell voltage readings; maximum-cell voltage has none.
- **6** minimum-temperature discontinuity flags under the configured 5 degC/s
  threshold, plus abnormal temperature-spread flags. Raw largest-step reports
  include original row pairs, elapsed interval where available, and possible
  boundary indicators; they do not label cross-session steps as physical faults.
- No missing/nonnumeric measurements in the public workbook. No values were
  repaired, clamped, sorted away or deleted.

## UI and regression behavior

Overview now separates numerical screening, physical suspicion, metadata,
timestamps and missingness, with category tooltips. Timestamp representation
inspection exposes raw examples/types, Excel formats, origin and interpretation.
The explicit **Use source-reviewed SCUT profile** option enables the documented
units/status codes plus inferred yearless parser; generic import defaults remain
conservative. The preset deliberately does not declare SOC percent or polarity.

Shared row/time interval and possible-segment selectors apply to every chart.
Synchronized charts share their time domain. Lines are separated at possible
session boundaries and missing measurements, including during downsampling.
Unknown-time row-index fallback uses points only and an explicit NOT-time warning.
Displayed anomaly points are prioritized within the plot budget; very large
selections are still sampled and should be zoomed for detailed review.

The diagnostics JSON now includes independent counts, timestamp evidence,
raw-anomaly summaries and original source references. Imported raw cells,
interpretation status and all conservative flags remain in recording JSON/CSV.

Validation of this correction:

- **166 automated tests passed** in the editable checkout and again using a
  rebuilt wheel in a separate environment, including all original CAN/DBC,
  importer, replay, power and export regressions. New tests cover calendar
  boundaries/invalid components, no invented year, numerical-vs-metadata
  classifications, raw sentinel/zero candidates, line breaks under sampling,
  source-profile provenance and shared UI zoom. No real dataset is required by CI.
- Streamlit AppTest loaded the **full public workbook** with the source-reviewed
  preset in approximately **13.1 seconds** in this environment, with no app errors.
  Its category metrics matched the table above. Zooming to elapsed 0–90 seconds
  selected exactly the first ten measurements with synchronized chart domains.
- Recorded replay consumed all **81,898** public-workbook observations in order
  and reached raw final timestamp `430235734`, without a CAN bus or invented IDs.
- Virtual ECU demo: **200 decoded observations**, zero flags. `pip check` and
  both staged/unstaged `git diff --check` passed. No formatter/linter is configured.
- No new non-ignored workbook/archive or file exceeding 1 MB is present. No
  dataset was committed. No hardware CAN validation or new GitHub Actions run
  is claimed. Changes from this correction are local on the development branch.

Additional documentation still needed: authoritative timestamp encoding and year/
timezone, SOC scale, current/power polarity, sensor sentinel/calibration semantics,
recording/trip boundary semantics, and redistribution/citation license terms.
The user's separately loaded file can be compared against the workbook SHA-256
above to establish byte identity with the public artifact tested here.

# v0.3 combined Phase 2 + Phase 3 release validation

Executed 2026-10-29, Python 3.12.14, package `automotive-can-lab` **0.3.0**.
The release preserves the source-reviewed Phase 2 implementation and extends it;
it does not replace the original virtual ECU/CAN pipeline.

## Automated and packaging verification

- **211 tests passed** in the editable checkout and **211 passed** from outside
  the checkout using the rebuilt wheel in a separate, non-editable environment.
  No skipped tests. All prior 166 tests remain included, covering CAN/DBC,
  timestamps/importers, independent quality dimensions, replay and interchange.
- New analytical tests cover smoothed acceleration/deceleration, stationary and
  constant-speed candidates, noise, irregular intervals, gap resets, documented
  charging status, unknown/unreferenced polarity, regeneration candidates,
  sign-crossing integration, invalid inputs, distance qualification, cell
  spreads/sentinels/trends, sessions/events, reports, feature CSV and original
  recording CSV/JSON consistency. Engineering core modules also import with
  CAN, pandas/openpyxl and dashboard libraries deliberately unavailable.
- Dashboard integration tests cover new views, threshold updates/errors, report
  preparation, replay metrics, shared session selection and time-domain labeling.
- The v0.3 wheel includes the SCUT profile and original DBC. `pip check` passed;
  `can-lab --version` reports `0.3.0`.
- Wheel-installed virtual demo: **200 decoded observations**, zero flags.
- CI now exercises `report-xlsx` with a generated synthetic workbook and optional
  feature CSV, in addition to the complete suite and original workflows. Actual
  remote Actions results are not claimed by these local checks.
- No formatter/linter configuration is present. `git diff --check` passed.
  No new runtime dependency was introduced.

## Full public-workbook engineering verification

The same pinned public workbook and SHA-256 documented above were used. The
original **81,898** observations and **2,575,705-second** inferred span remain
unchanged, including all sensor anomalies. A raw-cell hash before/after analysis
matched. Source references and recording flags remain in exports; recalculating
power now also preserves unrelated custom derived-definition metadata.

Default engineering configuration is committed as
`examples/engineering_config.json`; source cadence is explicit in
`examples/scut_quality.json`. The generic thresholds below are research
screening choices, not vehicle specifications.

| Candidate, default trailing-median window 3 | Observations |
| --- | ---: |
| Stationary | 32,639 |
| Approximately constant speed | 24,301 |
| Acceleration | 8,578 |
| Deceleration | 4,473 |
| Unknown dynamics / insufficient trend evidence | 11,907 |
| Source-reported charging (overlapping dynamics) | 6,811 |
| Possible regeneration | 0: current polarity not documented |

The existing 699 possible boundaries form **700 possible sessions**. Their signed
energy sums match the whole-recording accepted-interval integral within floating
precision. Candidate continuity produces 9,571 descriptive acceleration/deceleration
events; these are threshold candidates, not verified pedal/braking events.

### Signed electrical energy

Configured maximum integration interval: **30 seconds**. Data gaps are excluded,
not bridged or filled. Positive/negative components retain original measured sign.

| Quantity | Result |
| --- | ---: |
| Candidate adjacent intervals | 81,897 |
| Included intervals | 79,973 |
| Excluded boundary intervals | 699 |
| Additional intervals exceeding configured maximum | 1,225 |
| Total excluded intervals | 1,924 |
| Included duration | 841,317 s |
| Positive signed energy | 796.068312 kWh |
| Negative signed energy | -852.756864 kWh |
| Signed net energy | -56.688552 kWh |
| Absolute throughput | 1,648.825175 kWh |

All included intervals remain quality-annotated because current polarity is
unknown (and some intervals also carry cadence/flatline warnings). These results
are neither total vehicle consumption nor verified charging/discharging energy.
Time remains inferred and includes no invented year or timezone.

Only 75,215 accepted energy intervals had screened matched odometer deltas; the
sum over those partial intervals was 510 km. That is **not** reported as complete
session/month distance. Because coverage does not match all 79,973 energy
intervals, the signed energy-per-distance estimate is correctly **withheld**.
Odometer scale/resolution and rejected step semantics require confirmation; no
scaling factor or verified-efficiency interpretation was invented.

### Cells, exports and replay

- All **136 zero minimum-cell voltages** and **6 minimum-temperature -40 degC
  candidates** propagate into cell diagnostics. Spreads remain quality annotated;
  no confirmed battery defect, SOH or capacity estimate is asserted.
- Full engineering report JSON, Markdown and **81,898-row feature CSV** were
  produced successfully by the v0.3 CLI. The representative measured data,
  original timestamps, candidate/derived values and quality remain traceable.
  A separate real edge-case selection (including every zero/sentinel row)
  round-tripped through the original recording JSON and CSV without value loss.
- All **81,898 rows** replayed in original order without CAN hardware.
- Report/feature artifacts stayed under `/tmp`, never in Git. No workbook/archive,
  virtual environment, cache or generated report was staged.

## Dashboard validation and reproduction

Streamlit AppTest loaded the full source-reviewed workbook and engineering views
in approximately **15.8 seconds** in this environment, without app errors. It
verified 700 sessions, shared selection, report/feature download preparation,
Play/Pause and current candidate/power/temperature metrics. Session selection
updated every shared telemetry interval. The full UI check completed in about
23.1 seconds. Existing no-workbook startup and virtual simulation views passed.

Source analysis plus full report/feature CSV generation via the public-workbook
`report-xlsx` CLI completed in approximately **18.9 seconds**. Timing is local
measurement, not a performance guarantee. Plots are bounded and labeled as sampled;
full reports/analysis use all observations. See `docs/engineering_v0.3.md` for
architecture, file map, exact commands, calculation policies and UI descriptions.

Release publication is restricted to the existing `dev/phase2-ev-telemetry`
branch. `main` is not merged or rewritten. Commit identity is recorded by Git
and reported separately after successful push; no dataset is included.

Unresolved evidence remains: authoritative timestamp encoding/year/timezone,
current polarity, SOC scaling, odometer details, sensor sentinel/calibration
semantics, actual trip identifiers, vehicle-specific thresholds and dataset
redistribution/citation terms. Hardware/native CAN validation is not claimed.
