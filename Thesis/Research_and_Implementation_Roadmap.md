# Research and Implementation Roadmap

## Purpose and Status Rules

This is the master progress tracker for the Sheath thesis and paper. Detailed design remains in the linked supporting documents; this file records sequence, status, dependencies, evidence, and exit gates. Update a phase to **Complete** only when its gate is supported by versioned artifacts. **Conditional** work begins only when its stated evidence justifies the added complexity.

Status as of **2026-08-23**:

- **Complete:** gate passed with repository evidence.
- **Active:** source material exists and the gate is being implemented or audited.
- **Waiting:** the next action depends on identified external facts or material.
- **Pending:** specified but not started or not yet evidenced.
- **Conditional:** intentionally omitted unless an earlier experiment activates it.

## Current Position

The deterministic Stage-0 control plane is implemented and tested. It can normalize task contracts, validate generator proposals, authorize constrained tools, isolate disposable workspaces, extract and replay patches, revise across bounded attempts, make evidence-gated decisions, and export schema-v1.7 provenance. Infrastructure gates are in place, including schema-valid failure-run records for generator and coordination faults.

```text
Completed foundation
        |
Pinned CyxCode adapter
        |
Pilot corpus and D0 experiment
        |
Residual-error gate
   +----+----------------+
   |                     |
Stop at lean D0     Design/train D1 critic
   |                     |
   +----------+----------+
              |
      Freeze protocol
              |
 Confirmatory experiment -> analysis -> thesis and paper
```

## Next-Session Pickup Snapshot

| Item | Resume value |
|---|---|
| Active phase | **Phase 6: Pilot candidate review and replay** |
| Last completed milestone | Astropy was retained for internal research analysis using pinned supplemental official SWE-bench evidence; its exact card remains `NOASSERTION`. Free MiMo remains blocked from benchmark input, and design decision `phase6-generator-boundary-001` selects CyxCode's existing local OpenAI-compatible seam as the primary proposal path. All cases remain quarantined. |
| Operator guide | [`../usage/README.md`](../usage/README.md) documents setup, runnable Stage-0 behavior, tests, smokes, the CyxCode boundary, pilot validation, evidence interpretation, and current safety gates. |
| Next implementation slice | Audit host CPU, RAM, GPU, storage, and Docker-to-host connectivity; then record an explicit local runtime/model decision with identity, weights digest, license, context/tool capability, resource ceiling, and contamination treatment. |
| Then | Run one generated public non-benchmark local feasibility canary. Only after it passes may a separate gate consider benchmark input. |
| Protected source | Keep any separate upstream CyxCode checkout read-only |
| Development copy | `integrations/cyxcode` (independent and ignored), branch `sheath-integration` |
| Pinned CyxCode identity | Commit `42676876b63ed5a18957e3318272eb0d875a95fc`, package 2.3.8, Bun 1.3.11 |
| Pinned pilot artifact | Image `sha256:f0a466626dcb1f123645ea9a40e2e7ef55c046dd7b76b8726d603605751b560c`; executable `sha256:8c9d82ad1dc42961666470248e9a2241a45eeb1f0327fa6ec6aefe61c6c1a31e` |

Completed work to preserve:

