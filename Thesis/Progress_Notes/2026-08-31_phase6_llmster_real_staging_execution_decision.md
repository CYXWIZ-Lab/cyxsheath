# Phase 6 LLMster Real-Staging Execution Decision

## Outcome

A validator-backed decision authorizes one exact call to the fixture-verified `stage_archive` function after this checkpoint is committed and immediately revalidated. Creating the decision did not stat, hash, open, or extract the real archive.

The call is pinned to ignored child `.replay_cache/llmster_staging/llmster-f3895cbd1a6e421fa754386f2d144803`. The parent exists, is not a symlink, is empty, and the child is absent. Fresh free space is 106,866,806,784 bytes, exceeding the 6,086,645,562-byte preflight floor by 100,780,161,222 bytes. The staging implementation still remeasures before and after writing.

## One-Shot Boundary

- Validate the committed decision immediately before calling the function.
- Consume authorization at `stage_archive` function entry, even on failure or interruption.
- Permit exactly one invocation and no automatic or manual retry under this decision.
- On success, retain the marker-owned child for a separate signature-review decision.
- On failure, allow only the implementation's matching-marker owned-child cleanup.
- Record aggregate counts and digests without member paths, contents, or absolute local paths.
- Keep Authenticode tooling, installation, binary execution, networking, benchmark input, and successful-child cleanup blocked.

Twelve mutation and live-precondition tests pass. The complete pilot-data suite passes 479/479 on Python 3.12 and 3.14.

## Validation

```powershell
python Thesis\pilot_data\validate_llmster_real_staging_execution_decision.py Thesis\pilot_data\review_evidence\phase6_llmster_real_staging_execution_decision.json
python -m unittest Thesis.pilot_data.test_validate_llmster_real_staging_execution_decision -v
python -m unittest discover -s Thesis\pilot_data -p 'test_*.py' -v
```

## Next Action

Commit and revalidate this decision, invoke the exact call once, and write a validator-backed result whether it succeeds or fails. Stop before signature inspection, installation, or execution.
