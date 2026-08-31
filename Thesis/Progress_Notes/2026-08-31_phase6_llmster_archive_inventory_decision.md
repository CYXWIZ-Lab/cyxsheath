# Phase 6 LLMster Archive Inventory Decision

## Outcome

A validator-backed decision now authorizes exactly one metadata-only inventory of the acquired LLMster ZIP. It does not authorize reading member contents, extracting files, installing the runtime, launching binaries, making network requests, or supplying benchmark input.

## Implemented Boundary

`llmster_archive_inventory.py` is dependency-free and separate from acquisition and lifecycle code. Before Python parses central-directory metadata, it verifies the exact 867,394,409-byte SHA-256/SHA-512 identity and manually checks the end-of-central-directory record. It rejects ZIP64, multi-disk archives, excessive entry or directory sizes, traversal and Windows-unsafe paths, case collisions, links and special files, encryption, unsupported compression, and declared decompression bombs.

The returned evidence is aggregate metadata: entry and size totals, compression methods, top-level components, sensitive executable suffix counts, and canonical digests. Individual member paths and contents are not retained.

## Validation

Fifteen adversarial fixtures pass on Python 3.12 and 3.14 and prove that `ZipFile.open` is never called. The predecision complete suite passes 356/356 on each version. Ten decision mutations reject identity drift, retries, second invocations, weakened ceilings, extraction permission, member reads, and signature overclaims.

```powershell
python Thesis\pilot_data\validate_llmster_archive_inventory_decision.py Thesis\pilot_data\review_evidence\phase6_llmster_archive_inventory_decision.json
python -m unittest Thesis.pilot_data.test_llmster_archive_inventory Thesis.pilot_data.test_validate_llmster_archive_inventory_decision -v
```

## Remaining Gate

Commit and revalidate the clean decision checkpoint, then invoke `inspect_exact_archive` once. The authorization is consumed at function entry even on failure or interruption. Authenticode verification, extraction staging, overwrite analysis beyond metadata, installation, rollback execution, runtime health, and model use each require later decisions.
