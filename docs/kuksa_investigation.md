# KUKSA source-reported Tesla CAN investigation

**Result: Level 2 demonstrated on a public, source-reported vehicle excerpt.
Independent physical validation remains BLOCKED.** This is an executed engineering
investigation, not certification of vehicle accuracy or acquisition authenticity.
No raw capture or third-party DBC is included in this repository.

## Candidate comparison and selection

| Criterion | KUKSA CAN Provider — selected for bounded investigation | X-CANIDS — not selected |
| --- | --- | --- |
| Pinned source | `eclipse-kuksa/kuksa-can-provider` at `23f81d0b847e4ac353c7cc2eeaa89a4cc0fe4053` | `hellmarbecker/x-canids` at `eed0d1efb42b3fd29bd39a4e1050b90b84d625da` |
| Acquisition description | README calls the large trace a 2018 Tesla M3, software 2021.40.6; calls `candump.log` a smaller excerpt of it | ReadMe describes Hyundai LF Sonata 2017 e-VGT, Kvaser Memorator Professional HS/HS on OBD-II, six driving dumps and one idling dump |
| Raw availability and size | Direct `candump.log`: 9,207,888 bytes, 191,831 frames, three IDs; 769.139591 s first-to-last recorded span | Reviewed tree has descriptions, arbitration tables and parsing scripts, but no `raw/` or `sig/` files; direct `raw/dump1.parquet` returns 404. No usable download located in that revision; compressed bytes unknown. Described dumps have 2,915,982–4,817,590 frames, roughly 22–37 minutes |
| DBC association | README explicitly identifies bundled `Model3CAN.dbc`, 322,430 bytes, maintained by Josh Wardell; exact bundled bytes pinned | ReadMe identifies `hyundai_ccan_2015.dbc` and links OpenDBC's `hyundai_2015_ccan.dbc`; exact version not pinned, filename spelling differs |
| Signal/clock structure | Classical standard-ID candump, `elmcan`; three nonmultiplexed IDs; timestamp provenance caveat below | Parquet index is monotonic relative time at microsecond resolution; raw columns ID, DLC, bytes, label. `sig/` signals sampled every 5 ms using most recently received values |
| Independent reference | No independent instrumentation or authoritative measured value established | Published signals explicitly come from the same DBC; resampling/forward filling prevents naive row correspondence and is not independent physical evidence |
| Licensing | Repository LICENSE Apache-2.0; referenced upstream `joshwardell/model3dbc` LICENSE MIT, copyright 2019 Josh Wardell. Capture-specific acquisition/redistribution grant and exact upstream DBC ancestry not established | No LICENSE in reviewed tree and no dataset-specific grant located in ReadMe. OpenDBC license does not establish capture rights |
| Resource decision | Download only the 9.2 MB example and 322 KB DBC once outside Git; no large archive | No Parquet dependency installed and no large dataset downloaded |

