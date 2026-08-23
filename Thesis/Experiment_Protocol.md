# Experiment Protocol

## 1. Protocol Status

This document is a preregistration scaffold. Bracketed values must be decided before confirmatory runs. Pilot data may inform power and infrastructure decisions, but pilot tasks cannot enter the confirmatory test set.

## 2. Research Objective

Estimate the causal effect of an independent, stateful, evidence-grounded supervisor on repository-level software-engineering outcomes, relative to direct generation, repository instructions, and same-model reflection.

## 3. Frozen Experimental Units

- **Unit:** one task–repository snapshot–condition run.
- **Blocking unit:** task; all conditions use the same task snapshot.
- **Primary population:** held-out C, C++, and Python repository tasks meeting the inclusion policy.
- **Generators:** `[model IDs and immutable revisions]`.
- **Supervisor:** `[Stage 0 version; optional critic ID]`.
- **Environment image:** `[digest]`.
- **CyxWiz graph or external runner revision:** `[commit/checksum]`.

## 4. Conditions

| Code | Condition | Added mechanism |
|---|---|---|
| A | Direct | Standard generator and tools only |
| B | Instruction | Versioned engineering instruction file in generator context |
| C | Self-reflection | Same generator critiques and revises once or within matched budget |
| D0 | Stage-0 Sheath | Independent ledger, policy, risk, and tool/evidence checks; no learned critic |
| D1 | Learned Sheath | D0 plus residual learned critic |

The primary contrast is `[D0 or D1] - A`; choose before the confirmatory run. D0 versus D1 tests the learned critic. B and C distinguish instruction and self-feedback effects. D1 enters the confirmatory matrix only if it passes a frozen pilot gate for residual-task value, calibration, and false interventions; otherwise report its pilot result and use D0.

## 5. Fairness Constraints

- Same generator model, decoding parameters, initial task text, repository snapshot, and available safe tools.
- Context added by each mechanism is recorded; both fixed-token and unconstrained-system comparisons are reported.
- Conditions receive equal wall-clock and/or monetary budgets in the main analysis. A secondary quality–cost frontier may relax equality.
- Same retry cap, unless retry count is the mechanism under study; any difference is explicit.
- Sandboxes reset after every run.
- Hidden tests and reference patches remain unavailable to all agents.
- Condition labels are hidden from human outcome reviewers.

## 6. Task Sampling

Candidate admission, per-use rights, rejection/quarantine, lineage, duplication, and seed replay follow [Pilot_Data_Specification.md](Pilot_Data_Specification.md). Phase-6 seed cases are development-only and cannot enter the confirmatory test set.

### Inclusion

- reproducible build/test environment;
- clear task and reference outcome;
- at least one hidden or blinded verification mechanism;
- bounded completion time;
- license permits research use;
- no secrets or external side effects.

### Exclusion

- environment cannot be reproduced after documented repair attempts;
- task depends on unavailable external services;
- solution is duplicated across selected tasks;
- task was used for supervisor training/calibration;
- task requires prohibited offensive or destructive actions.

### Stratification

Stratify by language, task category, risk, estimated change surface, and repository. The confirmatory sample size is set by paired power analysis using pilot discordant proportions and a minimum practically important absolute success difference of `[delta]`.

## 7. Randomization and Repetition

Randomize condition order within task. Use a generated schedule stored before execution. If stochastic repeats are affordable, run `[k]` seeds per task-condition and define in advance whether the unit outcome is first-run success, majority success, or a hierarchical estimate. Never select the best seed after inspection.

## 8. Outcomes

### Primary Outcome: Verified Success

`verified_success = 1` only when:

1. mandatory visible and hidden verification passes on the final patch;
2. no blocking explicit constraint violation is found by blinded adjudication;
3. no new high/critical finding is produced by the predefined security checks.

Otherwise it is zero. Infrastructure failures are separate and trigger the predefined rerun policy.

### Key Secondary Outcomes

- hidden and visible test success separately;
- constraint violations by type/severity;
- unrelated changed files and patch line count;
- new analyzer findings by severity;
- attempts and successful recovery after failure;
- false interventions on proposals adjudicated valid;
- escalation, block, and human override rates;
- tokens, tool calls, wall time, peak memory, and estimated cost;
- evidence completeness;
- critic classification and calibration metrics.

## 9. Outcome Adjudication

