# Implementation Blueprint

## 1. Objective

Build the smallest auditable system capable of testing the thesis: does independent, evidence-grounded supervision improve repository-task outcomes? The first implementation is an orchestration service around an existing generator. It is not a new foundation model, IDE, autonomous platform, or replacement for compilers and tests.

**Current milestone:** [../sheath/README.md](../sheath/README.md) implements the contract, typed generator request/proposal boundary, single- and bounded-attempt coordinators, tool-backed verification, append-only revision/evidence ledger, explicit state machine, verified disposable workspace staging and restaging, bounded canonical patch extraction and fail-closed application, host/container executable authorization, content-addressed storage, fail-closed decisions, a constrained runner, and a digest-pinned Docker adapter. Run-record schema v1.7 preserves validated generator attempts, chronological proposal events, response/patch artifacts, and per-attempt policy, environment, action, authorization, observation, and evidence provenance; patch-record schema v1.0 preserves sorted binary-safe add, modify, and delete entries. Bounded attempts carry forward the prior result digest, create a fresh logical revision, invalidate evidence, expose exact decision feedback, and can reverify through distinct tool sessions. Repeated live fixtures produced identical source, result, patch, output, and sandbox digests across independent staging paths, reconstructed the declared result on fresh copies, left the source unchanged, and removed every copy. This is a partial Stage-0 core and narrow infrastructure evidence, not completion of the MVP definition in Section 12.

## 2. Planned Repository Layout

```text
sheath/
  pyproject.toml
  src/sheath/
    contracts.py       # TaskContract and constraint normalization
    ledger.py          # Append-only claims, actions, evidence, decisions
    risk.py            # Interpretable risk policy
    policy.py          # Hard permission and safety rules
    tools.py           # Non-executing tool policy and observation boundary
    supervisor.py      # Rule/tool checks and optional critic adapter
    generator.py       # Typed model-neutral request/proposal boundary
    coordinator.py     # One-attempt verification, decision, and export
    verification.py    # Snapshot-bound constrained tool checks
    runner.py          # Fail-closed isolated-backend coordinator
    artifacts.py       # Content-addressed, tamper-evident byte storage
    snapshots.py       # Verified writable copies and lifecycle cleanup
    patches.py         # Bounded canonical delta extraction and validation
    patch_application.py # Verified application to a fresh disposable copy
  configs/
    policy.yaml
    risk.yaml
    checks.yaml
  tests/
    unit/
    integration/
    fixtures/
  evals/
    tasks/
    hidden_tests/
    run_experiment.py
```

Python is proposed for the research harness because the initial implementation plan already uses Python-like schemas and ML tooling. This does not change the benchmark language scope of C, C++, and Python.

## 3. Typed Boundaries

### 3.1 Generator Interface

```python
class GeneratorAdapter(Protocol):
    @property
    def generator_id(self) -> str: ...

    def propose(self, request, snapshot, store) -> GeneratorProposal: ...
```

`GenerationRequest` freezes the task contract, current repository revision and source digest, attempt, and revision feedback. Attempt 1 must match the initial contract; later attempts may target ledger-recorded revisions without rewriting that contract. `GeneratorProposal` binds the generator identity and attempt to registered response and canonical-patch artifacts plus explicit claims. Validation requires artifact integrity, the expected source snapshot, and a result digest matching the generator workspace. Schema-v1.7 export requires contiguous attempts, a matching chronological proposal event, reverified artifacts, and an attempt context binding each revision to its tool provenance. The adapter must additionally preserve the exact model identifier, prompt, decoding configuration, seed, and CLI observation when available.

CyxCode CLI is the intended first adapter, not a dependency of the core. Its verified placement, trust boundary, required API facts, and live acceptance gate are defined in [CyxCode_Integration_Pipeline.md](CyxCode_Integration_Pipeline.md). The concrete `CyxCodeGenerator` now implements envelope-to-patch-to-proposal mapping; the remaining runtime join is a Python executor that drives the pinned binary.

DeepSeek Harness exposes typed `agent/*` and `tools/*` events, an append-only session log, and reversible plugin registrations. These make it a plausible future native host when in-flight interception is required. It does not replace the current CyxCode work: the project is in developer preview, would add a second agent runtime, and must be pinned and audited independently. No DeepSeek Harness or Cordis dependency enters the Stage-0 core.

Odysseus supplies additional implementation prior art for digest-bound action approval, untrusted-context handling, adaptive local-model context budgets, and stronger-teacher escalation. These are documented in [Odysseus_Source_Review.md](Odysseus_Source_Review.md), not imported. Its broad workspace scope, acknowledged lack of shell/filesystem sandboxing, large agent loop, and AGPL-3.0-or-later license make direct adoption unsuitable for the current MVP. A future external UI adapter or independently implemented approval refinement requires a measured CyxCode/Sheath limitation and a separate licensing decision.

