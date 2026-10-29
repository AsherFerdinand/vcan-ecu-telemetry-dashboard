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
