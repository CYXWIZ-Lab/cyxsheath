# Using Sheath Stage-0

## Purpose

Sheath Stage-0 is a dependency-free Python supervisory core. It turns a task into an immutable contract, gathers evidence against a specific repository revision, and returns `accept`, `revise`, `block`, or `escalate`. Generation is adapter-neutral: Sheath can evaluate a deterministic fixture or CyxCode proposal without trusting the generator to verify itself.

The package deliberately contains no trained model, training loop, MCP service, or CyxWiz graph. Those belong to later phases only if pilot evidence justifies them.

## How the Pipeline Works

1. `contracts.py` validates the task goal, repository snapshot, constraints, success criteria, risk, tools, and mandatory checks.
2. `snapshots.py`, `runner.py`, and `tools.py` stage a disposable workspace and constrain executable actions.
3. A `GeneratorAdapter` returns a typed proposal. CyxCode is one optional implementation.
4. `patches.py` and `patch_application.py` extract and replay binary-safe changes independently of model prose.
5. `verification.py` records tool-backed results in the append-only, revision-aware `EvidenceLedger`.
6. `decision.py` fails closed on unresolved questions, blocking findings, missing checks, failed checks, or stale evidence. `records.py` and `artifacts.py` produce auditable schema-v1.7 output and content-addressed artifacts.

## Minimal Runnable Example

From the repository root:

```powershell
$env:PYTHONPATH='sheath\src'
py -3.12 usage\examples\stage0_decision_example.py
```

Read [`examples/stage0_decision_example.py`](examples/stage0_decision_example.py) to see the public API. Change one evidence item's `passed=True` to `passed=False`; the same contract will return `revise`. Change the ledger revision before recording evidence and Sheath will reject the stale append.

## Run the Test Suite

```powershell
Set-Location sheath
$env:PYTHONPATH='src'
py -3.12 -m unittest discover -s tests -v
py -3.14 -m unittest discover -s tests -v
```

The last recorded full run passed 138 tests on each interpreter. Tests cover contracts, states, evidence, decisions, generator boundaries, snapshots, tools, Docker transport, patch handling, records, artifacts, and CyxCode adapter behavior.

## Docker Smokes

First inspect each command without executing a container:

```powershell
Set-Location sheath
$env:PYTHONPATH='src'
py -3.12 scripts\run_container_smoke.py --help
py -3.12 scripts\run_snapshot_smoke.py --help
py -3.12 scripts\run_cyxcode_smoke.py --help
```

The first two require `--image <digest-pinned-image>`. `run_container_smoke.py` checks the constrained runner boundary. `run_snapshot_smoke.py` additionally proves writable-copy staging, patch extraction/application, source preservation, and cleanup.

The deterministic CyxCode smoke has recorded Phase-5 defaults:

```powershell
py -3.12 scripts\run_cyxcode_smoke.py --artifact-root smoke-artifacts\cyxcode-local
```

It uses a loopback OpenAI-compatible fixture, not an external model. It validates the full adapter-to-verdict path while preserving prompt bytes, redacting secrets, leaving the source unchanged, and cleaning isolated state. A successful local rerun is infrastructure evidence, not model-quality evidence.

## Fail-Closed Behavior

An `accept` requires every mandatory check to have current, passing evidence. A revision invalidates older evidence for the decision. Unknown evidence references escalate; blocking findings block; unresolved material questions escalate. This is the central Stage-0 guarantee and the baseline against which a future learned critic will be evaluated.
