# Dataset and Model Plan

## 1. Research Data Goal

Construct data that teaches and evaluates **engineering supervision**, not generic code generation. Each example must connect a task and constraints to a proposal, observable evidence, a decision, and an engineering outcome. Large volumes of unlabeled code do not satisfy this requirement.

### 1.1 Phase-6 Frozen Boundary

The operational seed-corpus contract is [Pilot_Data_Specification.md](Pilot_Data_Specification.md), version `1.0.0`. It defines the case unit, 100–300-case coverage envelope, admission state machine, per-use license decisions, privacy and safety rules, lineage and duplicate grouping, contamination fields, double annotation, adjudication, agreement gates, split algorithm, and replay gate. The machine boundaries are [dataset_manifest.schema.json](schemas/dataset_manifest.schema.json) and [annotation_record.schema.json](schemas/annotation_record.schema.json). This broader document remains the conditional growth and model plan; where language differs, the frozen pilot specification controls Phase 6.

## 2. Data Layers

### Layer A: Task Contracts

Records contain the original request, repository snapshot, goals, constraints, success criteria, excluded work, risk indicators, permitted tools, and expected verification. These records test whether the system understands what must remain invariant.

### Layer B: Findings

A finding identifies one precise gap:

- violated constraint;
- unsupported completion claim;
- missing or stale evidence;
- scope drift;
- unsafe tool action;
- security or memory hazard;
- invalid state-machine transition;
- resource leak or incomplete cleanup;
- concurrency, locking, or atomicity defect;
- API/architecture incompatibility;
- inadequate or misleading test;
- unresolved uncertainty.

Every positive finding includes location, severity, rationale, required evidence, and preferred action. Negative examples—valid proposals that should not be blocked—are equally important for calibration.

### Layer C: Execution Traces

Traces preserve proposals, commands, outputs, patches, revisions, and final outcome. Only observable actions are stored as evidence. Private chain-of-thought is neither required nor treated as ground truth; concise decision rationales and state changes are sufficient.

### Layer D: End-to-End Outcomes

Outcomes include build and test status, hidden tests, analyzer deltas, scope violations, human review, attempts, cost, and latency. They enable training and evaluating the relationship between intervention and actual engineering success.

## 3. Candidate Sources

Prioritize sources with provenance and executable verification:

1. issue–patch pairs from tested C, C++, and Python repositories;
2. pull-request review comments linked to later code changes;
3. CI failure followed by a verified correction;
4. compiler/static-analyzer findings with patches;
5. security advisories and defensive fixes with safe regression tests;
6. benchmark tasks with hidden tests;
7. manually authored constraint-conflict and valid-nonviolation pairs.

Instruction files (`CONTRIBUTING.md`, repository guides, style/security policies) are useful context, but “file-to-weights” is not the only or default treatment. Current, project-specific rules must remain explicit and versioned even if stable patterns are learned. Books, articles, and repository instructions are collected only when their licenses or explicit permissions cover the intended extraction, training, and redistribution; public readability alone is insufficient.

### 3.1 Initial Calibration Inventory

The first intake slice is recorded in [pilot_data/candidate_events.jsonl](pilot_data/candidate_events.jsonl): 20 purposively balanced candidates from revision-pinned SWE-bench Multilingual and SWE-bench Verified releases. It spans 7 C, 6 C++, and 7 Python tasks across 10 repository families. One C, one C++, and one Python candidate have content-addressed baseline/gold replays, canonical source-archive identities, and passed privacy, secret, safety, 20-case lineage, and upstream file-scope review. Exact-card review permits research analysis of the Redis and fmt Multilingual cases under the internal project policy. The Astropy exact card remains `NOASSERTION`, but pinned supplemental evidence from the official SWE-bench project identifies Verified within its MIT-licensed code and data and documents model inference; Astropy is therefore retained for internal research analysis without granting redistribution or model-training rights. Big Pickle and MiMo-V2.5 Free remain blocked from benchmark input because their free-period inputs may be used for model improvement and benchmark exposure is unresolved. A separate MiMo-V2.5 Free infrastructure canary used only generated public non-sensitive input, required no paid credential, and captured a one-file proposal; it contributes no corpus case or model-performance result. The existing CyxCode local OpenAI-compatible seam is the selected primary benchmark-generation path. The capacity/connectivity audit passed, while the runtime/model pin and synthetic-only feasibility canary remain pending. All cases remain quarantined because genuine proposal artifacts and contamination clearance are absent. This batch calibrates the intake/replay process; it is not a random sample, seed admission, benchmark result, or training dataset. Because the multilingual source contains only two C++ families, later sourcing must add at least three independent C++ families before the frozen coverage gate can pass.

