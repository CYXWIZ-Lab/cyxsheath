# Sheath Stage-0 MVP

This package implements the smallest executable part of the thesis: an immutable task contract, an append-only evidence ledger, an explicit run-state machine, a typed model-neutral generator proposal boundary, and a decision policy that cannot accept a task without current evidence for every mandatory check. It also provides single- and bounded-attempt coordinators, a tool-backed verifier, verified disposable workspace snapshots, canonical binary-safe patch extraction and application, host/container executable identities, content-addressed stdout/stderr storage, a fail-closed runner, and a digest-pinned Docker backend. Completed runs export canonical JSON with resolvable proposals, per-attempt tool and environment provenance, executable actions, authorizations, observations, artifacts, sandbox profiles, and evidence plus a stable SHA-256 digest using run-record schema v1.7.

It deliberately contains no model, MCP adapter, CyxWiz integration, or training code. The optional `cyxcode` module is a narrow execution-result-to-proposal adapter; it does not add CyxCode or provider dependencies to the decision core.

## Run the tests

From this directory in PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

The 138 tests cover contract validation and immutability, legal and illegal state transitions, single- and bounded-attempt coordination, tool-backed verification, typed generator requests and proposals, CyxCode envelope/proposal mapping and subprocess prompt preservation, protected metadata restoration, success/failure artifact export, chained revision snapshots, generator/revision/attempt binding, canonical records and patches, executable authorization, sandbox dispatch, Docker hardening, timeout/output limits, cleanup, and complete Stage-0 acceptance/export flows. This includes exactly 20 synthetic control-plane scenarios with frozen expected verdicts and reason codes.

## Current boundary

Implemented modules are `contracts`, `generator`, `cyxcode`, `coordinator`, `verification`, `ledger`, `decision`, `state`, `records`, `tools`, `artifacts`, `snapshots`, `patches`, `patch_application`, `runner`, and `docker_backend`. The generator boundary freezes the task revision, attempt, and feedback, then binds a proposal to its expected generator identity, exact response artifact, canonical patch, source snapshot, and resulting workspace digest. The optional CyxCode adapter validates a canonical execution envelope, restores adapter-owned `.cyxcode`/`.opencode` roots, invokes a supplied trusted patch extractor, and creates a content-derived proposal. `run_single_attempt` composes one generator call, artifact validation, a typed verification report, evidence recording, decision, and schema-v1.7 export. `run_bounded_attempts` restages each revision from the prior validated result and supplies exact failure feedback until a terminal verdict or budget exhaustion. Schema v1.7 binds proposal revisions to their tool provenance. Snapshot staging, canonical patch replay, executable authorization, and the digest-pinned Docker adapter remain fail closed on drift, invalid paths, timeout, truncation, or cleanup failure.

The [container smoke fixture](tests/smoke/README.md) completed live on 2026-08-14 using Docker client/server 29.1.3 and a digest-pinned Python image. It observed both a blocked repository write and a failed outbound TCP probe, produced content-addressed stdout, stderr, and manifest artifacts, and left no matching container behind. This is narrow adapter evidence, not a complete security evaluation or benchmark result. See [../Thesis/Smoke_Test_Evidence.md](../Thesis/Smoke_Test_Evidence.md). To reproduce it with an approved local image, run:

```powershell
$env:PYTHONPATH = "src"
python scripts/run_container_smoke.py --image "python@sha256:<64-hex-digest>"
```

The writable-snapshot fixture separately proves that a container can mutate a verified copy, extract its patch, and reconstruct the same result on an independent fresh copy while the source remains byte-identical and both copies are removed afterward:

```powershell
$env:PYTHONPATH = "src"
python scripts/run_snapshot_smoke.py --image "python@sha256:<64-hex-digest>"
```

See [../Thesis/Snapshot_Smoke_Test_Evidence.md](../Thesis/Snapshot_Smoke_Test_Evidence.md). CyxCode is the first concrete generator adapter; its completed pinned-image bridge and remaining experimental limitations are documented in [../Thesis/CyxCode_Integration_Pipeline.md](../Thesis/CyxCode_Integration_Pipeline.md). The public Python adapter tests require no CyxCode checkout. The live `scripts/run_cyxcode_smoke.py` path additionally requires the separate experimental checkout described in [../integrations/README.md](../integrations/README.md); it is not yet a clean-clone public reproduction path. Tool-backed revision attempts export distinct policy, environment, action, authorization, and observation provenance.

The 20 JSON scenarios under `tests/data/` are regression fixtures, not benchmark evidence. They validate supervisory control behavior without claiming software-task or model performance.
