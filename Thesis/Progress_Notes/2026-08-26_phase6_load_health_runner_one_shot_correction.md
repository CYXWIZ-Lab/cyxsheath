# Phase 6 Load-Health Runner One-Shot Correction

## Outcome

The protocol-blocking result-overwrite defect is corrected without invoking LM Studio. The runner now validates its separate authorization before any cache operation, rejects an existing result, execution claim, or unexpected cache before host access, and consumes the one-shot authority by exclusively creating the dedicated cache directory and claim file. The claim binds the authorization and corrected runner digests and remains after success, failure, or a crash.

This is an implementation result, not execution authorization. `phase6_load_health_runner_execution_decision.json` remains absent, so the runner still returns exit code 2 before cache creation in the real workspace.

## Lean Boundary

The correction remains inside `run_local_model_load_health.py`, which already owns the frozen protocol and evidence lifecycle. No second process abstraction, dependency, thread, background service, or Sheath-core change was added. `monitored_process.py` and `lm_studio_windows.py` retain their previous identities.

The historical implementation result and blocked execution review remain unchanged. `phase6_load_health_runner_one_shot_correction_result.json` links their old runner/test identities to the corrected files, so the evidence chain records both the defect and its resolution.

## Validation

Nine runner fixtures pass on Python 3.12 and 3.14. The three new boundary fixtures prove that prior result bytes remain unchanged, a retained claim blocks a second invocation, and an unexpected cache blocks without mutation; all patch host observation out and record zero LM Studio calls. Ten correction mutations reject identity drift, weakened exclusivity or preservation, retry, runtime fixture use, execution authorization, and synthetic-canary permission.

The complete pilot-data suite reached 193/193 on Python 3.12 and 3.14. After the final test-only claim-binding assertions were added, the complete 3.12 suite and the final 29 correction-chain tests on both versions pass. Later complete 3.14 reruns overlapped 13 unrelated `cl.exe` compiler workers at approximately 100% host CPU and produced only pre-existing child-start timing errors, including the one-second PID-marker assumption. No production or correction assertion failed; the fixture timeout was not weakened or widened in this slice.

No authorization file, runner cache, LM Studio or `lms` process, or port-1234 listener existed at the checkpoint. No model-health or model-quality conclusion is permitted.

## Next Gate

Make a fresh validator-backed decision for corrected runner SHA-256 `e55394eabe43ccf7937e3428f3d7e3f80d8b5e15528ce0c719a829f8bbcf30b8`. Only a passing decision may create the exact one-shot authorization record. Execution remains a later step with no automatic retry.
