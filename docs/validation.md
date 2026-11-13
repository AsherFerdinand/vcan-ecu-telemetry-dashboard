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

# Architecture and portfolio revision — 2026-11-12

Reviewed foundation: v0.3.0 commit
`792b0df6172d2bef73e27d941dc588ba2ba5268d` on
`dev/phase2-ev-telemetry`. Work takes place on the dedicated
`refactor/engineering-architecture-roadmap` branch. The validated branch and
`main` are preserved; numerical algorithms, defaults, data schemas and package
version are unchanged. No v0.4–v0.8 functionality is added.

## Change and architectural evidence

The dependency review found the engineering core already independent of
Streamlit/CAN tools. No package-wide reorganisation was justified. The one source
refactor extracts duplicated workbook loading, validation and signed-power
preparation into `pipeline.prepare_workbook`, now called by CLI and dashboard.
Four new tests check raw-byte/stream-position/provenance preservation, known
signed power, conservative unknown-unit/time defaults, forwarding of source
selection/limits and dependency activation. All previous 211 tests remain.

`docs/architecture.md` retains its original spelling and schema anchors to avoid
a case-only `ARCHITECTURE.md` conflict on Windows. It adds six-layer and module
maps and explicit integration gaps. `WORKFLOWS.md` separates three industry-inspired
problems from affiliations/implemented features. `ROADMAP.md` gives v0.3–v0.8
acceptance gates. The README is an overview with a 128-word project introduction,
status-aware Mermaid diagrams, scoped capabilities and short-path Windows setup.
Numerical/dataset detail remains in the existing technical documents.

## Executed checks

- **215 tests passed**, no skips, in the existing development environment.
- A new `.venv` was created with **Python 3.12.14 on Linux**, using the README's
  pinned dependency installation, editable install and `pip check` commands.
  **215 tests passed**, no skips, in that fresh environment as well.
- The clean environment's documented module CLI ran the virtual ECU demo:
  **20 decoded observations, zero flags**. Independent synthetic byte-vector
  and transport tests remained in the full suite.
- Canonical CSV/JSON and supported synthetic candump CLI imports succeeded.
- A generated, clearly synthetic 60-row workbook produced engineering JSON,
  Markdown and a 60-row feature CSV through the headless CLI workflow.
- The clean environment launched Streamlit using the README command options.
  HTTP health returned `200 ok` and root HTML was served without a workbook;
  the validation process was stopped afterward. Existing Streamlit/replay tests
  exercise the shared preparation service through the unchanged application UI.
- `tools/check_docs.py` verified **35 local file/heading links across nine
  Markdown documents** and no case-only document collisions. A temporary broken
  link was deliberately rejected and then removed. CI now runs this check.
  External URLs, Shields.io rendering and Mermaid rendering are not covered by
  this local link check; diagrams were source-reviewed.
- `git diff --check` passed. No formatter/linter configuration is present.

## Full public workbook through the shared service

The pinned SCUT public archive was retrieved outside the checkout for this rerun.
Workbook SHA-256 matched the prior validation exactly:
`3d0f39c947ecb08867e01e49dfe83995552a5f9fb69580910ea71f8be12e34b3`.

`prepare_workbook` with the reviewed source profile and 10-second expected cadence,
followed by the existing engineering function, reproduced:

| Check | Result |
| --- | ---: |
| Observations | 81,898 |
| Inferred recording span | 2,575,705 s |
| Possible sessions | 700 |
| Included / excluded energy intervals | 79,973 / 1,924 |
| Signed net over accepted intervals | -56.68855195833805 kWh |
| Invalid timestamp values/clocks | 0 |
| Minimum-temperature raw -40 values | 6 |
| Zero minimum-cell-voltage values | 136 |

Engineering JSON/Markdown exports succeeded. The rerun took approximately 17.9 s
in this environment; this is an observed runtime, not a performance guarantee.
The workbook and generated reports stayed outside Git. Earlier full-workbook
replay and edge-case interchange evidence remains in the v0.3 validation section;
this refactor's complete suite reran replay/export regressions.

## Limits and remaining work

There is no native Windows, PowerShell executable or macOS host in this execution
environment. **Windows PowerShell instructions were reviewed but not natively
executed**; Linux equivalents were executed. The version lock was produced for
Python 3.12/Linux, so native Windows installation/runtime must be independently
checked before advertising Windows platform validation. No platform evidence is
inferred from command syntax alone.