The implemented `run_single_attempt` function requires `max_attempts=1`. `run_bounded_attempts` implements the revision loop for two or more attempts: it restages the prior result, records a content-bound logical revision, invalidates old evidence, supplies the previous reason codes as feedback, and stops on acceptance, block, escalation, wall-time overrun, or attempt exhaustion. Both accept a `VerificationReport` containing typed evidence, findings, and an optional tool session. `ToolBackedVerifier` translates constrained-runner observations into evidence and rebinds policy to each active proposal snapshot. Schema v1.7 exports each session through an `attempt_contexts` binding. The coordinator rehashes the snapshot after verification and escalates drift. CyxCode remains behind `GeneratorAdapter`; coordinators do not launch it directly.

### 3.2 Tool Interface

```python
class SandboxBackend:
    def execute(self, request: SandboxRequest) -> SandboxResult: ...

class ConstrainedRunner:
    def execute(self, action, check_ids) -> ExecutionOutcome: ...
```

The coordinator authorizes an argument-array action, substitutes the pinned absolute executable path, revalidates its size and SHA-256 identity immediately before dispatch, and supplies timeout and combined-output limits to the backend. A backend is eligible only when its typed profile declares filesystem and process isolation, disabled networking, resource limits, and executable-identity enforcement. Backend failures and contract violations become append-only error events.

An `Observation` contains start/end time, exit code, stdout/stderr artifact references, timeout and truncation status, environment digest, repository revision, and the sandbox backend ID, version, capability digest, and guarantees. Truncated output cannot pass a check. Shell text is never treated as proof without an actual observation.

The interface is transport-neutral. A disposable-container adapter, MCP-compatible isolated adapter, or another typed transport may implement it, but an unisolated host subprocess is not an acceptable backend. The decision policy—not the transport or generator—owns the mandatory-check list. Giving the generator tool access does not permit it to skip those checks.

### 3.3 Supervisor Interface

```python
class Supervisor:
    def assess(self, task, state, proposal, observations) -> Assessment: ...
```

`Assessment` contains findings, required checks, missing evidence, confidence, and a recommended decision. Hard-policy findings are generated outside the learned critic.

### 3.4 Decision Interface

```python
class DecisionPolicy:
    def decide(self, assessment, policy, budget) -> Decision: ...
```

Allowed decisions are `accept`, `revise`, `block`, and `escalate`. Each decision includes stable reason codes and evidence identifiers. Free-form explanation is supplementary.

## 4. State Machine

```text
RECEIVED
  -> CONTRACTED
  -> TRIAGED
  -> PROPOSED
  -> ACTION_VALIDATION
       -> BLOCKED
       -> EXECUTED
  -> ASSESSED
       -> REVISION_REQUIRED -> PROPOSED
       -> ESCALATED
       -> VERIFIED
  -> EXPORTED
```

Transitions are explicit and append-only. The raw task and original constraints are immutable. A user-approved contract amendment creates a new version linked to the old one. Evidence becomes stale whenever a later patch changes files covered by that evidence.

## 5. Minimal Decision Algorithm

```python
def run(task, generator, supervisor, tools, budgets):
    draft = normalize(task)
    contract = confirm_material_inferences_and_freeze(task, draft)
    state = initialize_ledger(contract)
    risk = triage(contract, repository_snapshot())
    checks = checks_for(risk, contract)

    for attempt in range(budgets.max_attempts):
        proposal = generator.propose(contract, state, state.feedback, budgets)

        violation = validate_actions(proposal.actions, contract, policy)
        if violation.is_hard_block:
            return export(decision="block", evidence=violation)

        observations = tools.execute_allowed(proposal.actions)
        state.append(proposal, observations)

        assessment = supervisor.assess(contract, state, proposal, observations)
        decision = decide(assessment, checks, budgets)

        if decision in {"accept", "block", "escalate"}:
            return export(decision, state)

        state.feedback = concrete_revision_request(assessment)

    return export(decision="escalate", reason="attempt_budget_exhausted")
```

Acceptance requires every mandatory check to reference current evidence. The supervisor cannot waive a mandatory check merely by assigning high confidence.

Normalization may flag a human request as ambiguous, contradictory, unsafe, or incompatible with repository policy. A material inference is never silently promoted to a requirement; it is confirmed, rejected by higher-priority policy, or escalated with its provenance intact.

## 6. Check Catalog

Checks have a stable ID, purpose, trigger, mechanism, severity, required evidence, timeout, and failure policy.

| ID | Trigger | Evidence | Default consequence |
|---|---|---|---|
| `scope.paths` | Any patch | Changed-path diff | Revise if unrelated; block if forbidden |
| `build.required` | Compiled project | Build observation | Revise |
| `tests.regression` | Behavior change | Selected test observations | Revise |
| `tests.hidden` | Evaluation only | Isolated harness outcome | Score; never reveal |
| `security.static` | Security-sensitive paths | Analyzer observation | Revise/block by severity |
| `claims.evidence` | Completion summary | Claim–evidence links | Revise |
| `policy.command` | Tool action | Authorization decision | Block |
| `api.compatibility` | Public API edit | Tests and structured diff | Revise/escalate |

