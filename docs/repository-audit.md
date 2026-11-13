# Repository hygiene and exposure audit

The original checkout tracked a Linux home-directory snapshot alongside the
application. Phase 1 removes these categories from the Git index while leaving
local copies untouched and retaining all existing commits:

- `.bash_history`, `.bashrc`, `.bash_logout`, `.profile`
- `.cache/pip/` package/download cache and MOTD cache
- `.cache/ubuntu-insights/` OS/WSL telemetry and `.cache/ubuntu-pro/` logs
- `.config/ubuntu-insights/` consent settings
- `.motd_shown` and `.vscode/settings.json`

`.gitignore` now excludes these files, virtual environments, Python/build/test
outputs, editor settings, `.env` files, local `datasets/` and generated `outputs/`.
All new test fixtures are intentionally synthetic and safe to distribute.

## Exposure findings

The committed history contains 38 shell-history lines and OS telemetry containing
`insightsVersion`, `collectionTime` and `systemInfo` fields. Command history,
collection times and machine configuration should be treated as possible
operational/privacy exposure even when they do not contain credentials. The
removed files are unrelated to application development.

A heuristic scan inspected the current tracked files and **69 historical blobs**
reachable from local Git refs. It checked recognizable GitHub token and AWS key
patterns, private-key headers, credential-like assignments, and HTTP URLs with
embedded username/password. **No matches were found**. Values were not printed
or copied into this report. This limited pattern scan is not a comprehensive
secret audit: arbitrary passwords, uncommon tokens and remote-only refs may be
missed. No confirmed secret exposure is asserted.

Removing files from the current index does not remove historical public copies,
clones, forks, platform caches or ignored local files. Existing history was not
rewritten. If the owner identifies a credential in historical content, revoke or
rotate it first and separately coordinate any history cleanup; rewriting history
alone cannot invalidate a leaked credential. Review of privacy-sensitive historic
content remains recommended. No history rewrite, force-push or remote publication
was performed as part of this change.