- all large context sources were audited and converted into the manuscript, traceability record, implementation blueprint, dataset/model plan, experiment protocol, paper plan, and this roadmap;
- a lean operator package under [`../usage/`](../usage/README.md) now separates repeatable local commands, deterministic integration smokes, completed one-shot evidence, and blocked research operations; its minimal Stage-0 example runs on Python 3.12 and 3.14;
- Phases 0-4 are complete at the infrastructure level, including schema v1.7 records, bounded retry, disposable snapshots, Docker isolation, canonical patch replay, and fail-closed evidence decisions;
- 138/138 Sheath tests pass on Python 3.12 and 3.14, including the concrete subprocess bridge regression;
- live isolation and writable-copy replay fixtures passed without mutating their sources;
- the independent CyxCode copy is pinned and audited: two package typechecks and 115 focused tests pass, while the non-clean full Windows suite remains a documented limitation;
- the floating `ghostty-web` dependency is pinned, frozen install passes, two Linux builds produced the same executable digest, and no-model container smokes pass; and
- `tolook.md` was fully reviewed and corrected against the DeepSeek Harness and Cordis primary sources; only reconstructable model context and a conditional future host seam were retained.
- a 20-case SWE-bench calibration inventory is revision-pinned and validator-backed; upstream license-file evidence is captured separately from dataset licensing, while every case remains explicitly quarantined pending replay and review;
- a pinned SWE-bench 5.0.2 vertical slice demonstrates correct baseline/gold oracle transitions for C, C++, and Python; a documented LF adapter fixes Windows-to-Linux script translation; and
- privacy-minimized review evidence closes privacy, secret, safety, lineage, and upstream file-scope gates for the replayed cases;
- network-disabled probes resolve all three pinned base commits to Git tree identities and SHA-256-addressed canonical source archives;
- the historical benchmark runner remains pinned to the now-blocked Big Pickle route, excludes all benchmark oracles, keeps raw artifacts restricted, and stops before task access; and
- live inspection and an independent smoke showed that Redis/fmt were not waiting on slow inference: the anonymous cloud endpoint returned HTTP 429 `FreeUsageLimitError`, which CyxCode silently retried. The corrected image fails fast, excludes resume/memory/graph/wiki state from experiment prompts, and passes populated-state cleanup;
- a 2026-08-21 short fmt canary captured a bounded public failure record and restricted response artifact for the corrected path: the run terminated on its single 429 event, changed no files, removed isolated state, and left no container.
- the exact pinned dataset cards resolve `research_analysis` to `allowed` for Redis/fmt. Pinned supplemental official SWE-bench project evidence retains Astropy for internal analysis while preserving the exact Verified card's `NOASSERTION`; event 29 records the change. Redistribution, training, and contamination remain unresolved, and all 20 cases remain quarantined;
- the official provider disclosure identifies Big Pickle as a stealth, unversioned model and states that free-period data may be used to improve it. Further benchmark submission is blocked in both policy evidence and the runner; the already submitted Redis/fmt prompts returned no model output, and Astropy was not submitted.
- the capped replacement review remains the benchmark-grade provider audit: neither reviewed route is approved for benchmark input and no call was made; and
- a superseding synthetic-only gate corrects the earlier conflation of infrastructure and benchmark requirements. One zero-cost MiMo-V2.5 Free attempt used only a generated public fixture through CyxCode's public-token path and captured a one-file proposal. The separate runner has no candidate, ledger, dataset, or source-evidence inputs; benchmark admission is unchanged; and
- design decision `phase6-generator-boundary-001` blocks free MiMo benchmark use and selects the already-supported local OpenAI-compatible CyxCode seam. Ollama is not installed, no local model is selected, and installation remains outside the completed decision.

The exact next slice is:

1. Completed: freeze [Pilot_Data_Specification.md](Pilot_Data_Specification.md) version 1.0.0 with explicit coverage, admission, rights, privacy, safety, lineage, contamination, annotation, agreement, split, and replay gates.
2. Completed: add strict Draft 2020-12 dataset-manifest and annotation-record schemas plus example records; both examples validate and five invalid-state mutations fail.
3. Completed: create and validate the append-only candidate inventory with 20 quarantined registrations, immutable dataset/base revisions, and pinned upstream license-file evidence.
4. Completed: pin the harness, datasets, environment, and image identities; baseline/gold replay `redis__redis-10068`, `fmtlib__fmt-1683`, and `astropy__astropy-12907` with content-addressed evidence.
5. Completed: hash the three cases' task/patch/test/script artifacts, compare task lineage across all 20 candidates, manually review privacy/secrets/safety and changed-file scope, and append events 24–26.
6. Completed: resolve each replayed base commit inside its pinned image and hash the exact canonical source archive without retaining another source copy.
7. Completed: diagnose Big Pickle quota/retry behavior, isolate learned prompt state, and record the short canary. The provider is now blocked from benchmark submission because its underlying model/revision and prior exposure are undisclosed and free-period data may be used for model improvement.
8. Completed: evaluate exactly two replacements under benchmark-grade requirements. Neither is approved for benchmark input; GLM 5.2 remains an optional paid synthetic route, not a prerequisite.
9. Completed: separate the infrastructure-canary gate from benchmark admission. Authorize one free MiMo-V2.5 attempt only for a generated public non-benchmark fixture, and add a bounded runner plus mutation tests.
10. Completed: run that one free synthetic canary. CyxCode captured response and patch artifacts for a change limited to `arithmetic.py`; source preservation and post-run container absence passed. This does not authorize benchmark input.
11. Completed: preserve the exact-card decisions, pin supplemental official project evidence, retain Astropy for internal analysis, block free-cloud training-use routes, and select the existing local OpenAI-compatible seam without installing a runtime.
12. Active: audit host capacity and Docker-to-host connectivity, then make an explicit runtime/model decision. Only a generated public non-benchmark fixture may enter the first local feasibility canary.
13. Resolve the pinned local generator's contamination treatment and admit genuine proposals only after the synthetic local gate passes.
14. Replay and review the remaining 17 only after step 13 yields an operational admission path.
15. Double-label and adjudicate eligible calibration cases, then audit agreement and operational cost before scaling toward the 100–300-case Phase-6 gate.

