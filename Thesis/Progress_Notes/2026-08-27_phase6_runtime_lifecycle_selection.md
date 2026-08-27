# Phase 6 Runtime-Lifecycle Selection

## Outcome

Standalone `llmster` is selected as the only reviewed LM Studio lifecycle compatible with the frozen experiment contract. The desktop headless service is rejected for this bounded path because the vendor states that `daemon down` stops `llmster`, not the desktop app. Forced desktop termination remains a failed safety fallback, and a direct llama.cpp server would add an unvalidated parallel runtime path.

This is a source-and-evidence decision only. No installer, archive, runtime, model, HTTP server, CyxCode process, or Docker container was downloaded, installed, or invoked.

## Why Installation Is Still Blocked

LM Studio's official Windows command streams a mutable installer into PowerShell. The reviewed installer identifies version `0.0.21-2`, downloads an x64 archive, executes its `llmster.exe bootstrap`, and may modify `PATH`. Its SHA-512 lookup can return no checksum, and checksum verification can also be skipped after a hashing error. Those upstream conveniences do not satisfy this project's pinned-artifact and fail-closed requirements.

The existing desktop CLI, engine, and model state may share the same LM Studio home. A preflight must therefore pin the installer and archive, require the published checksum, identify overwrite scope, disable path modification, preserve the existing installation and weight, and define rollback before one separately authorized installation attempt.

## Primary Sources

- [Headless modes](https://lmstudio.ai/docs/developer/core/headless)
- [`daemon up --json`](https://lmstudio.ai/docs/cli/daemon/daemon-up)
- [`daemon status --json`](https://lmstudio.ai/docs/cli/daemon/daemon-status)
- [`daemon down`](https://lmstudio.ai/docs/cli/daemon/daemon-down)
- [Windows installer source](https://lmstudio.ai/install.ps1)

## Evidence and Validation

The decision record is [phase6_runtime_lifecycle_selection_decision.json](../pilot_data/review_evidence/phase6_runtime_lifecycle_selection_decision.json). Nine negative mutations reject evidence drift, desktop selection, forced-cleanup acceptance, mutable shell execution, checksum-risk concealment, download or installation permission, runtime-health overclaim, and model drift.

```powershell
python Thesis\pilot_data\validate_runtime_lifecycle_selection_decision.py Thesis\pilot_data\review_evidence\phase6_runtime_lifecycle_selection_decision.json
py -3.12 -m unittest discover -s Thesis\pilot_data -p 'test_*.py' -v
py -3.14 -m unittest discover -s Thesis\pilot_data -p 'test_*.py' -v
```

The complete pilot suite passes 262/262 on both Python versions. The next step is a separate pinned acquisition-preflight decision, not `irm https://lmstudio.ai/install.ps1 | iex`.
