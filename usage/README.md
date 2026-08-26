# Sheath Usage Guide

This folder is the operator guide for the software and research evidence implemented so far. It explains how to run the dependency-free Sheath Stage-0 supervisor, validate the Phase-6 pilot records, and exercise the isolated CyxCode adapter. The thesis argument and future design remain in [`Thesis/`](../Thesis/README.md).

## Start Here

From the repository root in PowerShell:

```powershell
py -3.12 --version
$env:PYTHONPATH='sheath\src'
py -3.12 usage\examples\stage0_decision_example.py
```

Expected final output:

```json
{"evidence_ids": ["evidence-scope", "evidence-tests"], "reason_codes": ["mandatory_checks.current_and_passed"], "verdict": "accept"}
```

The example creates an immutable task contract, records revision-bound evidence, and asks the fail-closed decision policy for a verdict. It does not invoke a model or modify a repository.

## Guide Map

- [Environment and Operations](Environment_and_Operations.md): prerequisites, shell setup, output locations, and troubleshooting.
- [Sheath Stage-0](Sheath_Stage0.md): implemented components, execution flow, examples, tests, and Docker smokes.
- [CyxCode Adapter](CyxCode_Adapter.md): the model-generation boundary, isolated adapter flow, focused checks, and safe canary status.
- [Pilot Data and Evidence](Pilot_Data_and_Evidence.md): benchmark-project definitions, Phase-6 ledger, validators, evidence interpretation, and research restrictions.

## What Exists Today

| Area | Current capability | Status |
|---|---|---|
| Sheath core | Contracts, evidence ledger, state machine, constrained tools, snapshots, patch replay, artifacts, verification, and verdicts | Implemented; 138 tests pass on Python 3.12 and 3.14 |
| CyxCode adapter | Canonical prompt to isolated CLI session, explicit export, redaction, trusted patch extraction, cleanup, and proposal mapping | Python fixture public; experimental live bridge remains a separate checkout |
| Free-model canary | One generated arithmetic task through `opencode/mimo-v2.5-free` | One-shot infrastructure check completed |
| Phase-6 pilot | Schemas, append-only candidate ledger, replay/review/capacity/model/activation/load-result evidence, 20 quarantined candidates | Active; fresh runner decision blocked on engine-inventory ordering mismatch |
| Learned Sheath critic | Model design and training after the deterministic pilot identifies residual errors | Planned for conditional Phases 9-10 |

## Current Boundary

The system is a deterministic Stage-0 engineering supervisor, not a trained Sheath model. The free CyxCode model proved that a paid Zen account is unnecessary for the synthetic infrastructure canary. It did **not** authorize real benchmark submission, establish model quality, or complete Phase 6. The public repository does not vendor the experimental CyxCode worktree, so clean-clone users should run the Python fixture path and curated validators. The rights audit retains Astropy and blocks free MiMo benchmark use; see [What Astropy Means Here](Pilot_Data_and_Evidence.md#what-astropy-means-here) before operating on pilot records. The exact local Qwen2.5-Coder-7B Q4_K_M weight is checksum-verified, Git-ignored, and symbolically imported. The synchronous CLI transport, identity-only `lms --help` probe, integration design, and runtime-blocked activation runner fixtures pass. The reviewed result-overwrite defect is corrected: prior state blocks before host access, and a retained exclusive claim prevents a second invocation or crash retry. The fresh execution review still blocks authorization because the recorded engine digest uses PowerShell culture-aware ordering while the runner recomputes the same 20 files in Python Windows-path order. A locale-independent identity correction and another decision are required; no daemon, model load, prompt, HTTP server, or genuine benchmark proposal is authorized.