Real vehicle CAN/matching-DBC and physical hardware validation remain outstanding.
The original synthetic codec is unchanged. Source candump files retain raw frames,
but exported v1 samples do not provide a complete frame archive/back-reference;
that is a documented v0.4 requirement, not an implemented feature of this task.
Timestamp encoding remains inferred; recording year/timezone, current polarity,
SOC scale, sentinel meaning and dataset redistribution terms remain uncertain.
No AI, forecasting, root-cause or gateway/cloud functionality is claimed.

The full real dataset, generated outputs, `.venv`, caches and temporary link probe
are excluded from the commit. Publication is limited to the new refactoring branch,
with no automatic merge or changes to validated branch refs.

## v0.4 foundation — current execution

Starting point: architecture commit `d8aa5fdef334050bf1ddab24e10c8a872f2ec33b`.
Development branch: `dev/v0.4-real-can-validation`; package `0.4.0.dev0`.
**Implemented, synthetic-fixture validated; public real-CAN validation BLOCKED.**
The historical v0.3/SCUT results above are retained and were not rerun or promoted
to raw-CAN evidence in this task. The original synthetic codec remains unchanged;
the new configurable decoder has an explicit provenance-rich Recording adapter.

Three public source candidates and their pinned revisions were assessed in
[raw CAN validation](raw_can_validation.md). None established a selected permitted
capture + matching DBC + independent physical references. No real-vehicle accuracy,
hardware CAN validation or completed v0.4 release is claimed. Required next evidence:
vehicle/software/bus compatibility, timestamp basis, capture redistribution terms,
exact DBC revision, and independently sourced values/tolerances.

The authored fixture verifies little/big endian, signed extraction, scaling,
offset and units with five manually calculated expected values. All five passed;
7 scanned records produced 4 decoded frames, 1 unknown ID, 1 wrong DLC and
1 malformed record. Raw timestamp text and frame line/index/byte offsets survive;
JSON/CSV Recording round trips preserve the shared frame table and optional RPM.
One electrical frame gives −10 kW signed measured power; no accepted battery-energy
intervals exist. Equal timestamps across separate V/I frames do not create power.
The independent physical accuracy status remains `not_established`.

Regression coverage adds strict DBC/protocol rejection, malformed input counters,
unknown IDs, exact hash checking before decode, metadata/path protection, filtering,
clean byte/line-limit failure, a 20,000-line generated input with retention capped
at 10 frames, deterministic reports, no-overwrite output policy, read-only audit
and dataset-free Streamlit investigation/engineering/download preparation. Default
tests make no research download. Baseline virtual bus, synthetic DBC, replay,
workbook quality, engineering and export tests remain in the suite.

### Storage evidence and retention

Before changes: 63 tracked files / 334,930 content bytes; ignored outputs:
16 files / 340,771 bytes. After the explicitly requested full example run:
21 output files / 400,616 bytes (five new artifacts, 59,845 bytes). Largest outputs
were `phase2-synthetic.json` 82,205; `demo.json` 78,948;
`phase2-synthetic.csv` 72,121; historical architecture feature CSV 54,569;
new CAN engineering JSON 26,168 bytes. Source audit measures working tracked-file
content, not compressed `.git`, ignored environments or all filesystem usage.
The existing repo `.venv` occupies approximately 493 MB; it was not copied/deleted.
Small research probes stayed outside the checkout (one SavvyCAN log 489,938 bytes,
DBCs 274,509 and 2,001 bytes). No full research corpus, redundant dataset copy,
phase ZIP or model artifact was produced or committed. No cleanup was performed.

Ignore checks cover raw logs/CSV/workbooks/archives, outputs and environments;
tiny authored fixture exceptions are explicit. New source manifests/configuration
are permanent; run reports are ignored generated artifacts. Existing historical
reports, original workbooks and any independent acquisitions require separate
owner-managed backup, identified by SHA-256. They were not removed. See
[retention policy](data_artifacts.md). Final tracked/output inventory is available
through the read-only `storage-audit` command at the pushed revision; clean-source
example reports are opt-in and not part of Git.