The X-CANIDS ReadMe cites Jeong, Lee, Lee and Kim, *IEEE Transactions on Vehicular
Technology* 73(3), 3230–3246 (2024), DOI
[10.1109/TVT.2023.3327275](https://doi.org/10.1109/TVT.2023.3327275).
The cited paper is a published dataset description, not a measured-speed reference
for this Tesla capture. Availability conclusions apply to the reviewed URL/revision,
not a claim that the dataset is unavailable everywhere.

## Provenance and licensing caveats

The source [README](https://github.com/eclipse-kuksa/kuksa-can-provider/blob/23f81d0b847e4ac353c7cc2eeaa89a4cc0fe4053/README.md#provided-can-dump--and-dbc-files)
explicitly associates log and DBC. That is stronger than unrelated same-brand files.
However, `candump.log` starts at `1597242902.648455`, which is
2020-08-12 14:35:02.648455 UTC **if interpreted as Unix seconds**. This predates the
large trace filename `candump-2021-12-08_151848.log.xz` and the attributed 2021.40.6
software. The log also uses channel `elmcan`. KUKSA documents an ELM/OBDLink-to-virtual-CAN
bridge, so this name alone neither proves simulation nor authenticates capture hardware.
We cannot independently confirm that the small file is an unmodified excerpt of
the described 2021 vehicle capture, or which software generated it. Clock error,
replay or a different acquisition are possibilities, not established explanations.
No VIN, calibration record, route or synchronized instrument reference is provided.

DBC association and byte compatibility are demonstrated for the three selected
messages, not every model/year/software/bus. The bundled DBC `VERSION` is empty;
identify it by the KUKSA commit and SHA-256, **not** today's upstream model3dbc HEAD.
The upstream MIT license was reviewed at `c56c113c353d09b1a5dd57677461f02fe8b7c6ca`;
that is a licensing-source revision, not a claim that its DBC equals KUKSA's copy.
KUKSA has a repository-level Apache-2.0 LICENSE but the log has no per-capture license
header. No third-party log, DBC, extracted subset or raw-data test fixture is
redistributed here. Obtain source-owner clarification before redistributing one.

## Raw bytes, DBC interpretation and worked values

A line has `(timestamp) channel ID#payload`. `257` is hexadecimal arbitration ID
0x257, or decimal 599; payload bytes stay in transmission order. The DBC defines
which bits belong to each signal, endian/sign rules, scale, offset and unit. It is
a reverse-engineered specification, not an independent measurement of reality.

Only 0x118 (`ID118DriveSystemStatus`), 0x257 (`ID257DIspeed`) and
0x266 (`ID266RearInverterPower`) are selected. The full DBC has 159 messages,
29 multiplexed; explicit `--dbc-frame-id` scope keeps those unrelated definitions
out of the supported decoder. No multiplexing, CAN FD or extended-ID support was
added. Original full-DBC hash/bytes and the selected IDs are retained in manifests.

Three manual checks use original source line numbers (one-based):

| Line / signal | Byte interpretation independent of decoder execution | Expected / tolerance |
| --- | --- | --- |
| 9989, 0x118 `DI_accelPedalPos` | Payload `5C06851820800000`: byte 4 = 0x20 = 32; unsigned start 32, length 8, little endian; 32 × 0.4 | 12.8 %, absolute 1e−10 |
| 9995, 0x266 `RearPower266` | Payload `0900153215009401`: signed little-endian 11 bits starting at 0 = 9; 9 × 0.5 | 4.5 kW, absolute 1e−10 |
| 9997, 0x257 `DI_vehicleSpeed` | Payload `38AD21030E000000`: little-endian bytes 1–2 = 0x21AD; shift right 4 and mask 0xFFF → 538; 538 × 0.08 − 40 | 3.04 kph, absolute 1e−10 |

All three passed. Expected numbers are manual DBC-based arithmetic, **not sensor
measurements**. This independently checks decoder implementation against the
specified DBC, and establishes Level 2; it does not establish DBC/OEM accuracy.
The conventional `kph` spelling is explicitly normalized to `km/h` with factor 1;
original DBC/source units remain recorded. No magnitude-based conversion occurs.

## Executed bounded results

The first **10,000 original records** cover timestamps `1597242902.648455` through
`1597242942.742306`: 40.093851 s (minor float rounding in numeric reports).
All 10,000 decoded under the selected three-ID scope: 4,006 ID 0x118, 1,994 ID
0x257 and 4,000 ID 0x266. Unknown, malformed, wrong-DLC, unsupported and decode-error
counts were zero **in that subset**. The frame cap was reached; these are not
whole-file decoding statistics. Full source SHA-256 covers all 9,207,888 original
bytes, even though only the first 10,000 frames are retained. No subset file is made.

| Signal | Count | Minimum | Maximum |
| --- | --- | --- | --- |
| `DI_vehicleSpeed` | 1,994 | −6.56 kph | 3.04 kph |
| `DI_accelPedalPos` | 4,006 | 0 % | 12.8 % |
| `RearPower266` | 4,000 | 0 kW | 4.5 kW |

Only vehicle speed enters canonical Recording; motor/inverter power must not be
substituted for battery V×I or consumption. Other decoded signals remain in the
frame table/report. There is no voltage, current, SOC or temperature measurement
in this selected three-message source. No battery signals or charge/discharge
polarity are invented. One observation per frame and exact source byte offsets
are retained; optional integration tests read the original file at those offsets.

Negative speed values are preserved: 249 speed observations are flagged by the
existing nonnegative-speed policy. Reverse travel or incompatible semantics could
explain them, but neither is independently established. Do not take absolute values,
clamp them or call them confirmed sensor faults. There are 1,745 numerically plausible
mapped observations; 8,006 frames carry no mapped speed. All observations have
missing optional signals and unverified metadata. These overlapping summaries are
not a count of accurate/invalid CAN frames.

No timestamp reversal or invalid numeric timestamp was found in the subset.
Existing cadence screening reports 5,634 irregular intervals on interleaved
multi-rate messages; that is a heuristic anomaly count, not evidence of 5,634
invalid CAN timestamps. The physical clock/date attribution remains unverified.

Existing engineering analysis produced 1,723 stationary candidates, 22 unknown and
8,255 insufficient-evidence rows. Sparse observations reset derivative history;
no acceleration/session/route claim follows from those candidates. All 9,999
battery-energy intervals are excluded for absent electrical measurements. The
reported zero accepted-interval integral does **not** mean zero energy consumption.

## Reproduce without a large archive

From an installed repository checkout, choose an external directory. Commands
below download only the two pinned small inputs. Review source terms first. They
do not extract the approximately 150 MB large trace or install KUKSA services.

```bash
export VCAN_DATA_DIR=/tmp/vcan-kuksa-inputs
mkdir -p "$VCAN_DATA_DIR"
curl --fail --location --output "$VCAN_DATA_DIR/candump.log" https://raw.githubusercontent.com/eclipse-kuksa/kuksa-can-provider/23f81d0b847e4ac353c7cc2eeaa89a4cc0fe4053/candump.log
curl --fail --location --output "$VCAN_DATA_DIR/Model3CAN.dbc" https://raw.githubusercontent.com/eclipse-kuksa/kuksa-can-provider/23f81d0b847e4ac353c7cc2eeaa89a4cc0fe4053/Model3CAN.dbc
python examples/investigate_kuksa.py --data-dir "$VCAN_DATA_DIR" --output-prefix outputs/reports/kuksa --output-root outputs
```

Use an empty external directory for acquisition and fresh report prefix; avoid
re-downloading or overwriting retained inputs. The script checks hashes before
parsing and writes only four requested compact artifacts: CAN JSON/Markdown,
engineering/quality summary JSON and run manifest. It does not save a full decoded
Recording or images. The manifest includes the reference configuration, full input
hashes, selected IDs, source/Git revisions, dirty-tree state and output hashes.
A dirty-tree execution cannot be recreated from the recorded commit alone.

| Input | SHA-256 |
| --- | --- |
| `candump.log` | `a47687a2efc115e4cbfa4c2738049eb7987dde68fff6251002966cd5f886b2b5` |
| `Model3CAN.dbc` | `d54df533fc82f3dab11ddd0f5ae4d846f22c0a24b111d8cba2b93e79caf60151` |

For headless investigation with no files written, the equivalent generic command is:

```bash
python -m can_lab.cli investigate-can "$VCAN_DATA_DIR/candump.log" --dbc "$VCAN_DATA_DIR/Model3CAN.dbc" --dbc-frame-id 0x118 --dbc-frame-id 0x257 --dbc-frame-id 0x266 --mapping data/manifests/kuksa_mapping.json --provenance data/manifests/kuksa_model3.json --channel elmcan --time-basis unix --max-frames 10000 --preview-frames 6
```

The generic command alone does not run the script's three manual reference checks.
In the existing Streamlit raw-CAN workspace upload those two files, enter the three
DBC IDs, mapping JSON from `data/manifests/kuksa_mapping.json`, channel `elmcan`,
Unix basis and a 10,000-record cap. Inspect signals and frames; no images are saved.
UI uploads lack the script's pinned-source manifest check: use the CLI/script for
hash-verified reproduction and do not infer upload identity from a filename.

Ordinary CI remains dataset-free. Optional external verification:

```bash
VCAN_KUKSA_DIR="$VCAN_DATA_DIR" python -m pytest tests/test_kuksa_external.py -q
```

## Evidence gate and next acquisition step

Level 1 parser and Level 2 selected DBC interpretation are demonstrated. Numeric
ranges are compatible with low-speed activity, but documented operating conditions
and synchronized motion references are absent: **Level 3 is limited plausibility
screening, not independently established behaviour. Level 4 remains blocked.**
Request clarification of the small log's acquisition date, vehicle/software,
hardware/bus, relation to the large trace, capture rights and exact upstream DBC
version. Obtain synchronized independently calibrated speed/power measurements or
authoritative measured examples, with timestamp alignment, units and justified
error tolerances. Reference resolution and alignment error must inform physical
tolerances. A decoder-vs-DBC comparison, plausible range or another decode of the
same DBC cannot substitute for that evidence.

Source documents reviewed: [KUKSA LICENSE](https://github.com/eclipse-kuksa/kuksa-can-provider/blob/23f81d0b847e4ac353c7cc2eeaa89a4cc0fe4053/LICENSE),
[KUKSA ELM bridge description](https://github.com/eclipse-kuksa/kuksa-can-provider/blob/23f81d0b847e4ac353c7cc2eeaa89a4cc0fe4053/doc/elm.md),
[X-CANIDS ReadMe](https://github.com/hellmarbecker/x-canids/blob/eed0d1efb42b3fd29bd39a4e1050b90b84d625da/ReadMe.md),
[X-CANIDS reviewed tree](https://github.com/hellmarbecker/x-canids/tree/eed0d1efb42b3fd29bd39a4e1050b90b84d625da),
and [model3dbc MIT license](https://github.com/joshwardell/model3dbc/blob/c56c113c353d09b1a5dd57677461f02fe8b7c6ca/LICENSE).
