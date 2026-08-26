# Phase 6 Load-Health Runner Execution Result

## Outcome

The locale-independent engine-inventory correction, repeated execution decision, and authorized one-shot runner execution are complete. The overall load-health gate failed closed, no retry is authorized, and the retained claim prevents a second invocation in this workspace.

The correction sorts normalized relative POSIX paths by raw UTF-8 bytes before compact JSON hashing. This replaces both the PowerShell culture-aware digest `389f3fc...` and Python Windows-`Path` digest `c016b534...` with the explicit digest `f40cc691...` for the same 20 files and 558,082,098 bytes. The boundary fixture now distinguishes uppercase/lowercase and hyphen/underscore ordering.

## Observed Result

The pinned Qwen2.5-Coder-7B Q4_K_M model loaded with exit code 0 using CPU-only settings, 8,192-token context, one parallel prediction, and the exact identifier. Inventory contained exactly that model, all 15 post-load samples completed, and no HTTP listener or inference was observed.

Observed resource gates passed:

- available-memory drop: 9,052,844,032 bytes, below the 12 GiB ceiling;
- minimum available memory: 21,241,774,080 bytes, above the 16 GiB floor;
- peak activation-tree working set: 6,369,894,400 bytes, below 12 GiB;
- peak activation-tree private bytes: 1,933,262,848 bytes, below 12 GiB; and
- maximum GPU-memory delta: 260 MiB, below 512 MiB.

Unload returned 0 and the loaded inventory became empty. `daemon down` returned 1, however, and the owned service root remained alive beyond the ten-second grace window. The runner therefore used its bounded owned-process cleanup and correctly rejected overall acceptance with `daemon_down_exit_nonzero` and `forced_cleanup_required`.

Final and independent checks found no matching LM Studio process, no port-1234 listener, no partial weight, no temporary CLI, and no retained raw CLI output. The canonical CLI, engine inventory, preference file, and model weight still matched their pinned identities.

## Evidence and Validation

- `phase6_load_health_runner_execution_decision.json` records the exact one-shot authorization and canonicalization transition.
- `phase6_load_health_runner_execution_result.json` separates observed load, inventory, and resource success from failed graceful-shutdown and overall gates.
- The ignored local cache retains the exact result and exclusive claim by SHA-256; raw CLI output was deleted by the runner.
- The complete pilot suite passes 222/222 on Python 3.12 and 3.14. Historical validators now accept source changes only through the digest-linked correction and execution-decision chain; earlier evidence records were not rewritten.

## Next Gate

Do not rerun the runner, invoke `lms` manually, send a prompt, start the HTTP server, or invoke CyxCode. Review the daemon-down exit and root-liveness contract using existing evidence and source first. Any new diagnostic or execution requires a separate validator-backed decision. The local synthetic canary and contamination gate remain blocked because the full load-health contract did not pass.
