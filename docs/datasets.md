# Volkswagen ID.3 and Porsche Taycan dataset investigation

Status: **unverified; adapter intentionally deferred** (2026-10-23).

No vehicle dataset, signal dictionary, DBC, license or vehicle-specific file was
present in the repository. The implementation therefore makes no claim about
ID.3/Taycan dataset availability, file structure or signal definitions.

Read-only discovery attempts in this execution environment:

| Source / request | Result |
| --- | --- |
| Crossref works search, `Volkswagen ID.3 Porsche Taycan dataset` | HTTPS proxy tunnel returned 403 |
| GitHub API repository search, `ID.3 Taycan dataset` | HTTPS proxy tunnel returned 403 |
| DataCite DOI search, `ID.3 Taycan` | HTTPS proxy tunnel returned 403 |
| Mendeley Data research-data search, `ID.3 Taycan` | HTTPS proxy tunnel returned 403 |

Attempted hosts: `api.crossref.org`, `api.github.com`, `api.datacite.org`,
`data.mendeley.com`. A denied search is not evidence that a dataset does not
exist. No search response, downloadable archive, sample headers or signal
reference could be inspected. No guessed adapter, fabricated citation or
production-vehicle CAN mapping is included.

## Evidence required before adding an adapter

1. Locate the publisher/research group's primary dataset page and record its DOI,
   version, license, vehicle model/year, measurement hardware and provenance.
2. Download a licensed sample and record archive/file checksums and actual file
   layout, encoding, delimiter, headers, timestamp precision and clock basis.
3. Inspect the accompanying dictionary/paper/DBC: signal identifiers, endian/sign,
   scaling, offsets, units, pack versus cell quantities, temperature location,
   sampling cadence, missing sentinels, and charge/discharge polarity.
4. Establish whether files contain decoded measurements or raw CAN. Raw frames
   require a validated signal definition, not a mapping guessed from vehicle name.
5. Preserve absent signals as null. Do not derive RPM for an EV or equate a
   heating/coolant temperature to battery temperature without evidence.
6. Add a vehicle adapter into schema v1, a provenance manifest and a small
   redistributable golden fixture. Verify expected physical values independently
   of the adapter and compare timing/units/polarity against documentation.

The generic profile importer can process documented recorded tables today;
it is not a verified vehicle adapter. `tests/fixtures/synthetic.*` and `mapped.csv`
are handwritten synthetic examples only. Their filenames, source fields, and
README make their provenance explicit. The `.log` fixture models the original
simulator's classical CAN frames. No actual vehicle recording is bundled.