### Executed installation and runtime checks

At implementation commit `f5e852b141cf02772360619d63d417eec16a87e5`:

- Full suite: **263 passed** in 15.52 s; all 215 baseline tests retained.
- A shallow single-branch fresh clone installed from `requirements-lock.txt` plus
  `pip install --no-deps --no-build-isolation .`; import resolved to the installed
  `site-packages/can_lab`, version `0.4.0.dev0`, rather than the original checkout.
  Existing dependency runtime was deliberately reused to avoid duplicating roughly
  493 MB. This verifies fresh-source installation, **not a pristine OS/new-venv test**.
- Fresh-checkout suite: **263 passed** in 15.68 s, without downloading research data.
  `pip check` reported no broken requirements. All 47 local documentation links/
  headings passed the offline checker.
- Virtual CAN demo: 20 samples processed, zero flagged. Existing regression tests
  exercised synthetic DBC, replay and telemetry exports.
- Fresh-checkout synthetic investigation: four decoded frames, all five manual
  references passed; compact JSON/Markdown plus manifest created only on request.
  Manifest recorded the clean implementation commit and complete input/DBC hashes.
- Streamlit started headlessly from the fresh checkout; `/_stcore/health` returned
  `ok`. Streamlit AppTest regressions exercised the new workspace, bounded scan,
  engineering analysis and requested report preparation, not just HTTP startup.

No historical archive was needed. The verification clone is a small shallow source
checkout, not a copied research dataset or another full dependency environment.
Native Windows/macOS and physical CAN hardware remain untested in this execution.

## Real vehicle evidence sprint — 2026-11-13

Starting revision: `eca7498069d664b1b372765ed45e55cf62c9a84e`, same
`dev/v0.4-real-can-validation` branch. Historical foundation checks above remain
historical; the new [KUKSA investigation](kuksa_investigation.md) documents the
subsequent source comparison, exact revisions/licenses, manual arithmetic,
commands and limitations. **Level 2 DBC interpretation demonstrated on a public
source-reported vehicle excerpt; Level 4 independent physical accuracy blocked.**

KUKSA commit `23f81d0b847e4ac353c7cc2eeaa89a4cc0fe4053` supplies the selected
9,207,888-byte `candump.log` and 322,430-byte bundled `Model3CAN.dbc`. Both full
hashes are in `data/manifests/kuksa_model3.json` and checked before parsing.
The README associates these files with a 2018 Tesla M3, but the small log's
Unix-interpreted August 2020 clock contradicts attribution to a December 2021
trace/software 2021.40.6. Exact small-log origin, capture rights, upstream DBC
ancestry and physical calibration remain unresolved. Repository Apache-2.0 and
upstream model3dbc MIT licenses are recorded separately; no raw capture/DBC is
redistributed. X-CANIDS at `eed0d1efb42b3fd29bd39a4e1050b90b84d625da` documents
Sonata raw/signal data but provides no usable raw download in the reviewed tree,
no pinned DBC revision or capture license. Its described signals are same-DBC,
5 ms most-recent-value samples, not independent physical references.

Only narrow implementation extensions were needed: explicit DBC message-ID scope
preserving the original DBC hash, the conventional `kph` → `km/h` identity alias
with source units retained, and compact per-signal count/range summaries. The
three selected messages are not multiplexed; unsupported protocols still fail.
The existing sparse Recording adapter, quality and engineering modules were reused.
No v0.5 detector, dependency, resampler or new framework was added.

### Executed results

- First 10,000 original frames / 40.093851 s: all 10,000 decoded; 4,006 ID 0x118,
  1,994 ID 0x257, 4,000 ID 0x266; no malformed, unknown, wrong-length or decode errors
  in the subset. `limit_reached=true`; no whole-recording decode-coverage claim.
- Source has 191,831 lines and first-to-last numeric span 769.139591 s, measured
  separately without retaining a full decoded recording. Full source hash is used
  even for the bounded subset. No extracted source copy is written.
- Three manual vectors pass at 1e−10 absolute tolerance: pedal 12.8 %, rear motor
  power 4.5 kW, speed 3.04 kph. They validate DBC bit/scaling interpretation, not
  physical calibration. Ranges: speed −6.56–3.04 kph, pedal 0–12.8 %, power 0–4.5 kW.
