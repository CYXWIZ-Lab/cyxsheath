# Findings and Traceability

## Source Inventory

The repository is a Markdown research workspace. The source documents serve different roles:

| Source | Contribution | Evidentiary status |
|---|---|---|
| `Research_Thesis.md` | Original mission, scope, questions, hypotheses, capability model, safety principles | Proposal |
| `CyxWiz_Implementation_Plan.md` | Dataset schema, six graph pipelines, MVP, roadmap | Design proposal |
| `Evaluation_Benchmarks.md` | Capability tracks, 0–5 rubric, initial 100-task mix | Evaluation proposal |
| `same_hello_query_plus.md` | Wisdom framing, Sheath architecture, dialectical loop, patterns, model/data ideas, and extensive self-critique | Exploratory design record |
| `Hello Query.md` | Earlier conversation lineage, benchmark/code sketches, implementation proposals, peer critique, and superseded drafts | Exploratory provenance; no executed results |
| `debate_doc2.md` and `doc3.md` | Cognitive exercise and early theoretical synthesis | Hypothesis-generation only |
| `Meetup_Pitch.md` | Public narrative and proposed demonstration | Communication artifact |
| `Readme.md` | Repository purpose and research discipline | Project guide |
| `tolook.md` | DeepSeek-R1 detour, guessed DeepSeek Harness claims, Cordis discussion, and speculative stitched thesis | Exploratory provenance; corrected in `Tolook_Source_Review.md` |

At the start of the source audit, no executable implementation, dataset, benchmark output, trained checkpoint, experiment manifest, or Git history was found. A dependency-free partial Stage-0 core has since been added under `sheath/`; it implements contracts, explicit state transitions, generator-neutral coordination, snapshot-bound verification, disposable workspaces, canonical patch extraction and application, executable authorization, content-addressed artifacts, a fail-closed runner, a digest-pinned Docker adapter, decisions, schema-v1.7 run records, and 20 synthetic control-plane fixtures. A concrete `CyxCodeGenerator` and subprocess executor now map reconstructable canonical inputs through the pinned CyxCode image and trusted patch boundary, restore protected runtime metadata, and export content-derived success/failure provenance. The deterministic pinned-image proposal-to-verdict smoke produced a schema-valid accepted record while preserving the source and redacting the fixture credential. Live isolation and replay evidence is recorded in [Smoke_Test_Evidence.md](Smoke_Test_Evidence.md), [Snapshot_Smoke_Test_Evidence.md](Snapshot_Smoke_Test_Evidence.md), and [CyxCode_Adapter_Fixture_Evidence.md](CyxCode_Adapter_Fixture_Evidence.md). These fixtures remain regression coverage rather than benchmark evidence, and the thesis cannot yet claim measured improvement.

## Stable Findings

The documents consistently support five design requirements:

1. Software-agent quality must be judged by executable evidence, not fluent code.
2. Generation and governance should be separable experimental components.
3. The supervisor must preserve task scope and explicit constraints across iterations.
4. Deterministic tools should settle testable questions; language-model judgment should handle residual ambiguity.
5. Every run must preserve prompts, actions, patches, evidence, verdicts, costs, and versions.
6. Every model-visible input must be reconstructable from versioned artifacts rather than hidden runtime state.

These requirements align with prior work on repository-level evaluation, tool-using agents, iterative critique, and the documented limitations of feedback-free self-correction [1–9].

## Claims Requiring Correction

