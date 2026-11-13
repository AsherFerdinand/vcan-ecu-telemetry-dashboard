# Data and artifact management

Source history belongs in Git, not repeated full-project ZIP backups. Reconstruct
milestones from a Git commit, `requirements-lock.txt`, reviewed configurations,
source hashes and explicitly obtained inputs. A dirty-tree run manifest warns
that its Git commit alone cannot reproduce modified source.

| Category | Location / retention |
| --- | --- |
| Permanent source | `src/`, `tests/`, `docs/`, `data/manifests/`; commit code, small licensed fixtures, mappings, golden vectors and source manifests after review |
| Reproducible generated | Ignored `outputs/reports/`, `outputs/figures/`, `outputs/temporary/` when needed; regenerate from inputs/configuration, save only on request |
| Important research evidence | External originals, independent reference measurements, signed-off results and non-repeatable outputs; retain separately, never delete automatically |

Set `VCAN_DATA_DIR` to an external data directory appropriate to the host. Inputs
are explicit CLI paths; no dataset copy, archive extraction, plot image, cache or
ZIP is produced automatically. There are no empty placeholder output directories.
Existing historical outputs are retained. Research extensions are ignored, with
narrow exceptions for the tiny authored fixtures. Ignore rules are an accident
barrier: inspect staged changes before committing and never force-add captures.

Back up original acquisitions and important evidence to separately managed storage
before considering any manual removal. Keep a human-reviewed inventory with SHA-256,
bytes, source URL/revision, capture conditions, license, reference method and
backup location/access owner. Verify the backup checksum. Store private backup
locations/access details separately from public manifests. Hashes identify bytes;
they neither establish measurement accuracy nor replace a backup. Historical SCUT
workbooks/reports and any non-repeatable measurements require separate retention;
Git does not back up ignored files. No originals or historical evidence were deleted
in this task. No cleanup utility is implemented.

## Read-only audit and bounded work

```bash
python -m can_lab.cli storage-audit --repository-root . --output-root outputs
```

The audit reports tracked working-file bytes (not compressed Git history), total
output bytes/count and ten largest outputs. It skips output symlinks and never
deletes. An explicitly requested investigation refuses existing output names,
paths outside its configured output root and symbolic-link traversal. This is
single-user local path protection, not a defence against hostile concurrent
filesystem mutation. There is no extension-based cleanup or deletion command.

Default CAN processing hashes at most 128 MiB in chunks, retains at most 10,000
scanned non-comment records and previews 100 frames. Oversized sources/lines fail
cleanly. Increase the byte limit explicitly for a reviewed larger source; hashing
still reads the complete original to establish its hash, while decoded retention
is frame-bounded. Channel/time filters preserve original line/byte references and
do not write a subset copy. UI scan limit is 20,000 and scatter preparation at
most 2,000 points. Files already uploaded through Streamlit occupy its upload
buffer; the bounded decoder does not claim to stream the browser upload itself.
DBC input is limited to 2 MiB / 10,000 signal definitions. No decoded cache is used.

Requested CAN report manifests record input/DBC hashes and metadata, decoder
versions, Git commit/dirty state, mappings, limits, reference configuration/results,
UTC execution time, output hashes/relative paths and reproduction arguments.
Missing provenance is explicit `unknown`, never inferred. External input arguments
use replaceable directory placeholders, not private absolute paths. Supply public
HTTPS URLs without credentials/query tokens. Manifests are execution records;
reviewed validation results should be backed up as important evidence separately.