- 249 negative-speed observations are retained and flagged by existing nonnegative
  speed screening; 1,745 mapped observations are numerically plausible. 8,006 frames
  have no mapped speed. Missing signals and unverified metadata are preserved.
- No numeric timestamp invalidity or reversal. Existing cross-message cadence
  screening flags 5,634 irregular intervals; that policy is not a CAN clock-fault
  detector. Date/clock authenticity is still unverified.
- All 9,999 energy intervals excluded because electrical measurements are absent.
  Rear-inverter power is not mapped to battery power. Sparse-frame analysis gives
  1,723 stationary candidates, 22 unknown, 8,255 insufficient evidence; no derivative,
  route, confirmed operating-state or total-energy claim is made.
- Default suite: **276 passed, 1 skipped** in 15.48 s, retaining all 263 prior tests.
  Optional `VCAN_KUKSA_DIR` integration: **1 passed** in 2.15 s. It verifies exact
  hashes, real-source values, original byte-offset payload lookup, the 10,000-frame
  cap, manifest reference configuration and refusal to overwrite reports.
- Tests for selected/unselected/unsupported DBC messages, invalid ID scopes, unit
  alias provenance, deterministic signal summaries and reproduction arguments use
  only authored synthetic fixtures. External data are never downloaded by CI.
- Virtual CAN demo: 20 samples, zero flagged. Existing tests still exercise original
  simulation, DBC, replay and exports. No physical CAN host or calibrated instruments
  were used.

### Storage audit

Starting tracked source: 79 files / 423,551 content bytes. Starting ignored outputs:
21 files / 400,616 bytes. The development investigation explicitly wrote four compact
reports/manifests totalling **41,830 bytes**, giving 25 outputs / 442,446 bytes.
Largest outputs remain historical synthetic JSON 82,205 bytes, demo JSON 78,948,
synthetic CSV 72,121 and feature CSV 54,569. The new CAN JSON is 19,660 bytes and
engineering/quality summary 9,235 bytes; no full 10,000-row export or plots were saved.
Raw inputs total **9,530,318 bytes**, once each outside Git. Research text/HTML probes
also stay external. No large archive was downloaded/extracted, no dataset copies or
new environment/package installs were required, and no files were deleted.

Reviewed source/license documents, original capture and any signed-off results need
separate owner-managed retention/backups; Git contains only code, small configurations,
synthetic tests and documentation. Run manifests retain their exact hashes and dirty
state. This sprint follows the existing [retention policy](data_artifacts.md).

### Clean-commit reproduction and final inventory

Implementation commit `2eee856ee6ba911862fddc47ab5656fd7118b0bb` was investigated
again with the same two external inputs (no second download). The clean manifest
recorded that exact Git commit, `working_tree_dirty=false`, all three reference
checks passing, and SHA-256 for each requested output. Four compact verified
artifacts totalled 41,766 bytes. The earlier development artifacts were retained,
not overwritten or deleted; they document a dirty-source exploratory run.

At that implementation revision: **85 tracked files / 461,624 content bytes**.
After the clean run: **29 ignored generated files / 484,212 bytes**. These figures
exclude `.git`, environments and external research inputs, whose two-file size
remains 9,530,318 bytes. No raw log, research DBC, workbooks, Parquet, archive or
runtime output appears among staged changes. Ignore checks explicitly cover them;
only scoped authored DBC fixtures are exceptions. The documentation-only follow-up
records this execution and does not change tested numerical code.

## v0.4.5 Interactive Engineering Workbench — 2026-11-13

Started at verified `377d68af559a27947a2693c39ebf3c6bfe5d742d` on
`dev/v0.4-real-can-validation`. Local/remote branch inspection found no existing
interactive-learning work to reuse. Work is isolated on
`feat/interactive-engineering-workbench`; main and the evidence branch are preserved.
Package version is `0.4.5.dev0`, a workbench development milestone, not a new
independent physical validation claim. The unavailable BusBench GIF was not
inspected; the written visual description was used without copied assets.

### Implemented and executed

- A single Streamlit entry point now opens Overview with six working module cards,
  a dark navy sidebar, light workspace, orange accents, technical labels and native
  controls. Previous data-source delivery moved into `telemetry_dashboard.py`;
  numerical import, Recording, replay, engineering and export implementations are
  unchanged. Two UI regression tests now navigate explicitly to Vehicle data
  before their original assertions; no baseline test case was removed.
