# Interactive Automotive Engineering Workbench — v0.4.5

The existing Streamlit application now opens on **Overview**, with dark navy
navigation, a light workspace, restrained orange accents, technical labels and
compact module cards. Configure → Run → Observe → Investigate → Explain guides
each experiment. This is the same application and analysis stack, not another
frontend. No account, network dataset, AI API or new runtime dependency is needed.
The unavailable BusBench GIF was not inspected; its written design description
informed a distinct VCAN interface without copied branding or assets.

## Start and navigate

Install the locked environment as in the README, then run from the repository root:

```bash
python -m streamlit run src/can_lab/dashboard.py --server.headless true
```

1. Open an Overview card or use the sidebar **Workspace** radio controls.
2. Choose **Vehicle data**, then expand **Existing data workflows** in the sidebar
   to select the original virtual ECU sample, synthetic candump/canonical imports,
   raw-CAN investigation or EV workbook analysis.
3. Existing workbook quality, synchronized plots, replay, engineering diagnostics
   and requested reports remain in that workflow. No source data is required to
   explore the three new experiments or Learn CAN.

Native controls retain keyboard operation and focus outlines. Bit highlights use
underlines as well as colour, and an accessible table includes every byte and
selected bit number. The layout was inspected at 1440×1080 and 1024×768 in Linux
Chromium. This is not a formal accessibility audit or native Windows/macOS test.

## Frame Laboratory

The offline KUKSA-derived speed example uses ID **0x257**, payload
`38 AD 21 03 0E 00 00 00`, start bit 12, length 12, Intel/little endian, unsigned,
scale 0.08 and offset −40. It produces raw **538**, physical **3.04 km/h**.
Edit byte AD to BD: raw becomes **539**, physical **3.12 km/h**. The interface
recalculates automatically after valid edits; Decode also provides an explicit
run action. Invalid edits clear the old result. Reset restores the example.

Inspect eight byte cells, binary values and highlighted DBC bits. Intel traverses
upward from the least significant signal bit. DBC Motorola traverses downward
from the most significant signal bit, jumping from bit 0 to bit 15 of the next
byte; it is not a reversed Intel range. The original synthetic 0x100 RPM signal
and an authored signed, cross-byte Motorola 0x300 example exercise that distinction.
`cantools` performs extraction/scaling through the existing VCAN codec loader;
the visual bit traversal is not a competing decoder.

`src/can_lab/data/education.dbc` is a small authored teaching specification. Its
speed facts derive from KUKSA's bundled DBC SHA-256
`d54df533fc82f3dab11ddd0f5ae4d846f22c0a24b111d8cba2b93e79caf60151`,
as worked in the [KUKSA investigation](kuksa_investigation.md); source spelling
`kph` is presented as equivalent `km/h`. It is not an OEM DBC, a redistributed
research recording or an independently physically verified measurement. Other
teaching definitions use the original synthetic protocol or expressly invented
signed values. Expand the calculation and evidence explanations in the module.

## Virtual CAN Network

Configure up to four educational publishers: powertrain, BMS, VCU and instrument
cluster. Set standard IDs, periods, first-release phases, enable flags, duration
and optional raw payload overrides. Default IDs 0x100 and 0x200 use the original
synthetic engine/temperature protocol; other IDs carry uninterpreted teaching
payloads. These names do not model Tesla topology or actual ECU firmware.

The presets change actual configuration: normal staggered phases, simultaneous
common-phase releases, one stopped powertrain publisher, and heterogeneous periods.
Press **Run network experiment**. Metrics, timeline, payload table and individual
event inspector reflect the completed run, not unsubmitted form edits.

The adapter reuses `simulator.frames`, `SyntheticCodec` and two `python-can`
virtual bus instances. It adds a bounded logical release schedule, not a second
signal generator or live transport implementation. Integer millisecond timestamps
are simulated; wall-clock receive timestamps are not presented as measurements.
The end time is inclusive: period 100 ms over 1000 ms produces 11 releases from
0 through 1000 ms. At most four nodes × 1001 releases = **4004 events** are retained.
Simulation durations are 100–10000 ms, periods 10–2000 ms, with no wall-clock sleeps.

Equal-time releases are sorted by ID for display only. Real standard data-frame
arbitration favours the lower ID and postpones other traffic; the workbench does
not calculate occupancy, bitrate, stuffing, delays, error frames or retries.
Duplicate transmitting IDs are rejected rather than pretending to model collisions.

## Controlled Fault Investigation

These are synthetic teaching rules, **not the evaluated v0.5 detector**. Real
recordings are never modified. The original sine-wave source remains available.

| Scenario | Computed evidence / strict threshold |
| --- | --- |
| Missing message | Stop nominal releases; compare silence through the observation horizon with expected period × multiplier |
| Timing irregularity | Add a deterministic delay to alternating releases; compare absolute inter-arrival deviation with allowed milliseconds |
| Signal discontinuity | Add an explicitly configured speed step to the original synthetic signal; compare absolute backward-difference rate with km/h/s threshold |

Equality does not exceed a threshold. Findings retain original event indices,
payloads, logical timestamps, values, intervals and thresholds. A no-arrivals case
records schedule origin and observation horizon instead of inventing a last message.
No results are saved automatically. Ground truth identifies the configured injection;
it does not turn every threshold crossing into a failed-ECU diagnosis. Logger gaps,
changed rates, clock uncertainty, normal transitions and incomplete captures are
alternative explanations in real investigations. No interpolation or automatic
repair is applied. Synthetic speed steps saturate at the original 8-bit limit 255.

## Learn CAN and Knowledge Check

Twenty FAQ expanders pair short beginner explanations with engineering detail,
including CAN/FD/OBD-II, arbitration, endian rules, message timing, provenance,
validation levels and diagnostic reasoning. Context buttons from each experiment
open Learn CAN with its topic identified. The Knowledge Check has beginner and
intermediate sets of four deterministic questions, covering eight categories.
Submit for explained feedback and score; unanswered questions receive no credit.
Hints are optional. Retry clears answers/results; changing an answer clears stale
feedback. Session state is local to the active Streamlit session, with no database,
identity collection or uploaded scores.

## Actual application screenshots

These two small JPEGs were captured from the running Linux Chromium application,
not generated mockups. Capture is deliberate documentation evidence; the app does
not export screenshots, plot images or ZIPs during normal use.

![VCAN overview with module cards and navigation](images/workbench-overview.jpg)

![Frame Laboratory showing the actual raw and physical calculation](images/workbench-frame.jpg)

## Evidence boundaries

- **Simulated:** node releases, payload waveforms and controlled faults.
- **Synthetic-validated:** independent expected bytes/values and deterministic
  experiment regressions. Correctness of a formula is not sensor calibration.
- **Real-data demonstrated:** the separate KUKSA investigation reaches Level 2
  on a source-reported public vehicle excerpt, with documented attribution caveats.
- **Independently physically validated:** not established; remains pending.
- **Planned:** production detector evaluation, forecasting, AI and connected delivery.

Future work should first measure usability and accessibility with actual learners,
then resolve the existing acquisition/reference evidence gate. Keep evaluated
production diagnostics distinct from these learning thresholds.
