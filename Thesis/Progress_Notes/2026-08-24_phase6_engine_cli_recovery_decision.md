# Phase-6 Engine and CLI Recovery Decision

## Decision

Adopt the already installed and active llama.cpp CUDA/AVX2 `2.29.1` package for the next bounded load-health attempt. Do not downgrade to `2.28.2`, install another backend, update LM Studio, or change the selected Qwen weight or load settings. The 20-file engine package is pinned by a canonical inventory digest, manifest digest, server digest, and the active preference-file digest.

Invoke the pinned `lms.exe` 1.3.3 client only from one hash-verified temporary copy under `.replay_cache`. The canonical executable remains the source of the copy but is not invoked after staging. This leaves LM Studio's canonical extraction target unlocked and directly addresses the observed Windows `EPERM` unlink failure without adding a runtime, SDK, or wrapper dependency.

## Preserved Boundary

Exactly one fresh load-health execution is authorized. It retains CPU-only loading, 8,192 context tokens, one parallel prediction, the original memory and GPU ceilings, exact loaded inventory, 15 post-load samples, zero-exit CLI clients, and full cleanup. Inference, HTTP serving, CyxCode, Docker, synthetic prompts, benchmark content, and automatic retry remain forbidden.

The temporary client must match the pinned 120,772,792-byte executable before every invocation. Identity or clean-baseline failure stops before daemon startup. Cleanup must unload the exact identifier, stop only the activation process tree, remove the temporary executable and raw output, and leave no model inventory or port-1234 listener. The canonical client must retain its pinned digest after the attempt.

## Rationale and Next Gate

The final failed attempt already observed model load/unload and acceptable resource use under `2.29.1`; restoring the older installed backend adds another state transition without addressing the CLI lock. LM Studio documents `lms` as its bundled runtime-control CLI and `lms daemon up` as the daemon entry point. Its official bug tracker records the same Windows `EPERM` family when a running canonical `lms.exe` is replaced. The temporary-copy mechanism changes only which identical client file is executing.

Validate the decision with:

```powershell
python Thesis\pilot_data\validate_local_engine_cli_recovery_decision.py Thesis\pilot_data\review_evidence\phase6_local_engine_cli_recovery_decision.json
python -m unittest Thesis.pilot_data.test_validate_local_engine_cli_recovery_decision -v
```

If the decision and full pilot suite pass, execute the exact contract once and record a new result. A passing load-health result still does not authorize inference; the authenticated-server gate remains separate.

The direct validator and all eight mutation tests pass on Python 3.12 and 3.14. The full pilot-data suite passes 103/103 on both versions.
