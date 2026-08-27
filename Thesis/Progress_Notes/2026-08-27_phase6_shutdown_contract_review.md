# Phase 6 Shutdown-Contract Review

## Outcome

The failed load-health result remains failed, but the next correction is now bounded. The most likely defect is a lifecycle-mode mismatch, not a ten-second timeout: the runner treated `LM Studio.exe --run-as-service` as standalone `llmster`, then called a command that LM Studio explicitly refuses when its desktop application owns the backend. Because the runner deleted the command's raw output, the exact exit-1 message cannot be proved retrospectively.

No LM Studio command, model load, inference request, HTTP server, CyxCode process, or Docker container ran during this review. The local server log was inspected but remains outside the repository; only its byte count, SHA-256, and privacy-minimized event sequence are recorded.

## Primary-Source Basis

LM Studio documents standalone `llmster` and the desktop app's headless service as distinct modes. Its [`daemon down` documentation](https://lmstudio.ai/docs/cli/daemon/daemon-down) states that the command stops `llmster`, not a running GUI app. The current official [`down.ts`](https://github.com/lmstudio-ai/lms/blob/main/src/subcommands/daemon/down.ts) implementation exits 1 when no backend is found or when `system.getInfo()` reports `isDaemon: false`; it requests shutdown only for `isDaemon: true`.

The official [`up.ts`](https://github.com/lmstudio-ai/lms/blob/main/src/subcommands/daemon/up.ts) and [`daemon status --json`](https://lmstudio.ai/docs/cli/daemon/daemon-status) interfaces expose `pid` and `isDaemon`. The runner should use those vendor-supported fields instead of inferring shutdown semantics from root-process liveness alone.

## Approved Correction

Fixture-only implementation is authorized:

- start with `daemon up --json`, require `status: running`, `isDaemon: true`, and a PID matching the owned root before any model load;
- fail before model load when the backend is desktop-service mode;
- retain numeric exits, bounded output lengths/digests, and an allowlisted diagnostic code;
- after unload and empty inventory, record status, call `daemon down` once, then poll `daemon status --json` until `not-running`;
- retain root exit, zero runtime artifacts, and zero port-1234 listeners as independent host cleanup gates; and
- keep forced cleanup as a safety fallback that fails acceptance.

Extending the root wait alone is rejected. The prior forced cleanup is not reinterpreted as graceful shutdown.

## Decision Boundary and Next Step

The validator-backed record is [phase6_shutdown_contract_review_decision.json](../pilot_data/review_evidence/phase6_shutdown_contract_review_decision.json). Run:

```powershell
python Thesis\pilot_data\validate_shutdown_contract_review_decision.py Thesis\pilot_data\review_evidence\phase6_shutdown_contract_review_decision.json
python -m unittest discover -s Thesis\pilot_data -p 'test_*.py' -v
```

Next, implement and fixture-test the mode-aware observations without invoking LM Studio. A later decision must separately select standalone `llmster` or another justified lifecycle contract and authorize any live diagnostic. No retry, installation, prompt, server, synthetic canary, or benchmark input is authorized here.