## 4. Inclusion and Exclusion

For the Phase-6 seed, include a case only when:

- source, exact revision, snapshot digest, publication date, license evidence, and collection date are known;
- the task can be reconstructed without secrets;
- a clean, digest-pinned replay produces outcome evidence suitable for two independent reviewers;
- generated/vendor/binary content is identified;
- required context fits the declared representation strategy;
- research analysis is explicitly allowed after license review; and
- the case is defensive, contains no necessary personal data, and requires no unapproved external service.

Reject hard failures; quarantine resolvable uncertainty. Neither state contributes to quotas or splits. License status is recorded as an SPDX expression and list version, but analysis, metadata/label/source redistribution, and model training remain separate `allowed`/`prohibited`/`unknown` decisions. Exact reason codes and append-only supersession rules are frozen in the pilot specification.

## 5. Annotation Ontology

### 5.1 Core Categories

Use a small initial ontology:

| Category | Operational question |
|---|---|
| `epistemic_gap` | Does the proposal rely on missing or invented context? |
| `constraint_violation` | Does it conflict with an explicit task/project rule? |
| `scope_violation` | Does it change behavior outside the necessary task surface? |
| `evidence_gap` | Is a completion claim unsupported or supported by stale evidence? |
| `impact_gap` | Is a relevant downstream effect or regression check omitted? |
| `unsafe_action` | Does a tool action exceed authorization or safety policy? |
| `engineering_defect` | Is there a concrete correctness/security/maintainability defect? |
| `no_violation` | Is the proposal acceptable under the available contract/evidence? |

The debate-derived patterns are secondary tags until validated.

### 5.2 Severity

- `info`: useful observation, no revision required;
- `warning`: plausible risk requiring disclosure or optional check;
- `revision`: correctable gap that prevents acceptance;
- `blocking`: hard policy, authorization, or severe safety violation;
- `escalation`: cannot be resolved within available evidence/authority.

### 5.3 Annotation Form

Annotators answer in order:

1. What is directly observable?
2. Which task/constraint/evidence ID applies?
3. What is the smallest supported finding?
4. What evidence could refute the finding?
5. What action is proportionate?

This order reduces labels based only on stylistic preference.

## 6. Quality Control

- Train annotators on shared fixtures and publish the guide.
- Double-label validation and test data; sample training data.
- Track agreement by category and severity, not only aggregate accuracy.
- Adjudicate before freezing the split.
- Include matched hard negatives for each violation type.
- Run parsers, builds, tests, and analyzers on code examples where feasible.
- Detect exact and near duplicates before splitting.
- Audit model-generated examples independently of the generating model.
- Maintain a rejection log and dataset changelog.

Every seed case is double-labeled; a third reviewer adjudicates all disagreements and audits a frozen 10% sample of agreements. Retained binary categories and actions require raw agreement at least `0.80` and Cohen's kappa at least `0.60`. Ordinal severity requires exact agreement at least `0.75` and weighted kappa at least `0.60`. Prevalence and positive/negative agreement are reported beside kappa. After one guide revision and blind relabel of at least 20 affected cases, a category that still fails is merged, demoted, or removed rather than rescued by lowering the threshold.