Phase 5 remains closed. Phase 6 remains active until the full seed set exists and satisfies the frozen quality gates.

Do **not** start another cloud-provider comparison, repeat the completed cloud canary, install a local runtime before its design decision, begin CyxWiz graph work, train a critic, or add MoE/continual learning in the next slice. Continue only through the frozen capacity, local-generator, contamination, replay, and admission gates.

Baseline restart commands:

```powershell
Set-Location sheath
python -m unittest discover -s tests -v

Set-Location integrations\cyxcode
bun install --frozen-lockfile --ignore-scripts --no-progress
Set-Location 'packages\opencode'
bun typecheck
Set-Location '..\app'
bun typecheck
```

Build identities and the Windows cross-target limitation are recorded in [CyxCode_Build_Evidence.md](CyxCode_Build_Evidence.md); executable semantics and adapter acceptance tests are frozen in [CyxCode_Adapter_Contract.md](CyxCode_Adapter_Contract.md).

## Phase Roadmap

| ID | Phase | Status | Deliverable and exit gate |
|---:|---|---|---|
| 0 | Context consolidation | **Complete** | Both large transcripts and supporting files were audited range by range; claims and contradictions are recorded in [Context_Audit.md](Context_Audit.md) and [Findings_and_Traceability.md](Findings_and_Traceability.md). |
| 1 | Research specification | **Complete as proposal** | Research questions, hypotheses, conditions, outcomes, validity limits, staged learning policy, and publication rules are documented. Numerical preregistration placeholders remain open until the pilot. |
| 2 | Stage-0 decision core | **Complete** | Immutable contracts, evidence ledger, state machine, mandatory-check decisions, tool authorization, artifacts, and canonical records are implemented under `sheath/src/sheath/`. Invalid or stale evidence cannot produce acceptance. |
| 3 | Isolation and patch boundary | **Complete** | Verified snapshots, digest-pinned Docker execution, bounded output, canonical binary-safe patch extraction, fail-closed replay, source preservation, and cleanup pass automated and live fixtures. |
| 4 | Generator-neutral retry pipeline | **Complete** | Typed generator proposals, single and bounded coordinators, revision feedback, fresh retry snapshots, tool-backed verification, and schema-v1.7 `attempt_contexts` are implemented. A generated two-attempt accepted record validates against the schema. |
| 5 | Concrete CyxCode adapter | **Complete** | The concrete Python executor drives the immutable CyxCode image through the canonical bridge, deterministic provider, explicit export, trusted patch boundary, and accepted schema-v1.7 record. Prompt preservation, secret redaction, source preservation, and Docker/Windows cleanup passed. See [CyxCode_Adapter_Fixture_Evidence.md](CyxCode_Adapter_Fixture_Evidence.md). |
| 6 | Pilot data specification | **Active — local generator gate pending** | Version 1.0.0 and strict schemas are frozen. The 29-event ledger contains 20 quarantined candidates; three pinned C/C++/Python cases pass replay, five non-replay gates, source-snapshot capture, and internal research-analysis review. The free synthetic CyxCode canary passed its infrastructure purpose but its route remains blocked for benchmark input. The existing local OpenAI-compatible seam is selected pending capacity, runtime/model, synthetic feasibility, and contamination gates. |
| 7 | CyxWiz capability audit | **Pending** | Verify the available CyxWiz version against ingestion, graph execution, training, evaluation, and artifact-export requirements. Gate: a capability matrix and one reproducible minimal graph; missing capabilities remain narrow external adapters. |
| 8 | Stage-0 experimental pilot | **Pending** | Run approximately 50 paired tasks across A, B, C, and D0 using frozen snapshots, budgets, randomization, hidden checks, and blinded review. Gate: stable harness, measured exclusions and infrastructure failures, annotation agreement, and variance estimates sufficient for power analysis. |
| 9 | Sheath D1 model specification | **Conditional** | Analyze D0 errors that deterministic Sheath checks cannot settle. Freeze the residual critic's inputs, structured outputs, labels, confidence/abstention behavior, context limits, and resource budget. Gate: a documented residual task with enough reliable examples and a simple baseline that leaves measurable room for improvement. |
| 10 | Sheath D1 dataset and training | **Conditional** | Build grouped temporal train/validation/test manifests, leakage audits, loaders, baseline classifiers, and then the smallest justified adapted model. Gate: reproducible checkpoint, model card, calibration, held-out residual improvement, acceptable false interventions, and a favorable quality–cost trade-off. No MoE or continual learning without separate evidence. |
| 11 | Protocol freeze | **Pending** | Resolve every bracketed field in [Experiment_Protocol.md](Experiment_Protocol.md): generators, images, budgets, seeds, primary contrast, effect threshold, multiplicity method, non-inferiority margin, sample size, rerun policy, and D1 admission gate. Publish the randomization schedule and analysis revision before test outcomes are examined. |
| 12 | Confirmatory experiment | **Pending** | Run all admitted conditions on held-out repository families without changing models, thresholds, or analysis. Gate: complete schema-valid records, checksummed artifacts, exclusions, deviations, blinded adjudication, and reproducible result tables. |
| 13 | Analysis and thesis completion | **Pending** | Compute paired effects, confidence intervals, calibration, cost/latency, failure analysis, and preregistered ablations. Replace manuscript placeholders only with artifact-backed findings; complete results, discussion, threats to validity, limitations, and conclusion. |
| 14 | Paper and reproducibility release | **Pending** | Derive the shorter paper from actual results, retain null/negative outcomes, audit every quantitative claim, and publish permitted code, schemas, manifests, configurations, checksums, and reviewer guidance. The empirical-paper gate is defined in [Paper_Plan.md](Paper_Plan.md). |

