# Phase 6 Specification Snapshot - 2026-08-20

## Completed in this slice

- Froze `Pilot_Data_Specification.md` version 1.0.0. It defines one case as an immutable task, repository revision, proposal, evidence bundle, and outcome.
- Fixed the seed envelope at 100–300 adjudicated cases, including C/C++/Python coverage, repository-family caps, at least 25% `no_violation` cases, and category-support gates.
- Separated `admitted`, `quarantined`, and `rejected` states with stable append-only reason codes.
- Required SPDX license expressions and list versions while separately recording permission for analysis, metadata/label/source redistribution, and model training.
- Froze privacy, secret, defensive-security, lineage, exact/near-duplicate, contamination, double-label, adjudication, agreement, grouped temporal split, and replay rules.
- Added strict Draft 2020-12 manifest and annotation schemas with non-data examples.

## Validation evidence

- `Pilot_Data_Specification.md`: `sha256:6e882260d9a00afdfe8b4fed52c9bd68ce2add22f1cba8a992b5af332a547b2b`
- `dataset_manifest.schema.json`: `sha256:3f1be04bb93110bc0ed240f9f5ea54781eb504ea83c01d5ad5b1bad61de27d39`
- `annotation_record.schema.json`: `sha256:6942f9c8a44ebd9bf3cfaaf71a7ccaf310159f33ca710eccf3813d5c569e136f`
- Both examples validate with AJV 2020 in strict mode with date-time formats.
- Five negative mutations fail: unknown analysis rights for an admitted case, admission with rejection reasons, quarantine assigned to the seed split, `no_violation` with findings, and a positive annotation without findings.

## Next pickup

Phase 6 remains active. The append-only inventory and three-language vertical replay are complete; see [2026-08-20_phase6_candidate_inventory.md](2026-08-20_phase6_candidate_inventory.md) and [2026-08-20_phase6_vertical_replay.md](2026-08-20_phase6_vertical_replay.md). The next slice resolves non-replay gates for those three candidates before the remaining 17, double-labeling, or scaling. No critic training begins until the full Phase-6 and residual-task gates pass.