## 7. Split Strategy

All Phase-6 cases use split `seed`; they are development-only and permanently excluded from confirmatory testing. If the residual-learning gate later opens, group forks, issue/patch lineages, retries, exact duplicates, and confirmed or unresolved near duplicates before assignment. Whole newest repository families form approximately 20% held-out test; the newest remaining lineage groups form approximately 20% validation/calibration; the remaining approximately 60% forms training. Challenge cases remain separate. Publication time and stable ID determine order, never labels or model performance.

Record public benchmark membership and generator exposure even when exposure is `unknown`. The reference solution and blinded checks never enter model context. Training the generator and training the supervisor remain separate contamination questions.

## 8. Dataset Growth Gates

| Stage | Approximate scale | Purpose | Gate |
|---|---:|---|---|
| Seed | 100–300 | Validate schema and ontology | Replay, provenance, coverage, and annotation gates in the frozen pilot specification |
| Pilot | 1,000–3,000 | Train first residual critic | Only if residual-task admission passes; beats simple classifiers/rules |
| Expansion | 10,000+ | Improve domain/language coverage | Learning curve still improving |
| Specialization | As justified | Separate difficult domains | Error interference demonstrated |

Counts are planning ranges, not success criteria. Stop collecting when marginal examples do not improve held-out performance or coverage.

## 9. Model Tasks

The learned component can be decomposed into bounded tasks:

1. risk classification;
2. constraint–proposal entailment/contradiction;
3. finding type and severity classification;
4. missing-artifact prediction;
5. evidence sufficiency classification;
6. structured remediation generation;
7. calibrated abstention/escalation.

Start with non-generative or constrained-output formulations where possible. Compare against logistic/encoder baselines before adapting a decoder LLM.

## 10. Training Objectives

For verdict class \(y\), finding category \(z\), required artifact \(a\), and confidence target \(c\), a candidate multi-task loss is:

\[
L = \lambda_v L_{verdict} + \lambda_f L_{finding} + \lambda_a L_{artifact} + \lambda_c L_{calibration}.
\]

The weights are tuned on validation data and reported. A routing loss is introduced only for an evaluated expert architecture. Rationale generation is not allowed to dominate verdict accuracy or calibration.

Class imbalance is addressed with sampling or cost weighting based on the real consequence of false acceptance and false intervention. Thresholds are selected on the calibration set, never the final test set.

## 11. Model Selection Ladder

1. deterministic rules and external tools;
2. bag-of-features or compact encoder classifiers;
3. small pretrained code/text model with frozen head or LoRA [10];
4. separate domain adapters;
5. sparse MoE only after measured domain interference [11].

For each rung report quality, calibration, memory, active/total parameters, tokens per second, cold/warm latency, energy if available, and license. Select the smallest model on the Pareto frontier that meets the preregistered quality gate.

## 12. Model Card Requirements

Every checkpoint release records:

- base model, license, revision, tokenizer, and context length;
- data manifest and excluded sources;
- task formulations and loss weights;
- hardware, software, seeds, and training duration;
- overall and slice metrics with confidence intervals;
- calibration and abstention behavior;
- known false-positive and false-negative modes;
- intended use and prohibited use;
- privacy, security, and contamination assessment;
- checksum and compatibility version.

## 13. Continual Learning Policy

Do not update the production critic automatically from unreviewed interactions. Collect candidate failures in a quarantine set, annotate them, run regression evaluation, and release a new version. Replay representative older categories to detect forgetting. Organization-specific policies should default to explicit configuration; weight adaptation is optional and separately versioned.

## 14. Stop Conditions

Do not train a custom critic if Stage 0 meets the target outcome. Do not build MoE if a dense/adapted model meets latency and quality gates. Do not expand data if improvements disappear on held-out repositories. A smaller validated system is the intended lean outcome.