## When the Sheath Model Starts

The implemented system is currently **Sheath Stage 0**, a deterministic supervisory control plane, not a newly trained model. CyxCode supplies the coding generator while Sheath controls contracts, isolation, evidence, retries, and decisions.

The learned **Sheath D1 residual critic** begins only after Phase 8 measures errors that rules and tools cannot settle. Phase 9 designs that model and freezes its bounded task; Phase 10 prepares the leakage-controlled dataset, compares simple baselines, and trains the smallest model justified by held-out improvement. If Stage 0 already meets the target or no stable residual task exists, D1 is not trained. This is a planned decision gate, not an omission.

## Completed Evidence Baseline

- **Automated tests:** 138/138 pass on Python 3.12 and 138/138 on Python 3.14; 9/9 CyxCode adapter tests and 19/19 retry tests pass; the CyxCode package typecheck passes.
- **Schema:** a two-attempt tool-backed accepted run, the CyxCode fixture success/failure records, and the pinned-image accepted record validate against Draft 2020-12 schema v1.7, including date-time formats.
- **Live isolation:** the read-only Docker fixture blocks repository writes and outbound TCP under the exercised configuration; see [Smoke_Test_Evidence.md](Smoke_Test_Evidence.md).
- **Live mutation and replay:** two independent writable-snapshot runs produced identical source, result, patch, output, and sandbox digests and removed every copy; see [Snapshot_Smoke_Test_Evidence.md](Snapshot_Smoke_Test_Evidence.md).
- **CyxCode audit:** both Bun package typechecks and 115 focused CLI/session tests pass; isolated no-model CLI checks pass. A pinned Linux builder produced the same executable SHA-256 twice and passed container version/help smokes. The non-clean full Windows suite remains a recorded limitation; see [CyxCode_Build_Evidence.md](CyxCode_Build_Evidence.md).
- **Scope limit:** the 20 synthetic scenarios are control-plane regression fixtures, not benchmark or model-performance evidence.
- **Pilot-data schemas:** strict Draft 2020-12 validation accepts both versioned examples and rejects five inconsistent rights/admission/annotation mutations. No actual seed case is claimed by the example files.
- **Candidate intake:** the dependency-free ledger validator accepts 29 append-only events for 20 revision-pinned registrations with a 7 C / 6 C++ / 7 Python balance and rejects sequence, supersession, reason, and premature-admission mutations. All 20 dispositions are quarantined.
- **Vertical replay:** three marker baselines preserve 1/1/2 failing F2P tests while 7/42/13 P2P controls pass; all three gold patches then pass the F2P and P2P sets. Exact dataset, harness, environment, image, report, and output identities are recorded.
- **Three-case non-replay review:** no retained raw text, secret signals, personal identifiers, offensive-security content, exact duplicates, or task five-gram similarities at or above 0.85 were found. Core-file license scope passes. Exact-card review allows research analysis for the two Multilingual cases; supplemental official project evidence permits internal analysis of Astropy while its exact card remains `NOASSERTION`. Redistribution, training, generator exposure, and artifact completeness remain unresolved. All three stay quarantined.
- **Source snapshots:** Redis, fmt, and Astropy base commits resolve as commit objects inside their pinned, network-disabled replay images. Canonical Git archive SHA-256 identities are recorded without retaining another raw source copy. Astropy's diagnostic container HEAD differs from the requested base, so the explicit base commit—not ambient HEAD—is authoritative. Eighteen pilot-data tests pass.
- **Rights/provider exposure:** [phase6_rights_and_provider_exposure.json](pilot_data/review_evidence/phase6_rights_and_provider_exposure.json) binds the exact dataset-card hashes, per-use decisions, outbound-submission history, and Big Pickle block. Its dependency-free validator and five mutation tests pass; the full pilot suite is 24/24.
- **Replacement-provider gate:** [phase6_provider_replacement_gate.json](pilot_data/review_evidence/phase6_provider_replacement_gate.json) pins the historical benchmark-grade review and two fail-closed decisions. Its six mutation tests still pass; no benchmark candidate is approved.
- **Synthetic-canary correction:** [phase6_synthetic_canary_gate.json](pilot_data/review_evidence/phase6_synthetic_canary_gate.json) supersedes only the synthetic portion of the earlier decision. One free public-token attempt with generated local input captured a proposal changing only `arithmetic.py`; source preservation passed, no matching container remained, and the benchmark block is unchanged. The full pilot suite is 40/40.
- **Outbound/Astropy decision:** [phase6_outbound_and_astropy_decision.json](pilot_data/review_evidence/phase6_outbound_and_astropy_decision.json) pins the supplemental SWE-bench and current OpenCode evidence, retains Astropy, blocks free MiMo benchmark use, and selects the existing local seam without claiming runtime readiness. Its six mutation tests pass; the full pilot suite is 46/46.

