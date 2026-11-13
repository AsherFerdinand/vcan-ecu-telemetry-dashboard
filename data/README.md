# Data location and provenance

Commit only reviewed small configuration manifests here. Research recordings,
workbooks and archives are ignored. Keep originals outside this checkout:
`VCAN_DATA_DIR` can name a local external directory (default recommendation:
`~/VCAN-data`). `can_lab.artifacts.external_data_directory()` returns that path
without creating it. CLI input paths remain explicit; there is no automatic
acquisition or download.

`manifests/synthetic_can.json` identifies the deliberately small, authored fixture
under `tests/fixtures/raw_can/`, its exact recording/DBC SHA-256 and scoped license.
It is **synthetic evidence**, not an OEM recording. A real-data manifest must
record separately justified capture licensing and DBC compatibility; a URL or
successful decode alone does not establish either.

See [raw CAN investigation](../docs/raw_can_validation.md) for reproduction and
[artifact retention](../docs/data_artifacts.md) for backups and storage policy.

`manifests/kuksa_model3.json` pins the externally obtained KUKSA excerpt and full
DBC hashes, source revision and qualified license/provenance status. The separate
`kuksa_mapping.json` maps only speed; it contains no capture data. Reproduction
and the blocked physical-validation gate are in the [investigation](../docs/kuksa_investigation.md).