- Offline educational DBC speed: `38 AD 21 03 0E 00 00 00` on 0x257 → raw 538 →
  3.04 km/h; changing AD to BD → raw 539 → 3.12 km/h. cantools performs decoding
  through existing VCAN loaders. Tests cover original big-endian RPM, authored
  signed 12-bit Motorola byte crossing, Intel mapping, invalid input and clearing
  stale results. Display traversal handles the Motorola bit-0-to-bit-15 jump.
- Network presets configure actual periods/phases, simultaneous releases, stopped
  transmission and user payloads. Logical timestamps are deterministic integers;
  original `simulator.frames`, SyntheticCodec and python-can virtual transport are
  reused. No bus occupancy/arbitration delays or production topology are implied.
  Maximum tested retention is 4004 events, without sleeps or source copies.
- Controlled missing-message, jitter and signal-step rules preserve exact event
  references, original payloads/times, thresholds and ground truth. Tests exercise
  no arrivals, strict threshold equality, calculated rates, unchanged inputs and
  inspector reset after a shorter run. These are educational rules, not v0.5
  production anomaly detection or confirmed faults.
- Learn CAN provides 20 beginner/detail FAQ entries and eight questions split
  across beginner/intermediate levels. Scoring, unanswered feedback, hints, retry,
  answer changes and contextual navigation are tested. No account, personal data,
  database or AI API is used.

### Verification evidence

Full suite: **324 passed, 1 skipped** in 17.23 s, retaining all 276 baseline cases.
The skipped case is the explicitly optional external KUKSA integration; enabled
separately against the previously retained inputs it passed (**1 passed**, 2.55 s).
Default tests do not download research data. The original virtual CAN CLI demo
processed **20 samples, zero flagged**. Existing replay, DBC, workbook quality,
engineering and export regressions passed. Locked dependencies are unchanged;
`pip check` and the offline documentation-link checker passed. A built wheel was
checked for the packaged `can_lab/data/education.dbc`, ensuring the teaching
resource is included without downloading a vehicle DBC.

