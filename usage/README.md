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
| Phase-6 pilot | Schemas, append-only candidate ledger, replay/review/capacity/model/activation/load-result evidence, 20 quarantined candidates | Active; real staging accepted and consumed, non-executing signature review design next |
| Learned Sheath critic | Model design and training after the deterministic pilot identifies residual errors | Planned for conditional Phases 9-10 |

## Current Boundary

The system is a deterministic Stage-0 engineering supervisor, not a trained Sheath model. The free CyxCode canary proved that a paid Zen account is unnecessary for the synthetic infrastructure check; it did not authorize benchmark submission or establish model quality. Standalone `llmster` was selected and its exact archive was acquired and inventoried. The sole real-staging call then succeeded, retaining 3,595 payload files and 91 digest-bound signature candidates in one marker-owned ignored child. That authorization is consumed. The platform-independent Authenticode review policy is implemented, and the separate Windows adapter design is frozen, but adapter implementation and real candidate review are not complete. Retained-child access, signature tooling, installation, runtime, prompt, HTTP server, benchmark proposals, retry, cleanup, and trained critics remain gated or unimplemented.

Superseding update (2026-08-30): the unused authorization above is retired. The versioned policy module alone may make one request; it retains the 1-GiB ceiling, requires 9 GiB before and 8 GiB after the write, and permits no retry. The complete pilot suite passes 331/331 on Python 3.12 and 3.14.

Acquisition result (2026-08-30): the single request succeeded, the ignored 867,394,409-byte archive independently matches the published SHA-512, and existing CLI/engine/model identities remain unchanged. The request authorization is consumed and the suite passes 341/341 on both Python versions. Inventory, extraction, installation, runtime, and benchmark use still require separate decisions.
