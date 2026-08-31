# Phase 6 LLMster Separator Canonicalization

## Outcome

The ZIP path boundary now safely accepts backslashes only as path separators and emits forward-slash canonical paths. This fixture-only correction responds to the consumed `member_backslash_rejected` result; it does not retry or inspect the real archive.

## Contract

Leading `/` or `\`, drive prefixes, empty segments, `.` and `..`, unsafe Windows segments, non-NFC raw names, directory-marker mismatches, and canonical or case-folded collisions remain rejected. Both separator spellings produce the same canonical inventory digest. Raw member names are not retained.

The implementation stays inside the cohesive, dependency-free inventory module. It adds no runtime module or dependency. The earlier decision validator was also corrected to bind historical source identities to its immutable baseline commit instead of requiring later authorized source versions to match.

## Validation

- 27 generated archive fixtures pass on Python 3.12 and 3.14.
- 10 design-decision mutations and 10 implementation-result mutations reject weakened boundaries.
- The complete Phase 6 suite passes 408/408 on both supported versions.
- Real archive identity reads, central-directory reads, member reads, extraction, installation, execution, and networking in this slice: zero.

```powershell
python Thesis\pilot_data\validate_llmster_separator_canonicalization_decision.py Thesis\pilot_data\review_evidence\phase6_llmster_separator_canonicalization_decision.json
python Thesis\pilot_data\validate_llmster_separator_canonicalization_result.py Thesis\pilot_data\review_evidence\phase6_llmster_separator_canonicalization_result.json
python -m unittest Thesis.pilot_data.test_llmster_archive_inventory -v
```

## Next Gate

Review this corrected checkpoint. A separately committed, validator-backed one-shot decision is still required before reading the real archive again. Extraction, Authenticode inspection, installation, runtime, and benchmark use remain blocked.