Automated outcomes are recomputed from artifacts. Two reviewers independently inspect constraint adherence and severe findings without seeing condition identity. A third reviewer adjudicates every disagreement and audits the prespecified 10% sample of agreements. Seed category/action agreement requires raw agreement at least `0.80` and kappa at least `0.60`; severity requires exact agreement at least `0.75` and weighted kappa at least `0.60`. The guide, prevalence, positive/negative agreement, agreement statistics, and all post-freeze changes are published. Confirmatory thresholds are frozen separately before confirmatory outcomes are examined.

Reviewer judgments cannot convert a failing hidden test to success. Conversely, a passing test does not erase an explicit scope or safety violation.

## 10. Statistical Analysis

### Primary

- Report success rate per condition and paired absolute difference with 95% confidence interval.
- Use McNemar's exact test for the preregistered paired primary contrast.
- Use task-clustered bootstrap confidence intervals as a robustness analysis.

### Secondary

- Binary outcomes: paired differences and conditional/mixed logistic models if justified.
- Counts: paired bootstrap and an appropriate count model with repository/task grouping.
- Continuous cost/latency: median paired difference, quantiles, and bootstrap intervals.
- Calibration: Brier score, expected calibration error with declared bins, and reliability plots.
- Detection: precision, recall, F1, AUROC, and AUPRC; emphasize precision–recall under imbalance.

Report effect sizes and intervals. Mark unregistered subgroup or pattern analyses exploratory. Correct the family of key secondary comparisons using `[method]`.

## 11. Non-Inferiority Test for Adaptive Scrutiny

Compare risk-adaptive and full Sheath supervision. Declare the verified-success non-inferiority margin `[m]`, chosen from practical consequences rather than pilot convenience. Adaptive supervision is successful only if the lower confidence bound is above `-m` and it reduces at least one preregistered resource metric by `[threshold]` without increasing severe violations.

## 12. Ablations

Run only ablations tied to research questions:

- D0 versus D1: value of learned residual critic;
- D0 without state ledger: value of persistent constraints;
- D0 without tools: value of executable grounding;
- C versus the preregistered Sheath condition: independent supervision versus self-feedback;
- B versus the preregistered Sheath condition: instruction context versus enforced supervision;
- adaptive versus full supervision for the preregistered Sheath condition: value of risk routing.

The main experiment should not be delayed by every possible component combination.

## 13. Failure and Rerun Policy

- **Infrastructure failure:** sandbox/image/runner failure unrelated to agent action; repair and rerun all conditions for that task if the repair could affect outcomes.
- **Agent-induced environment damage:** score as task failure if the action was permitted and caused the damage.
- **Provider/transient failure:** follow a fixed retry count and backoff; log every attempt.
- **Timeout/budget exhaustion:** task failure or escalation according to the frozen scoring rule.
- **Invalid artifact:** exclude only under a condition-blind rule; report exclusions by condition after unblinding.

## 14. Contamination Analysis

- Group split by repository family and issue/patch lineage.
- Keep every Phase-6 seed case out of confirmatory testing and any confirmatory threshold calibration.
- Search exact and near-duplicate task, patch, and test content across local training/validation/test sets.
- Record public benchmark membership and publication dates.
- Run a canary or solution-recognition probe where feasible.
- Report a stricter subset of tasks created after model knowledge cutoffs or from private/permitted sources when available.

Contamination cannot always be eliminated for pretrained generators; it must be bounded and disclosed.

## 15. Reproducibility Checklist

- [ ] Task and run schemas frozen.
- [ ] Task inclusion/exclusion log exported.
- [ ] Dataset and split manifests checksummed.
- [ ] Models, tokenizers, prompts, policies, and instruction files versioned.
- [ ] Environment image and dependency locks archived.
- [ ] Randomization schedule generated before runs.
- [ ] Budgets and stopping rules frozen.
- [ ] Hidden tests isolated.
- [ ] Reviewers trained and blinded.
- [ ] Primary contrast, effect, and analysis code frozen.
- [ ] All tool outputs and final patches retained.
- [ ] Deviations logged before results are examined where possible.

## 16. Required Result Tables

1. Task composition and exclusions.
2. Condition configuration and resource budgets.
3. Primary verified-success outcomes and paired contrasts.
4. Constraint/security outcomes.
5. Cost, latency, attempts, and tool use.
6. Supervisor detection and calibration.
7. Ablations.
8. Category/language slices with uncertainty.
9. Infrastructure failures and protocol deviations.

## 17. Interpretation Rules

- Do not call a non-significant result “equivalent” without an equivalence/non-inferiority design.
- Do not infer model superiority from a system comparison; attribute the tested bundle and use ablations.
- Do not claim security from absence of selected findings.
- Do not generalize beyond tested languages, repositories, models, and budgets.
- Do not claim AGI from repository-task improvement.