Actual running UI was checked in installed Linux Chromium using the already
available Playwright runtime; no browser/frontend dependencies were added to the
project. Keyboard activation opened Frame Laboratory. Browser checks verified
payload recalculation, reset, network counts, fault evidence and a submitted
unanswered quiz score of 0/4. No page errors or Streamlit exception blocks occurred.
The server health endpoint returned `ok`. At 1024×768 there was no document-level
horizontal overflow; result labels were adjusted after laptop-width inspection.
This is targeted verification, not a formal accessibility audit or native Windows/
macOS test. The two [actual screenshots](workbench.md#actual-application-screenshots)
were deliberately captured at 1440×1080; no mockup/GIF is presented as running UI.

### Storage and limits

Starting tracked source: **85 files / 462,707 bytes**. Historical ignored outputs:
**29 files / 484,212 bytes**, unchanged through the experiments and tests. The only
new binary source artifacts are two requested actual documentation JPEGs:
`workbench-overview.jpg` 122,606 bytes and `workbench-frame.jpg` 97,200 bytes
(**219,806 bytes total**). They are permanent documentation evidence, not automatic
plot exports. Teaching inputs/results and quiz state stay in memory; no persistent
cache, research download, new environment, duplicated recording, ZIP or automatic
cleanup was introduced. A small verification wheel/build products remain ignored
or external. Existing inputs and historical reports were not deleted.

Independent physical validation still awaits the acquisition clarifications and
aligned references in the KUKSA investigation. The next workbench milestone should
measure learner usability/accessibility and native Windows behaviour, while keeping
production detector evaluation separate from teaching thresholds.

The staged-source audit measured 97 tracked files, approximately **0.76 MB** total
including 0.22 MB of screenshots; source remained below 0.8 MB. Ignored generated
outputs stayed at 484,212 bytes. The packaged teaching example was also decoded
successfully directly from the built wheel with isolated Python import paths
(raw 538, 3.04 km/h), without an external DBC or a new environment. Exact working
content-byte counts can be reproduced with `can-lab storage-audit` at this revision.

## v0.4.6 Visual CAN Engineering Studio — 2026-11-13

Started at `a5f783b6ec57c804303f6d0060b95304a78b24b4` on the existing workbench
branch. New work is isolated on `feat/visual-can-engineering-studio`. No reference
images were accessible beyond the pasted descriptions; no inaccessible illustration
was claimed as inspected. All new field/arbitration/vehicle diagrams are original
HTML/CSS/SVG driven by calculated values or explicitly scoped simulation data.

### Implemented scope and evidence

- Compact native segmented navigation replaces sidebar workspace radio controls.
  Original CAN, workbook quality, replay, engineering, reports, fault scenarios,
  FAQ and quiz remain accessible. Baseline navigation tests were adapted to the
  new control and release-experiment subview; none of the 324 existing test cases
  or their engineering assertions was removed.
- Standard 11-bit classical **data** frames expose SOF, identifier, RTR, IDE, r0,
  DLC, Data, CRC, delimiters, ACK and EOF, with following intermission explicitly
  outside the frame. DLC 0–8 is derived from actual payload length. The separate
  cantools DBC inspector retains its own required message length and still computes
  raw 538 → 3.04 km/h; changed payload computes 3.12 km/h.
- CRC-15/CAN uses 0x4599, initial/final XOR zero, no reflection, MSB-first unstuffed
  SOF through Data. Catalogue check `123456789` → 0x059E passes. Independently
  specified frame vectors: empty ID 0 → 0x0000; ID 0x123 / `11223344` → 0x11DA;
  ID 0x257 / `38AD21030E000000` → 0x04CD. A distinct polynomial-long-division
  calculation checks those remainders and appending CRC gives zero residue.
  Stuffing tests cover complementary insertion, inserted bits participating in run
  counting, source reconstruction and final-boundary insertion. Delimiters, ACK,
  EOF and intermission are outside that stuffed region. ACK is simulated link-layer
  receiver response, not application acceptance; ACK errors/retries are unmodelled.
- Actual wired-AND identifier arbitration withdraws recessive transmitters that
  observe dominant. Of 0x120, 0x124 and 0x3E0, cluster loses at identifier bit 9,
  BMS at bit 2 and 0x120 wins. Duplicate and unsupported IDs fail explicitly.
  This does not add physical occupancy/latency to the existing release scheduler.
- Differential illustration computes nominal single-ended levels and Vdiff for
  logical bits; equal deterministic common-mode noise cancels to floating-point
  precision. It does not model receiver range, asymmetry, real EMC or every CAN
  physical layer. Original/disturbed lines and logical/dominant state are inspectable.
- Vehicle SVG uses one paired segment, two end terminations, four existing-model
  publishers and passive Brake ECU. Dashed local motor/battery/sensor links do not
  create extra CAN nodes. Per-ECU reception is modeled broadcast observability;
  the existing single python-can observer validates actual frame delivery. No
  acceptance filters, separate receiver queues, gateways or production firmware
  are claimed. Frame index, payload, timestamp, DLC, supported synthetic decoding
  and modeled receivers follow the retained event. Other message IDs remain raw.
- Start/Pause/Previous/Step/Reset operate a bounded playhead, never random animation
  events. Native fragments run only during play, stop at the buffer end and pause
  on navigation. Manual reduced-motion mode disables automatic play; CSS also
  honours OS reduced-motion preference. ECU/bus click or keyboard inspection is
  isolated in one HTML component; its JavaScript only selects the local info panel.
  Pause to read that panel: changing the current event rebuilds it.
- Fault Investigation preserves its existing injection and evidence model and now
  compares normal/injected arrivals side by side. These educational thresholds are
  not the planned v0.5 evaluated detector or a confirmed hardware-fault diagnosis.

### Verification

Full dataset-free suite: **366 passed, 1 skipped**, 19.78 s in this execution.
The optional external KUKSA integration was separately enabled using retained
inputs: **1 passed**, 2.45 s; no dataset download was needed. Existing synthetic
virtual-CAN demo processed **20 samples, zero flagged**. `pip check` passed;
locked dependencies are unchanged. The offline local-link/heading checker passed.

Installed Linux Chromium/Playwright exercised the running app at 1024×768 and
1440×1080. Verified frame/CRC display, reactive payload decoding, component
keyboard and pointer inspection, real automatic fragment playback, pause stable
beyond two timer periods, reset, arbitration loss stepping, differential/noise
controls and disabled automatic play in manual reduced-motion mode. There were
no browser page errors or Streamlit exception blocks, and no document horizontal
overflow on the frame or vehicle views at laptop width. Server health returned
`ok`. A single actual topology-component screenshot was deliberately captured for
[the guide](workbench.md#visual-studio-experiments); historical screenshots remain.
This is targeted browser verification, not a formal accessibility or native
Windows/macOS validation claim.

### Performance, storage and remaining work

Existing retention cap remains **4004 events**. One measured maximum-size schedule
ran in **74.46 ms** here; that is an observation, not a cross-platform performance
guarantee or real-time bus benchmark. Playback is capped at **4.00 items/s** and
uses original logical timestamps without inventing physical wire delays. No
background timer continues while paused. No new runtime dependency, new environment,
large frontend framework, research archive, plot export or persistent cache was added.

Starting tracked content was **0.76 MB**; existing ignored generated outputs remain
**484.21 KB** across 29 files. The only new binary evidence is a deliberately captured
studio screenshot, **38.50 KB**. Exact audit byte counts and manifest/output hashes
remain integers internally; human-facing CLI/UI/script size summaries now select
decimal units and round to two decimals. Source/DBC verification and machine JSON
are unchanged. No datasets or temporary simulation outputs were staged, and no
historical evidence was deleted. The read-only audit provides the final revision's
tracked content measurement without treating `.git` or environments as source.

Deferred boundaries: wire timing/occupancy, errors/retries, transmission-line/EMC
solving, production ECU firmware, full sensor physics, per-node receive queues,
gateways and independent physical validation. Native Windows testing must check
the locked install, browser/fragment timing, SVG focus/keyboard controls, 1024×768
layout, OS reduced motion and the existing CAN/Excel workflows. Learner usability
and assistive-technology review are recommended before expanding scope. The KUKSA
physical-reference/acquisition evidence gate remains pending.

A built `0.4.6.dev0` wheel was also checked with isolated Python imports: the
packaged offline DBC still decodes raw 538 and the frame model calculates CRC
0x04CD, without external vehicle data or a second environment.

The staged revision's read-only inventory contained 104 tracked files totaling
approximately **0.85 MB**, including the new **38.50 KB** screenshot. Historical
ignored outputs remained **484.21 KB**. No new runtime dependency was introduced;
the verification wheel was **107.16 KB** and remained outside Git.

## v0.4.7 Automotive Visual Experience — 2026-11-13

Started at `07b55e68274cc3e412c4c3414bf9f366be0a4463`, preserving the visual-studio
branch. New development is isolated on `feat/automotive-visual-experience`.
This is a presentation/interaction milestone. The CAN/DBC, CRC-15, stuffing,
arbitration, differential calculations, event generator, fault rules and telemetry
analysis core were not rewritten. All 366 preceding passing tests remain intact.

### Implementation and boundaries

- Native Streamlit Light/Dark themes handle controls, charts and tables. The
  Appearance popover documents **⋮ → Light/Dark → Apply appearance**; Apply reads
  the public theme context and stores matching custom CSS/SVG tokens per session.
  It avoids private frontend theme APIs or global server-side theme mutation.
  This explicit synchronization accommodates the framework's theme-context delay.
- Six overview cards now include original inline SVG illustrations, concise
  descriptions/status, actions and hover/keyboard-focus feedback. No new assets
  are loaded from remote services. Light remains available.
- The original vehicle SVG is now a top-down illustrative EV with motor/controller,
  VCU, cluster, pack/BMS, passive ABS/ESC and passive airbag control. Four wheel-speed
  sensors connect locally to ABS/ESC; illustrative crash sensors connect locally
  to the restraint controller. Purple dashed paths are local harness/control
  illustrations, not CAN publishers or sensor/firmware physics.
- Exactly four simulated publishers remain. New safety/sensor objects do not
  generate CAN traffic. A single paired bus with two end terminations remains a
  broadcast segment. Additional passive reception is illustration/model assumption,
  not new per-node queues or independently verified vehicle topology.
- `visual_model` checks original event ID, payload, index, transmitter and timestamp,
  then provides the same paths for drawn conductors and animated markers. Motion
  stages TX branch, both bus directions and reverse receiver stubs; receiver
  flashes describe observability of the SAME frame. No random traffic is generated.
  Staging percentages are visual narrative, not propagation time, bitrate or wire
  occupancy. Pause/Step/Previous/Reset preserve the selected retained event; scenes
  restart their schematic cycle rather than preserving a physical wave position.
- Manual and OS reduced-motion preferences suppress wire motion. Native Python
  playback still owns event selection. SVG/SMIL renders only the selected cycle;
  no independent timer generates messages or grows an event buffer.
- Fault views mark threshold evidence and expected-but-unobserved release annotations
  without synthesizing packets. Signal-rate points are highlighted. Only the known
  synthetic Powertrain ECU / 0x100 is explicitly mapped to the motor-controller
  illustration; other cases report a limitation rather than inferring meaning
  from an arbitrary ID. Mapped diagrams use an actual source observation and retain
  all finding/event references. A red highlight is not a hardware-failure diagnosis.

### Executed verification

- Full suite: **375 passed, 1 skipped**, 18.06 s. New tests cover passive-node
  classification, unchanged publisher count/evidence, rejection of fabricated
  visual IDs/payloads, exact wire/motion path reuse, event-change/reset state,
  reduced motion, themes/icons and supported/unsupported fault mappings.
- The optional external KUKSA integration passed separately (**1 passed**, 2.34 s)
  using retained inputs; no research download was needed. The original virtual CAN
  demo processed **20 samples, zero flagged**. Locked runtime dependencies are
  unchanged; `pip check` passed. Default CI remains dataset-free.
- Running Linux Chromium/Playwright checks selected native Light and Dark and
  applied matching custom visuals, navigated via Overview actions, inspected a
  wheel sensor and passive airbag node by keyboard/pointer, exercised Start/Pause/
  Step/Previous/Reset and manual reduced motion, and verified missing-release
  component evidence. Light-mode frame decoding still displayed 3.04 km/h.
- Actual SVG motion was sampled on the drawn MCU branch: scene-clock samples near 0.05/0.20 s moved
  from approximately (364, 140) to (375–378, 140), remaining on the original
  conductor. The SVG clock continues during browser command round trips. These are
  SVG coordinates/animation times, not physical propagation measurements.
- Desktop 1440×1180 and laptop 1024×768 were checked; no document-level horizontal
  overflow or JavaScript/Streamlit exceptions occurred. Pause was checked after
  waiting beyond the selected event interval. Native Windows/macOS, assistive
  technology and formal contrast/usability audits remain outstanding.
- The two current screenshots are genuine browser captures: dark overview and the
  selected-event vehicle component. They are documentation evidence, not generated
  mockups. Historical screenshots were retained. Three exact portfolio sequences
  are documented in the guide; no GIF was generated.

### Storage and next steps

Starting tracked content was approximately **0.85 MB**. Historical ignored outputs
remain **484.21 KB** across 29 files. New screenshots are **99.50 KB** and
**44.48 KB** (**143.98 KB** combined). Calculations and manifests retain exact
byte counts; user-facing summaries use decimal units with two decimals. Inline
SVG/CSS and the existing component are used without a new runtime dependency,
frontend framework, data copy, persistent cache, archive or automatic plot export.
No historical engineering evidence was deleted.

Before advertising native Windows support, check the locked installation, native
browser appearance menu/context synchronization, SVG/SMIL timing/focus, reduced
motion, laptop scaling and original CAN/Excel workflows on that host. The layout
is an adaptable illustration, not OEM CAD or a production architecture. Physical
propagation, bus occupancy, EMC, braking/crash dynamics and real firmware remain
outside scope. The original KUKSA independent-physical-validation gate is unchanged.

The built `0.4.7.dev0` wheel also passed isolated offline imports, unchanged
four-publisher event generation, visual-node mapping and the known CRC 0x04CD
check. Its **112.09 KB** verification package remained outside Git.

Final staged tracked content is approximately **1.03 MB**, including the two new
requested screenshots. Ignored historical outputs remain **484.21 KB**; no runtime
dependency was added. The exact revision inventory is reproducible with the
read-only storage audit.
