# Raw CAN investigation — v0.4 foundation

**Implemented; validated with synthetic fixtures. Real-vehicle validation BLOCKED.**
This is a reusable offline decoder/Recording adapter, not a completed real-CAN
validation milestone. No independently verified physical vehicle accuracy is
claimed. The previously studied SCUT workbook is already decoded and cannot close
this raw-frame evidence gap.

## Candidate assessment

Reviewed public repositories at the revisions below. Tool/DBC licensing does not
automatically license external captures. No complete qualifying candidate was
selected; therefore no research capture or third-party DBC is redistributed.

| Candidate / pinned revision | Available evidence | Decision and unresolved checks |
| --- | --- | --- |
| [commaai/opendbc](https://github.com/commaai/opendbc/tree/27fa1c5d8eed3238a0a78c52ff5abb6cdc807bd2) | MIT code/DBC library; vehicle definitions and associated commaCarSegments references | Arbitrary same-brand logs are not matched. A specific route, matching vehicle/interface/DBC revision, capture license, timestamp basis and independent physical reference are not established. Specialized route/rlog tooling would add acquisition scope. Capture bytes/duration not established; no bulk download |
| [commaai/cabana](https://github.com/commaai/cabana/tree/53f12b8d003135a1e25b5572f8628a614d71e48c) | MIT tool, deprecated. `src/demo.js` explicitly binds route `4cf7a6ad03080c90/2021-09-29--13-46-36` to CorollaDBC / `toyota_new_mc_pt_generated.dbc` | Stronger route/DBC association, but external raw route availability, capture redistribution license and independent reference measurements were not established here. Raw capture download bytes/duration unknown. Not selected |
| [collin80/SavvyCAN](https://github.com/collin80/SavvyCAN/tree/b085b6f6379f69052a66c6e2d2db6f6cd46af249) | MIT tool; example `candump.log` (489,938 bytes), `ThinkCity.dbc` (274,509 bytes), `LeafPowertrainBus.dbc` (2,001 bytes) accessible | Adjacency in examples does not document log/DBC/vehicle compatibility or independent reference values. Log starts on `vcan0`, so genuine vehicle acquisition cannot be inferred. Physical recording duration and example-specific capture rights not established. Not selected |

These are source assessments, not a claim of an exhaustive dataset search. Small
SavvyCAN files were inspected once outside the checkout; no complete phase archive
or research dataset duplication was produced. Before a real demonstration, obtain
a permitted capture with documented vehicle/software, bus/interface, timestamp
basis, exact DBC revision, capture license and reference bytes/values or independent
instrumentation plus tolerances. Pin hashes and confirm every mapped signal/unit.
Resolve this evidence gate before adding formats or reporting v0.4 completion.

## Supported contract and integration

`can_recording.investigate_candump` accepts seekable binary input or file paths and
strict configurable DBC text. It supports classical standard-ID integer signals,
little/big endian, signedness, scale/offset, declared units and DLC checks. Accepted
log syntax is `(seconds) channel ABC#payload`, not generic ASC/BLF/rlog. Timestamp
basis (`relative` or `unix`) is a caller declaration, not inferred from magnitude.
Exact timestamp text, original line number, frame index and byte offset survive
alongside the floating-second analysis value. Unsupported FD, RTR and extended-ID
records are counted; unsupported DBC FD/extended/multiplex/float definitions fail.
Unknown IDs, malformed rows, wrong lengths, decode failures and filters have
separate counters and bounded examples. Mixed selected channels require an explicit
filter. Coverage clearly states when a scan limit prevents a full-source claim.

Mappings explicitly identify frame ID, DBC signal and canonical target; declared
units must match canonical units exactly. No heuristic conversion, brand matching,
current-polarity assumption or signal fabrication occurs. The adapter produces one
`Recording` observation per decoded frame. Signals absent from that frame remain
missing. **No alignment, interpolation, filling or cross-frame power calculation**
is performed, even for equal timestamps. Existing quality review and engineering
functions consume this Recording. Optional RPM is retained without changing workbook
missingness counts. A sparse recording may legitimately have zero energy intervals.

A global `can_frames` table stores each payload once with all decoded signals.
Observations reference its table index; global DBC definitions record message,
start/length, endian, sign, scale/offset, unit and declared ranges. Source and DBC
metadata/hash plus the explicit mapping complete the trace. JSON and annotated CSV
Recording exports preserve that evidence; canonical v1 exports are intentionally
less expressive. Preserve the original capture as well.

## Dataset-free reproducible example

Install the locked dependencies and package as in the README. The source fixture
is already in the checkout, with narrowly scoped MIT licensing in
`tests/fixtures/raw_can/LICENSE`; it is not real CAN data. Its source manifest
verifies full log/DBC SHA-256 **before decoding**. Run from the repository root:

```bash
python -m can_lab.cli investigate-can tests/fixtures/raw_can/example.log --dbc tests/fixtures/raw_can/example.dbc --mapping tests/fixtures/raw_can/mapping.json --references tests/fixtures/raw_can/references.json --provenance data/manifests/synthetic_can.json --time-basis relative
```

Default execution prints a summary without writing files. For explicitly requested
compact JSON/Markdown and a run manifest, append:

```bash
--output-prefix outputs/reports/my-investigation --output-root outputs
```

Use a fresh prefix; existing files are never overwritten. Optional
`--include-recording --engineering-report` reuse existing recording and engineering
exporters and consume more space. `--max-frames 2 --preview-frames 1` demonstrates
bounded processing; `--channel vcan0 --start-s 0 --end-s 0.03` selects an explicit
window without changing source bytes or its complete-source hash. A reference
outside a selected subset is reported `not_observed`; failed or unobserved
references give exit 2, input/configuration errors exit 1. Exit 0 means successful
processing, not vehicle validation.

In Streamlit choose **Raw CAN Investigation (v0.4 foundation)**, select the
repository synthetic example and click **Investigate raw CAN**. Inspect identifiers,
coverage, DBC definitions, a bounded scatter plot, individual raw frames, quality
and reference results. Engineering analysis and compact downloads require explicit
buttons. Startup needs no dataset or network; no source copies or images are saved.

## Independent synthetic interpretation checks

Expected values below were calculated directly from authored bytes, not another
call to the decoder. Reference JSON binds them to the exact DBC SHA-256 and records
method/source/tolerances. This verifies parser/DBC interpretation on synthetic
vectors, not physical accuracy or an OEM signal definition.

| Signal | Manual calculation | Expected |
| --- | --- | --- |
| VehicleSpeed | little-endian `D3 02` = 723; × 0.1 | 72.3 km/h |
| EngineSpeed | big-endian `1F 40` = 8000; × 0.25 | 2000 rpm |
| Temperature | signed byte `23` = 35; offset −40 | −5 degC |
| PackVoltage | little-endian `A0 0F` = 4000; × 0.1 | 400 V |
| PackCurrent | signed little-endian `06 FF` = −250; × 0.1 | −25 A, polarity unspecified |

All five checks pass (exact or 1e−10 tolerance as configured). Fixture coverage:
7 scanned records, 6 parseable selected frames, 4 decoded, 1 unknown ID, 1 invalid
length and 1 malformed record. The one frame containing both V and I gives signed
−10 kW; the fixture has no accepted battery-energy intervals. The sign is original
measured current, not verified charge/discharge polarity. Reports always state
`physical_accuracy: not_established`, even if supplied reference checks pass.

Evidence levels remain distinct: parser correctness, DBC interpretation checks,
numeric plausibility, and independently verified physical accuracy. A DBC unit is
DBC-declared metadata, not independent sensor calibration evidence. See
[artifact policy](data_artifacts.md) for storage, bounded execution and manifests.
