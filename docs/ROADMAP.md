# VCAN development roadmap

The versions describe engineering milestones, not claims that planned functions
already exist. This architecture/documentation revision preserves v0.3 numerical
behaviour. Company inspirations in [Workflows](WORKFLOWS.md) are not affiliations.

| Milestone | Status | Evidence gate |
| --- | --- | --- |
| v0.3 | Implemented foundation | Reproducible synthetic CAN and decoded-telemetry checks |
| v0.4 | **Next priority** | Independent real-recording / matching-DBC validation |
| v0.5 | Planned | Measured event/anomaly detection performance |
| v0.6 | Planned | Chronological held-out forecasting evaluation |
| v0.7 | Planned | Logged, human-reviewed AI tool orchestration compared with scripted automation |
| v0.8 | Optional research track | Measured delivery/recovery properties of a connected prototype |

## v0.3 — Validated foundation

Implemented: original synthetic ECU/CAN protocol, DBC encoding/decoding, supported
candump and canonical table imports, profiled decoded EV workbooks, independent
quality dimensions, deterministic engineering indicators, replay, local dashboard
and reports. Independent vectors cover the synthetic protocol; the public SCUT
workbook covers the decoded-data path. The [validation record](validation.md)
keeps exact test counts/platforms and source-review limitations.

Maintenance gate: the complete suite, portable virtual demo, dataset-free startup,
headless workbook workflow and report/interchange checks continue to pass. No
physical-CAN, OEM decoding, evaluated detector, agent or cloud claim follows from
that gate. Native Windows instructions need a Windows execution record before
being advertised as natively tested.

## v0.4 — Real CAN recording validation

**Next priority.** Validate raw frames through physical signals and traceable
engineering output using appropriately licensed public data.

Acceptance criteria:

1. Record source URL/version, license and permitted sample redistribution, hashes,
   capture conditions and timestamp basis; retain original identifiers/payloads.
2. Establish recording/DBC compatibility: vehicle/version/interface, IDs, frame
   type, lengths, byte order, sign, scale, offsets, multiplexing and units. Do not
   infer compatibility from a filename or brand alone.
3. Add only the necessary supported parser/decoder/provenance adapter, preserving
   current APIs and source evidence. Unsupported protocols remain explicit.
4. Check selected signals against an **independent** reference: documented golden
   bytes/values, independent instrumentation or traceable measurements, with
   tolerances and reference independence recorded. Reusing the same decoder as
   the expected result does not establish independent validation.
5. Report unknown-ID coverage, malformed frames, decode failures, missing signal
   coverage, clock limitations and the decision to reject/retain/skip each case.
6. Produce reproducible tests and a raw-CAN-to-signal/report validation artifact,
   preserving frame-to-signal back-references. Keep licensing-sensitive recordings
   outside Git and provide a reproducible local procedure where needed.

Physical bus testing is a separate evidence claim and requires a documented
interface/host setup; a successful offline decode alone is not hardware validation.
No dataset acquisition or v0.4 adapter is implemented in this milestone.

## v0.5 — Automated event and anomaly detection

Planned. Begin with engineering rules, statistical baselines, message timing,
missing/unexpected frames and signal discontinuities. Existing v0.3 screening
heuristics are useful inputs, not an already evaluated anomaly detector.

Acceptance criteria: define event labels, ground truth and unit/time assumptions;
separate tuning and evaluation recordings; compare baseline/rule variants;
report precision, recall, false-positive rate and detection delay per event type
with denominators and test conditions. Preserve source evidence for each alert
and document normal behaviours that resemble faults. Add ML only when an adequate
labeled/evaluable dataset exists; no unsupported model-accuracy claims.

## v0.6 — Predictive telemetry analysis

Planned. Treat decoded-signal forecasting and optional raw-message/traffic timing
forecasting as distinct problems with explicit targets and horizons.

Acceptance criteria: evaluate persistence and moving-average baselines before
classical/ML models; use chronological train/validation/test separation and
recording/session grouping; fit scalers/features only on training data; report
held-out error in signal units, horizon and inference cost. Compare against
baselines and document drift/coverage failures. Do not leak future samples across
windows or describe forecasts as diagnostic fault proof.

## v0.7 — AI-assisted diagnostic agent

Planned after appropriate validated tools/evaluation evidence exist. The agent
coordinates deterministic tools; it does not replace numerical methods.

Acceptance criteria: stable structured tool inputs/outputs, read-only defaults,
bounded authorised actions, logged tool calls, data/source/evidence references,
reproducible numerical results and explicit uncertainty. Demonstrate question-to-
tool selection, optional historical comparison/event replay and human-reviewed
findings. Evaluate against conventional scripted automation using tool correctness,
evidence coverage, unsupported-claim rate and investigation effort. Root-cause
candidates remain hypotheses unless independently established. No placeholder
agent functions, LLM service or framework are present in the current application.

## v0.8 — Connected telemetry prototype

Optional research track; local diagnostics must not depend on it. Scope a simulated
or actually supported CAN source, acquisition gateway, bounded persistent buffer,
secure transport, remote storage and an explicit delivery adapter. CAN traffic
and internet/application transport are different interfaces.

Acceptance criteria: define acquisition/receive clocks and synchronisation error;
measure loss, duplicates, ordering, latency distribution, timestamp consistency,
buffer limits and recovery after interruption/restart. Demonstrate authentication
and encrypted transport with controlled credential handling. Document replay,
backpressure, outage and failure tests. Report unsupported hardware/protocols;
no implied CAN FD/Ethernet/cloud support from a conceptual diagram.

## Scope and progression

No v0.4–v0.8 functionality is implemented as part of this restructuring. Keep
experimental models/agents/transport optional and separately evaluated. A claimed
milestone needs its evidence gate, reproducibility instructions and limitations,
not just a diagram, function name, library import or attractive dashboard.
