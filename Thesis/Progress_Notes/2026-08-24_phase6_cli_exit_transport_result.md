# Phase-6 CLI Exit-Observation Transport Result

## Outcome

The one authorized identity-only probe passed. A digest-identical temporary copy of `lms.exe` 1.3.3 ran only `--help` through the synchronous Python transport and returned numeric exit code `0` in 13,828 milliseconds.

The command produced 1,207 stdout bytes and zero stderr bytes, below the 1 MiB combined-output ceiling. Only output lengths and SHA-256 digests are retained in curated evidence; the help text itself was not retained.

## Runtime and Cleanup Boundary

No LM Studio or `lms` process and no port-1234 listener existed before or after the probe. No daemon, model-load, inference, HTTP-server, CyxCode, or Docker command ran. Forced cleanup was unnecessary. The temporary client was deleted and the canonical client retained its pinned size and digest.

This proves that the synchronous transport can obtain a numeric exit from the exact temporary LM Studio client without shell interpretation or residual runtime state. It does not test daemon health, model loading, Qwen inference, coding quality, CyxCode integration, or the thesis hypothesis.

## Next Gate

The help-probe authorization is consumed. No automatic probe retry or load-health retry is authorized. Before any daemon or model command, make a separate integration decision specifying how the synchronous transport interacts with activation monitoring, timeouts, output retention, service-root ownership, inventory checks, and fail-safe cleanup.

Validate the result with:

```powershell
python Thesis\pilot_data\validate_cli_exit_transport_result.py Thesis\pilot_data\review_evidence\phase6_cli_exit_transport_result.json
python -m unittest Thesis.pilot_data.test_validate_cli_exit_transport_result -v
```

The direct validator and all eight result mutations pass on Python 3.12 and 3.14. The full pilot-data suite passes 135/135 on both versions.