| Exploratory claim | Thesis treatment |
|---|---|
| Current agents fail because they “lack wisdom.” | Motivating interpretation; translated into measurable supervisory behaviors. |
| The ten debate patterns are the algorithmic backbone. | Provisional taxonomy to validate against real code reviews; not assumed complete. |
| A 3B MoE will be sufficient and run in under 20 ms. | Unverified design hypothesis; model size and latency must be measured. |
| Internalized weights are superior to instruction files. | Direct ablation question, not a conclusion. |
| The Sheath deterministically enforces all constraints. | Only explicit policy/tool gates may be deterministic; learned judgments remain probabilistic. |
| Passing the Sheath guarantees reliable or secure code. | Rejected. A pass means specified checks produced no blocking evidence. |
| The architecture demonstrates a path to AGI. | Long-term implication for discussion only; excluded from the primary hypothesis. |
| DeepSeek Harness proves lightweight trajectory control improves coding agents. | Rejected. The cited project is a composable agent harness; no such result is established by its repository or Cordis paper. |
| Cordis makes Sheath mathematically verified or guarantees perfect semantic rollback. | Rejected. Its composition mechanisms do not prove supervisory correctness, model compatibility, or recovery of arbitrary external side effects. |

## Lean Design Decision

The minimum publishable contribution is not a new foundation model. It is a controlled test of **decoupled, evidence-grounded supervision**. The initial implementation therefore contains four essential primitives:

- an immutable task/constraint contract;
- an auditable state and claim ledger;
- sandboxed build, test, and analysis tools;
- an independent decision policy with `accept`, `revise`, `block`, and `escalate` outcomes.

A learned critic is added only where deterministic checks and structured rules cannot classify a violation. MoE routing, expert growth, multimodality, and AGI framing are deferred extensions.

## Traceability Matrix

| Thesis element | Local origin | Validation artifact |
|---|---|---|
| Knowledge versus judgment distinction | `doc3.md`; global text around the theoretical foundation | Operational definitions and awareness metrics |
| Generator–supervisor separation | `doc3.md`; global “Sheath Architecture” | Architecture ablation |
| Evidence-first dialectical loop | `Research_Thesis.md`; global algorithm | Run ledger and tool evidence |
| Pattern taxonomy | `debate_doc2.md`; global training schema | Independent review-thread coding study |
| Capability benchmarks | `Evaluation_Benchmarks.md` | Held-out task suite |
| Dataset records and graph pipeline | `CyxWiz_Implementation_Plan.md` | JSON schemas, manifests, saved graphs |
| False-positive and overhead risks | global self-critique around “False Positive Problem” and “Overhead Problem” | Calibration, intervention burden, latency, and cost metrics |
| Human-requirement preflight | `Hello Query.md`, triple-helix critique | Contract confirmation, conflict fixtures, and escalation records |
| State/lifecycle/concurrency failures | `Hello Query.md`, logistics examples and peer review | Failure ontology, fixtures, and tool-backed checks |
| Transport-neutral tool boundary | global MCP/tooling discussion and peer review | Adapter contract and mandatory-check invariants |
| Source licensing boundary | global file-to-weights proposals and objections | License manifest, exclusions, and redistribution policy |
| Composable agent-host seam | `tolook.md`, corrected against DeepSeek Harness and Cordis primary sources | Conditional host audit; no current runtime dependency |

## Complete-Audit Reconciliation

The sequential review is recorded in [Context_Audit.md](Context_Audit.md). Every line range of both large transcripts was inspected, including a separately reread segment that had been truncated in terminal output. Reconciliation changed the thesis package in four material ways: it made human requirements subject to pre-flight scrutiny, expanded the software-specific failure taxonomy, made tool transport an optional adapter rather than an architectural dependency, and prohibited mining readable books or instruction files without suitable permission. Repeated prose, speculative topologies, arbitrary metrics, and unexecuted code were retained as provenance rather than promoted as findings.

## Decisions Still Required

- Institution-specific thesis format, citation style, author, degree, supervisor, and submission date.
- CyxWiz's implemented node/API capabilities; repository notes describe intended capabilities but contain no executable engine checkout here.
- Completion of the pinned CyxCode binary executor, exact model-visible input capture, and one end-to-end proposal-to-verdict smoke.
- Whether a future native DeepSeek Harness plugin offers measurable value over the completed external CyxCode adapter; do not evaluate this before the baseline exposes a specific interception limitation.
- Generator and critic model choices, licenses, hardware budget, and context limits.
- Dataset licenses, repository consent policy, and secure handling of vulnerability examples.
- Minimum practically important effect size and available experimental budget.
