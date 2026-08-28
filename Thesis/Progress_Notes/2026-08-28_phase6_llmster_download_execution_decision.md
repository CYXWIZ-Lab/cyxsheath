# Phase 6 llmster Download Execution Decision

## Outcome

One exact archive request is authorized through the pinned `acquire_exact_archive` function. The prior storage blocker was remediated by deleting only the approved, Git-ignored `integrations/cyxcode/node_modules` dependency tree. CyxCode source, Git history, project files, the model weight, and research evidence were preserved.

The fresh baseline reports 36,168,814,592 free bytes against the frozen 35,433,480,192-byte pre-request floor, a 735,334,400-byte margin. The archive destination and `.partial` path are absent. The module must remeasure storage before and after streaming, so later disk drift still fails closed.

## One-Shot Boundary

The decision permits one invocation of `Thesis.pilot_data.llmster_archive_acquisition.acquire_exact_archive`. It is consumed when the function call begins, regardless of success, failure, or interruption. Automatic retry is forbidden; any later attempt requires a fresh decision.

Download authorization does not permit archive inventory, extraction, installation, executable launch, LM Studio operation, model load, prompt, HTTP server, CyxCode invocation, Docker operation, or benchmark input.

## Evidence and Validation

The decision is [phase6_llmster_download_execution_decision.json](../pilot_data/review_evidence/phase6_llmster_download_execution_decision.json). Ten mutation tests reject evidence or source drift, weakened storage bounds, margin errors, destination contamination, a second attempt, extraction, and benchmark authorization.

```powershell
python Thesis\pilot_data\validate_llmster_download_execution_decision.py Thesis\pilot_data\review_evidence\phase6_llmster_download_execution_decision.json
py -3.12 -m unittest discover -s Thesis\pilot_data -p 'test_*.py'
py -3.14 -m unittest discover -s Thesis\pilot_data -p 'test_*.py'
```

The complete pilot suite passes 316/316 on Python 3.12 and 3.14. No archive request occurred while making this decision.

## Next Gate

Invoke the pinned acquisition function once and preserve a privacy-minimized result. Do not extract or inspect the ZIP until a later archive-review decision.