Checks should be composable data, not scattered `if` statements. A new check is added only when it has a failure fixture and observable evidence.

## 7. Risk Policy

Version 0 uses transparent rules:

- **Deep:** authentication, authorization, secrets, cryptography, database writes/migrations, memory-unsafe code, concurrency, package publication, destructive operations, or broad public API changes.
- **Standard:** normal bug fixes, features, refactors, build changes, or multi-file edits.
- **Light:** comments, spelling, formatting, and documentation-only edits with no executable snippets or contract changes.

Risk can only increase automatically within a run. Decreasing it requires a recorded reason or human approval. The pilot logs feature values and outcomes; later calibration may replace hand weights, but not hard-policy triggers.

## 8. Supervisor Stages

### Stage 0: Rules and Tools

- parse task and local instructions;
- compare changed paths with scope;
- require build/test evidence selected from project metadata;
- validate final claims against observations;
- enforce permissions and budgets;
- use structured rubrics for architecture and security review.

This stage must be completed before any critic fine-tuning. It establishes how much value comes from system design alone.

### Stage 1: Learned Residual Critic

Invoke the critic only for registered ambiguous questions. Its structured response is:

```json
{
  "finding_type": "scope_violation",
  "constraint_id": "constraint-2",
  "location": "src/orders.py:88",
  "claim": "The repository-wide refactor is not required by the null-fix goal.",
  "required_evidence": ["task_contract", "changed_paths", "patch"],
  "confidence": 0.81,
  "recommended_action": "revise"
}
```

Schema-invalid output is rejected. The critic must cite input record IDs and cannot request unregistered commands.

### Stage 2: Optional Specialization

Separate adapters or experts are warranted only if error analysis demonstrates domain interference—for example, security recall improves at the expense of scope calibration in a single critic. Compare specialization with the same active compute and report routing errors. A fixed 3B/14-expert topology is not assumed.

## 9. CyxWiz Integration Contract

Audit the engine before building nodes. The minimum integration requires only file/table boundaries:

| Pipeline | Required input | Required output |
|---|---|---|
| Ingest | Source manifest | Raw Parquet/JSONL plus provenance |
| Curate | Raw records and filter config | Deduplicated split manifest |
| Label | Curated examples and annotations | Schema-valid task/run records |
| Train | Frozen dataset/model configs | Checkpoint, logs, metrics, checksum |
| Evaluate | Frozen tasks/conditions | Immutable run records |
| Report | Run records | Tables, figures, failure index |

If CyxWiz lacks a node, an external runner implements this contract. Research logic should not depend on GUI state that cannot be exported and versioned.

## 10. Verification Strategy

### Unit Tests

- schema acceptance/rejection;
- state transitions and immutability;
- resource acquisition/release and cleanup after timeout;
- concurrent ledger writes and atomic artifact publication;
- evidence invalidation after patch changes;
- risk routing;
- hard-policy decisions;
- budget termination;
- critic response parsing.

### Integration Tests

- a valid patch is accepted with current evidence;
- a failing test cannot be overridden by critic text;
- an out-of-scope patch receives a bounded revision request;
- a forbidden command is blocked before execution;
- missing context causes escalation;
- a revised patch invalidates prior tests and reruns them;
- artifact replay produces the same deterministic decisions.

### Adversarial Tests

- generator fabricates test output in prose;
- critic cites a nonexistent evidence ID;
- patch hides changes in generated/binary files;
- repository instructions conflict with system policy;
- malicious task text attempts to weaken the supervisor;
- conflicting human requirements attempt to force an unsafe or infeasible contract;
- repeated revision exhausts the budget.

## 11. Observability and Reproducibility

Each run exports:

- task and run schema versions;
- repository commit and clean/dirty state;
- condition, model, prompt/policy hashes, seed, and budgets;
- proposals, tool actions, observations, patches, findings, and decisions;
- environment and dependency digests;
- timing, token, and cost counters;
- artifact checksums and parent run for retries.

Logs may redact secrets, but redaction must be recorded. A result without a replayable run record is excluded as infrastructure failure.

## 12. Definition of MVP Done

The MVP is done when:

1. 20 fixture tasks run in isolated environments;
2. all state transitions and decisions validate against schemas;
3. acceptance cannot occur without current required evidence;
4. direct, instruction, self-reflection, and Stage-0 Sheath conditions share one harness;
5. the entire outcome table can be regenerated from run records;
6. no custom model is required.

The current 20 JSON scenarios do not yet satisfy item 1: they test supervisory state and decision behavior but do not run repository tasks in isolated execution environments.