## Immediate Work Queue

1. Audit host CPU, RAM, GPU, storage, and Docker-to-host connectivity without installing a runtime.
2. Record an explicit local runtime/model decision with model and weights identity, license, context/tool capability, resource ceiling, and contamination treatment.
3. After that decision, run exactly one generated public non-benchmark local feasibility canary. Do not use candidate, replay, source-snapshot, or thesis content.
4. If the local gate passes, generate and independently verify one replayed candidate proposal; keep blinded checks and gold artifacts outside model context.
5. Apply the same pinned replay/review path to the remaining 17 registrations only after the one-case path is operational.
6. Double-label and adjudicate eligible calibration cases; compute the prespecified category, severity, and action agreement measures.
7. Add C++ repository families and valid hard negatives before scaling; complete the 100–300-case Phase-6 seed gate, then perform Phase 7 and Phase 8 before any D1 model work.

CyxCode acquisition and dataset-protocol work may proceed in parallel, but dataset collection must not start before provenance, licensing, and split rules are frozen.

## Lean Decision Gates

- Do not train a critic merely because training was proposed; first demonstrate a stable residual error set beyond rules and tools.
- Prefer rules, tools, compact classifiers, and constrained outputs before adapting a decoder model.
- Do not implement sparse experts, specialization, or continual learning until ablations show that a smaller model is insufficient.
- Do not add an experimental condition unless it answers a research question.
- Do not treat passing infrastructure fixtures as evidence that Sheath improves coding-agent outcomes.
- Do not write empirical conclusions before immutable confirmatory records and analysis exist.
- Do not switch agent hosts or add Cordis lifecycle machinery unless the completed CyxCode baseline exposes a specific limitation that those mechanisms solve.

## Supporting Documents

- [`../usage/README.md`](../usage/README.md): practical environment setup, Stage-0 and CyxCode operation, pilot validation, troubleshooting, and current execution boundaries.
- [Thesis_Manuscript.md](Thesis_Manuscript.md): canonical academic argument and research design.
- [Implementation_Blueprint.md](Implementation_Blueprint.md): interfaces, state machine, policies, and engineering definition of done.
- [Dataset_and_Model_Plan.md](Dataset_and_Model_Plan.md): corpus, annotation, model ladder, training objectives, and stop conditions.
- [Pilot_Data_Specification.md](Pilot_Data_Specification.md): frozen Phase-6 case, admission, rights, lineage, annotation, split, and replay contract.
- [Experiment_Protocol.md](Experiment_Protocol.md): conditions, fairness rules, outcomes, statistics, and preregistration checklist.
- [Paper_Plan.md](Paper_Plan.md): publication structure and empirical submission gate.
- [Tolook_Source_Review.md](Tolook_Source_Review.md): source correction and adopt/defer/reject decisions for the DeepSeek Harness, Cordis, and DeepSeek-R1 material in `tolook.md`.
