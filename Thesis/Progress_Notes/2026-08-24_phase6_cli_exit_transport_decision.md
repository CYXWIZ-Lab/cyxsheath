# Phase-6 CLI Exit-Observation Transport Decision

## Decision

Replace PowerShell `Start-Process` exit observation with a narrow Python standard-library transport for future LM Studio control commands. The new `cli_transport.py` module executes one absolute command synchronously with `shell=False`, null stdin, separate byte outputs, a mandatory timeout, a combined-output retention ceiling, and a required integer return code. It adds no dependency and does not change the Sheath core.

The module is separate because the existing CyxCode executor owns generation, bridge payload, and snapshot semantics, while the Docker runner owns container streaming and abort behavior. Adding LM Studio lifecycle behavior to either would weaken their boundaries.

## Fixture Evidence

Eight fixture tests pass on Python 3.12 and eight pass on Python 3.14. They cover zero and nonzero numeric exits, separate output capture, literal metacharacter arguments without a shell, timeout failure without an exit claim, output rejection, absolute-executable enforcement, invalid limits, and missing executables. No LM Studio command ran during these tests.

The output ceiling is deliberately described as a post-completion retention-acceptance bound, not a streaming memory bound. The transport is therefore limited to low-output `lms` control commands and is not presented as a general-purpose process runner. Cleanup of any separately spawned LM Studio service remains the activation runner's responsibility.

## Authorized Probe

Exactly one identity-only probe may copy the pinned 120,772,792-byte `lms.exe` 1.3.3 client into ignored `.replay_cache`, verify its SHA-256, and run only `--help` with a 30-second timeout and 1 MiB combined-output ceiling. It must begin and end with no LM Studio/lms process or port-1234 listener, delete the temporary client and raw output, and record a numeric zero exit.

No daemon command, model load, prompt, HTTP server, CyxCode, Docker, synthetic canary, or benchmark input is authorized. A successful help probe proves only the client transport seam; another decision is required before load-health execution.

Validate the decision with:

```powershell
python Thesis\pilot_data\validate_cli_exit_transport_decision.py Thesis\pilot_data\review_evidence\phase6_cli_exit_transport_decision.json
python -m unittest Thesis.pilot_data.test_cli_transport Thesis.pilot_data.test_validate_cli_exit_transport_decision -v
```

The direct validator and all 16 focused tests pass on Python 3.12 and 3.14. The full pilot-data suite passes 127/127 on both versions.
