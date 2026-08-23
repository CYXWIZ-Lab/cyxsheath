# CyxCode Integration Pipeline

## Status and Role

CyxCode CLI is the intended first coding-agent adapter and user-facing deployment surface for Sheath. It is not the Sheath itself and is not required by the research architecture. The core remains generator-neutral so the same experiment can use CyxCode or another agent without changing supervision or scoring.

The repository now implements the typed generator boundary, coordinators, constrained verification, and a concrete `CyxCodeGenerator` plus `SubprocessCyxCodeExecutor` in `sheath/src/sheath/cyxcode.py`. An independent full-history CyxCode clone exists under `integrations/cyxcode` at commit `42676876b63ed5a18957e3318272eb0d875a95fc`; acquisition and copy policy are recorded in [CyxCode_Local_Workspace.md](CyxCode_Local_Workspace.md). The Python coordinator has driven the pinned Linux image end to end against a deterministic local provider and exported an accepted schema-v1.7 record.

Verified source facts include the MIT license, the `cyxcode run` non-interactive command, snapshot selection through `--dir`, explicit `--model` and `--variant`, newline-delimited events through `--format json`, and full-session JSON through `cyxcode export`. The adapter must parse emitted `error` events rather than treating process exit alone as proof of success. The concrete invocation, isolation, parsing, artifact, failure, and acceptance rules are frozen in [CyxCode_Adapter_Contract.md](CyxCode_Adapter_Contract.md).

## Intended Runtime Pipeline

```text
Human request
     |
     v
CyxCode CLI user interface
     |
     v
Sheath pre-flight -> confirmed TaskContract
     |
     v
CyxCodeGenerator adapter -> GenerationRequest
     |
     v
Coding model edits a disposable snapshot
     |
     +-> exact response artifact
     +-> canonical patch artifact
     |
     v
Sheath single-attempt coordinator
     |
     +-> proposal validation and isolated checks
     |
     v
accept | revise | block | escalate
```

Pre-flight may challenge unsafe, contradictory, or materially incomplete human requirements before CyxCode invokes a model. Post-flight treats CyxCode output as a proposal, not proof. Generator-written claims and reported test results do not count as evidence unless reproduced through the authorized runner.

## Typed Adapter Contract

The generic boundary supplies:

- `GenerationRequest`: frozen task contract, current repository revision and source digest, attempt number, and exact revision feedback;
- `GeneratorAdapter`: a narrow `propose(request, snapshot, store)` protocol;
- `GeneratorProposal`: generator identity, request binding, exact response artifact, patch artifact, and explicit claims;
- `validate_proposal`: verifies generator/revision/attempt identity, artifact integrity, source isolation, canonical patch structure, and result-tree digest.

Run-record schema v1.7 then requires contiguous attempts, an append-only proposal event at the matching revision, reverified response/patch artifacts, and an attempt context binding each revision to its tool provenance. Later attempts can use a new ledger revision and source digest without rewriting the initial task contract.

The implemented `run_single_attempt` boundary records a typed `VerificationReport`, applies the fail-closed decision policy, and exports the complete v1.7 record. `run_bounded_attempts` additionally chains fresh snapshots from each validated result, records explicit logical revisions, invalidates old evidence, and sends exact decision reason codes as the next `GenerationRequest.feedback`. `ToolBackedVerifier` rebinds its policy template and optional backend factory to the proposal snapshot, gives later actions attempt-qualified IDs, and converts constrained-runner observations into current evidence; the coordinator rehashes that snapshot afterward and escalates drift. Schema v1.7 exports each attempt's policy digest, observed environment digests, actions, authorizations, observations, and artifacts. Deterministic fixtures cover content-derived proposal export and failure-response retention. The complete pinned-image path also preserves the canonical model-visible request, redacts provider secrets, restores protected metadata, extracts a trusted patch, and reaches an evidence-gated verdict.

The implemented `CyxCodeGenerator` owns only envelope validation, protected-metadata restoration, trusted patch extraction, response storage, and proposal construction. It does not own task normalization, mandatory checks, verdicts, or artifact acceptance.

## Trust and Experimental Boundaries

- CyxCode receives only the confirmed contract and permitted feedback for the current attempt.
- Its working directory is a verified disposable snapshot, never the source tree.
- The adapter preserves the immutable CyxCode version, model identifier, decoding settings, seed, prompt, response, exit status, and patch.
- Sheath owns tool authorization and required checks even when CyxCode has its own tools.
- Hidden tests remain unavailable to both generator and supervisor.
- Experimental conditions keep the CyxCode generator fixed; only the supervision condition changes.

## Remaining Experimental Preconditions

The source audit established the CLI surface, isolated XDG state, lack of a CLI seed, package type safety, and a passing 115-test adapter-relevant set. The lockfile and pinned Linux build identity are resolved; the full Windows suite remains non-clean and diagnostic. Before experimental use, the adapter still requires:

1. provider authentication with isolated experiment state;
2. token/cost extraction and provider-specific reproducibility limits;
3. enforced production network and process policy; and
4. cancellation, child-process handling, and interrupted-run cleanup evidence.

CyxCode does not need to expose a patch format: Sheath extracts the delta from the disposable snapshot through its trusted canonical patch boundary.

## Adapter Acceptance Criteria

The deterministic pinned fixture demonstrates that an immutable invocation receives the confirmed contract, touches only its snapshot, produces registered response and patch artifacts, survives proposal validation, reaches a verdict, leaves the source unchanged, and removes its transient directories. Fixture-level repeatability preserves content-derived proposal and patch identities; real-model output repeatability is not claimed.
