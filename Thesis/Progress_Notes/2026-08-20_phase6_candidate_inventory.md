# Phase 6 Candidate Inventory Snapshot - 2026-08-20

## Completed in this slice

- Registered 20 revision-pinned SWE-bench candidates in an append-only JSONL ledger: 7 C, 6 C++, and 7 Python cases across 10 repository families.
- Pinned SWE-bench Multilingual revision `846e647b9f33c0b51b739d005d13d85493c9af09` and SWE-bench Verified revision `78f471bf655a3137b2e8a75af1501690ec009ec3`.
- Captured each base commit, source date, pull request, published replay-image tag, and exact upstream license-file URI and SHA-256.
- Kept dataset licensing separate from upstream source licensing: the pinned Multilingual card declares MIT, while the pinned Verified card has no declaration and is recorded as `NOASSERTION`. Every per-use right remains undecided, and JQ's mixed repository notice remains unresolved at file scope.
- Added a dependency-free validator and five negative/ledger tests.

## Validation evidence

- `candidate_events.jsonl`: `sha256:3e7f0a2486496dc1d84533d0ed6bac2e5be3ca2bb3df3330bbb5237d9d19ad60`
- `validate_candidate_events.py`: `sha256:03535494c7a204ec762a4a8dec808777f6a286820aa52f00e7ab7c18e60cc681`

The inventory command reports:

```text
VALID: 20 events; 20 candidates; languages={'C': 7, 'C++': 6, 'Python': 7}; dispositions={'quarantined': 20}; repository_families=10
```

All five tests pass: expected balance, contiguous sequence enforcement, admission-rights enforcement, disposition/reason compatibility, and latest-event supersession.

## Limits

- All 20 candidates are `quarantined` under `artifact.incomplete`, `license.unclear`, and `privacy.review_required`; zero cases are admitted.
- No source snapshot, gold patch, test patch, replay log, annotation, or derived training record was added.
- Replay image references still use published `:latest` tags and have no resolved content digest.
- This purposive calibration inventory is not a prevalence sample or benchmark result.
- Only two C++ families are represented; the final seed requires at least five per language.

## Next pickup

The three-case vertical replay is complete and recorded in [2026-08-20_phase6_vertical_replay.md](2026-08-20_phase6_vertical_replay.md). Resolve its non-replay review gates and append decisions before applying the validated path to the remaining 17, double-labeling, or scaling.
