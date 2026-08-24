# Phase-6 Engine and CLI Recovery Result

## Outcome

The one authorized recovery execution failed closed before model loading. The hash-verified temporary `lms.exe` 1.3.3 copy started the LM Studio service, but the Windows PowerShell process object did not expose a numeric daemon-client exit code. Because the frozen contract requires every client to prove a zero exit, the runner did not invoke `lms load`.

There was no model activation, prompt, inference request, HTTP server, CyxCode process, or Docker container. Therefore this result says nothing about Qwen model health or coding quality.

## CLI Finding

The bounded LM Studio application-log window contains no `EPERM`, unlink, or failed-extraction event. The canonical CLI, temporary copy, active engine preference, and 20-file engine inventory retained their pinned digests. This is consistent with the temporary-copy mechanism avoiding the previously recorded lock, but absence of the error in one pre-load run is not enough to declare the lock resolved.

The new failure is evidence capture: `Start-Process` completed without a usable numeric exit property. Treating a missing exit as success would weaken the preregistered gate, so the runner stopped. The load command was never reached.

## Cleanup and Decision Boundary

Fail-safe cleanup removed the service process tree, temporary CLI, and raw runner output. Port 1234 remained closed, the loaded inventory was empty, no partial weight existed, and the engine, preference, and canonical client identities still matched. Forced process cleanup was required, so the protocol cleanup gate also failed even though final safety cleanup completed.

The authorized attempt is consumed. No automatic retry, prompt, server, synthetic canary, or benchmark input is authorized. The next action is a separate design decision for numeric CLI-exit observation—such as a synchronous invocation primitive—before any runtime command is executed again.

Validate the curated result with:

```powershell
python Thesis\pilot_data\validate_local_engine_cli_recovery_result.py Thesis\pilot_data\review_evidence\phase6_local_engine_cli_recovery_result.json
python -m unittest Thesis.pilot_data.test_validate_local_engine_cli_recovery_result -v
```

The direct validator and all eight mutation tests pass on Python 3.12 and 3.14. The full pilot-data suite passes 111/111 on both versions.
