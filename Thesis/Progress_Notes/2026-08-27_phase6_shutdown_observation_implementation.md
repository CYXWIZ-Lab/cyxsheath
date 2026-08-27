# Phase 6 Shutdown-Observation Implementation

## Outcome

The fixture-only lifecycle correction is implemented. The runner now requires structured `daemon up --json` evidence proving `status: running`, `isDaemon: true`, and a vendor-reported PID matching the owned service root before model load. Desktop-service mode and PID mismatch fail closed before load.

Shutdown now requires empty loaded-model inventory, a running standalone status with the owned PID, one `daemon down` call, and polling `daemon status --json` until `not-running`. A nonzero down exit, status timeout, ownership mismatch, remaining listener, or forced cleanup still fails acceptance. Control-command evidence retains only numeric exit, elapsed time, output lengths and SHA-256 digests, plus an allowlisted diagnostic code; raw control output is not retained.

## Lean Boundary

- `cli_transport.py` remains responsible only for bounded process execution.
- `lm_studio_lifecycle.py` owns vendor JSON parsing, mode checks, bounded diagnostics, and shutdown polling.
- `lm_studio_windows.py` owns Windows PID, creation-time, allowed-root, and force-cleanup scope.
- `run_local_model_load_health.py` orchestrates the protocol and evidence gates.

No dependency, thread, Sheath-core, model, or resource-setting change was introduced.

## Evidence and Validation

The append-only implementation record is [phase6_shutdown_observation_implementation_result.json](../pilot_data/review_evidence/phase6_shutdown_observation_implementation_result.json). Its validator and eight negative mutations reject source drift, desktop-mode loading, raw-output retention, missing status postconditions, dependency growth, runtime authorization, and installation authorization.

Run from the repository root:

```powershell
python Thesis\pilot_data\validate_shutdown_observation_implementation_result.py Thesis\pilot_data\review_evidence\phase6_shutdown_observation_implementation_result.json
py -3.12 -m unittest discover -s Thesis\pilot_data -p 'test_*.py' -v
py -3.14 -m unittest discover -s Thesis\pilot_data -p 'test_*.py' -v
```

The complete pilot suite passes 252/252 on both Python versions. No LM Studio, model-load, inference, HTTP-server, CyxCode, or Docker operation ran while implementing or validating this slice.

## Remaining Gate

Implementation evidence is not runtime evidence. A separate validator-backed decision must select a compatible lifecycle before any operation. Standalone `llmster` installation, live diagnostics, another load-health execution, synthetic canary, and benchmark input remain unauthorized.
