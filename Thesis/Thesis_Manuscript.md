# The Sheath: Evidence-Grounded Supervision for Reliable Software-Engineering LLM Agents

**A thesis draft from research idea to implementation**

- Author: `[Name]`
- Degree and department: `[Degree, Department, Institution]`
- Supervisor: `[Name]`
- Submission date: `[Date]`

> **Research status.** This manuscript specifies a proposed system and experiment. A dependency-free Stage-0 core now implements immutable contracts, explicit run states, a typed model-neutral generator proposal boundary, single- and bounded-attempt coordinators, snapshot-bound tool verification, verified disposable workspace staging and restaging, bounded canonical patch extraction and fail-closed application, host/container executable authorization, content-addressed artifacts, output-limit and timeout semantics, a fail-closed runner, a digest-pinned Docker adapter, mandatory-check decisions, schema-v1.7 run records, patch-record schema v1.0, and synthetic control-plane fixtures; it is not the complete runtime or a benchmark result. A concrete CyxCode adapter now maps canonical execution envelopes and trusted workspace deltas into content-derived proposals and preserves success/failure artifacts. Repeated fixtures have observed source isolation, deterministic patch reconstruction, protected runtime-metadata restoration, and stable proposal identities. The pinned-binary Python executor join, CyxWiz graphs, datasets, trained critics, and benchmark outcomes remain future work. Result placeholders must not be rewritten as findings until supported by versioned artifacts.

## Abstract

Large language models can generate plausible code, but practical software engineering requires more than plausible generation. An agent must preserve requirements across a repository, recognize missing context, obey architectural and security constraints, use tools, interpret failures, and support its completion claims with evidence. This thesis calls that collection of behaviors *engineering supervision*. The motivating distinction is between knowledge—available code patterns and technical information—and “wisdom”—context-sensitive judgment about whether, when, and how those patterns should be applied. Because wisdom is too broad to measure directly, the thesis operationalizes it as epistemic restraint, constraint fidelity, evidence seeking, impact awareness, and calibrated intervention.

The thesis proposes the **Sheath**, an independent supervisory layer placed around a code-generating agent. The Sheath maintains an immutable task contract and state ledger, assigns risk, constrains generation, invokes sandboxed build/test/analysis tools, challenges unsupported claims, and returns one of four auditable decisions: accept, revise, block, or escalate. Deterministic policy and executable tools decide questions they can observe; a learned critic is used only for residual judgments such as scope equivalence or rationale quality. This hybrid separation avoids asking the same generator to be its sole judge.

The central hypothesis is that evidence-grounded, independent supervision will increase verified success and reduce constraint violations on held-out repository tasks relative to direct generation and same-model self-critique. A paired experiment compares direct generation, instruction-file prompting, same-model reflection, rule-and-tool Sheath supervision, and—if its training gate is met—Sheath with a residual learned critic. Primary outcomes combine hidden-test success, explicit constraint adherence, and absence of severe security regressions. Secondary outcomes include false interventions, cost, latency, patch scope, retries, and calibration. CyxWiz is specified as the experiment-orchestration and artifact-tracking layer, subject to verification of its implemented capabilities.

The contribution is deliberately narrow: a falsifiable architecture, typed research records, a staged implementation, and a reproducible evaluation protocol. A custom small model, sparse mixture-of-experts architecture, continual learning, and broader claims about general intelligence remain conditional extensions rather than assumptions.

## 1. Introduction

### 1.1 Background

Code generation benchmarks established that language models can synthesize functions and complete local programming tasks. Repository-level software engineering is a different problem. It requires locating relevant files, understanding existing contracts, editing multiple artifacts, running commands, responding to failures, and avoiding regressions. SWE-bench formalized this gap using real GitHub issues and associated repositories [1]. SWE-agent subsequently showed that the interface between a model and its environment materially affects repository-task performance [2]. These findings motivate treating the agent as a system—not merely a model response.

Tool-using and iterative methods provide important building blocks. ReAct interleaves reasoning and action [3]. Reflexion and Self-Refine use feedback across iterations [4,6]. CRITIC explicitly grounds critique in external tools [5]. Yet feedback-free self-correction can fail or degrade reasoning [7], and model judges can exhibit systematic biases [9]. These results suggest that iteration alone is insufficient: the source, independence, observability, and calibration of feedback matter.

### 1.2 Research Problem

A coding agent can state “the bug is fixed” after producing a patch even when it has not run the relevant test. It can satisfy visible behavior while violating an architectural constraint. It can expand a small task into an unnecessary refactor. It can interpret its own plausible explanation as evidence. The common defect is not always missing programming knowledge; it is a missing boundary between a proposal and the evidence required to accept that proposal.

Existing controls often appear as instruction files, long prompts, self-review requests, or post-hoc human review. Each helps, but each leaves an empirical question. Does a separate, stateful, evidence-grounded supervisor improve outcomes beyond simply giving the generator more instructions or asking it to critique itself?

### 1.3 Thesis Statement

For repository-level software-engineering tasks, an independent supervisory layer that preserves explicit constraints and binds completion claims to external evidence will improve verified correctness and constraint adherence over direct generation and same-model self-critique; a risk-adaptive policy can obtain this improvement without imposing full scrutiny on every task.

This statement contains no claim of bug-free code, universal safety, or artificial general intelligence. It predicts a measurable difference between controlled systems on fixed tasks.

### 1.4 Contributions

This work aims to contribute:

1. an operational definition of engineering supervision;
2. a minimal generator–supervisor architecture with typed state and evidence;
3. a dataset schema joining tasks, constraints, patches, tool evidence, and review outcomes;
4. a paired evaluation that separates prompting, self-critique, independent critique, and tool grounding;
5. a risk-adaptive intervention policy and explicit false-positive analysis;
6. reproducible CyxWiz-compatible artifacts for data, training, and evaluation.

The ten reasoning patterns found in the exploratory documents are not claimed as a contribution until independently validated against real engineering reviews.

## 2. From Knowledge to Engineering Supervision

### 2.1 The Knowledge–Judgment Distinction

The founding idea in the local research notes is that human intelligence is not equivalent to retaining all information. A person who does not know how to perform a task can identify that limitation, find relevant information, apply it under constraints, test the outcome, and retain a reusable method. The notes call this ability *wisdom*. In software engineering, the useful part of this metaphor is the boundary between possessing a code pattern and judging whether that pattern is appropriate here.

The metaphor becomes scientifically useful only after translation into observable behavior. This thesis therefore does not attempt to measure wisdom as a human or philosophical property. It defines **engineering supervision** through five dimensions:

- **Epistemic restraint:** distinguish known facts, inferences, and unknowns; obtain context rather than inventing it.
- **Constraint fidelity:** preserve explicit scope, architecture, compatibility, security, and operational limits.
- **Evidence seeking:** bind claims to tests, builds, static analysis, or traceable repository evidence.
- **Impact awareness:** identify likely downstream effects and select verification proportionate to them.
- **Calibrated intervention:** intervene strongly when risk and evidence justify it, remain quiet on low-risk valid changes, and expose uncertainty.

These dimensions can be scored independently. A system may be good at requesting tests but poor at recognizing scope drift. This is preferable to a single vague “intelligence” score.

### 2.2 Dialectical Reasoning as a Control Loop

The exploratory work describes a thesis–antithesis–synthesis loop. For engineering purposes, it is formalized as:

1. **Proposal:** the generator produces a plan, edit, or claim.
2. **Challenge:** the supervisor searches for a counterexample, violated constraint, missing artifact, or unsupported inference.
3. **Resolution:** evidence causes acceptance, a concrete revision request, a policy block, or escalation.

This is not debate for its own sake. A challenge has value only if it refers to an observable requirement or produces a check that can change the decision. Repeated free-form criticism without new evidence is terminated by a retry and cost budget.

### 2.3 Provisional Failure Taxonomy

The local debate exercise generated ten candidate reasoning failures: concept drift, premise–conclusion inversion, special pleading, poor analogy fitness, unfalsifiability, misplaced burden of proof, inconsistent standards, “mystery” escape, false dichotomy, and failure to integrate a concession. They are useful sensitizing concepts, but one designed debate cannot establish their completeness or prevalence.

The taxonomy will therefore be handled in two stages. First, two or more annotators will code a corpus of real code-review and agent-failure traces, initially using open coding rather than forcing the ten labels. Second, the provisional labels will be retained, merged, split, or rejected based on observed coverage and inter-rater agreement. Software-specific categories—incorrect repository model, missing regression test, environment mismatch, invalid state transition, resource-lifecycle failure, concurrency or atomicity error, unsafe tool action, dependency hallucination, and incomplete requirement—are expected to emerge.

### 2.4 Lean Engineering Principle

Wirth argues for disciplined methodology, coherent decomposition, and continuous reduction of unnecessary complexity [12]. Applied here, model size, new experts, graph nodes, prompts, and intervention stages are costs until experiments show they improve the primary outcome. The minimum system uses explicit records and existing tools. It does not begin by training a multi-billion-parameter model.

## 3. Related Work and Research Gap

### 3.1 Repository-Level Agents

SWE-bench shifted evaluation from isolated code synthesis to real issue resolution across repositories [1]. SWE-agent demonstrated that a purpose-built agent–computer interface can improve an LM agent's ability to navigate, edit, and test software [2]. This thesis shares their view that tooling and environment design are causal parts of performance. Its distinct object of study is the supervisory boundary: what evidence and constraints must be satisfied before an agent may treat a task as complete?

### 3.2 Reasoning, Acting, and Feedback

ReAct combines reasoning traces with environment actions [3]. Reflexion stores linguistic feedback from prior trials [4], while Self-Refine uses the same model to produce feedback and revisions [6]. These methods show that iterative feedback can improve task performance. However, Huang et al. report that intrinsic self-correction without external feedback can be ineffective or harmful on reasoning tasks [7]. The Sheath experiment directly separates same-model reflection from independent supervision and further separates language critique from executable evidence.

CRITIC is the closest conceptual predecessor because it uses external tools to evaluate and revise outputs [5]. The proposed advance is domain-specific and stateful: an immutable engineering contract, a claim–evidence ledger, a risk policy, explicit intervention calibration, and comparison against instruction-file controls on repository tasks. Whether this bundle provides a meaningful benefit is an empirical question, not assumed novelty.

### 3.3 Constitutions and Instruction Files

Constitutional AI uses explicit principles to generate critiques, revisions, and preference feedback for alignment [8]. Repository instruction files similarly state local rules. The Sheath does not claim that principles are new. It asks whether enforcing project-specific engineering constraints through an independent runtime boundary is more reliable than placing those rules only in the generator's context.

The comparison is important because “internalizing” all rules in model weights can reduce adaptability and provenance. Some rules must remain explicit, versioned, and organization-specific. The likely design is therefore hybrid: stable engineering patterns may be learned; hard permissions, current repository contracts, and auditable policies remain external.

### 3.4 Learned Judges and Static Tools

LLM judges can evaluate open-ended properties but may show position and other biases [9]. Static analyzers, compilers, test runners, schema validators, and linters have narrower scope but observable semantics. The Sheath uses a precedence rule:

1. hard authorization and safety policy;
2. deterministic repository evidence;
3. calibrated learned judgment;
4. human decision when confidence or evidence is insufficient.

The learned critic must never overwrite a failing test with a textual claim that the code “should work.”

### 3.5 Efficient Adaptation and Sparse Models

LoRA provides a parameter-efficient way to adapt a pretrained model [10]. Sparse expert architectures can offer conditional computation, but research also documents routing and parameter-efficiency difficulties [11]. Consequently, a small dense classifier or critic with parameter-efficient fine-tuning is the default learned component. Mixture-of-experts is a stage-gated alternative, not part of the core claim.

### 3.6 Composable Agent Harnesses

DeepSeek Harness is a developer-preview agent host in which model adapters, tools, session logging, and the agent loop are replaceable plugins with typed request and tool interception points [20]. It is built on Cordis, which studies reversible effects and reactive dependencies for dynamically composed software [21]. These mechanisms are relevant deployment infrastructure: they can provide native seams for pre-flight, in-flight, and post-flight supervision, and their append-only session design reinforces the requirement that model-visible context be reconstructable. They do not establish that a supervisory policy is correct or improves software outcomes. Sheath therefore remains host-neutral; DeepSeek Harness is a conditional integration option rather than part of the causal claim or current implementation dependency.

## 4. Research Questions and Hypotheses

### 4.1 Research Questions

**RQ1.** Does independent, evidence-grounded supervision improve verified success on held-out repository-level tasks compared with direct generation?

**RQ2.** Which part of supervision produces the effect: explicit instructions, iterative reflection, critic independence, state tracking, or executable tool evidence?

**RQ3.** How accurately can the supervisor detect constraint violations without blocking correct work, and how well calibrated are its intervention probabilities?

**RQ4.** Can risk-adaptive scrutiny preserve most of the reliability gain while reducing latency, token use, tool calls, and user-visible interruptions?

**RQ5.** After a rule-and-tool baseline, does a trained small critic improve ambiguous engineering judgments enough to justify its training and inference cost?

### 4.2 Hypotheses

**H1—Verified success.** Sheath-supervised runs will have a higher paired verified-success rate than direct-generation runs.

**H2—Constraint adherence.** Sheath supervision will reduce blocking scope, architecture, security, and compatibility violations per task.

**H3—External evidence.** Independent tool-grounded critique will outperform same-model, feedback-free self-critique on verified success.

**H4—Adaptive efficiency.** Risk-adaptive supervision will be non-inferior to full supervision within a preregistered success margin while using fewer resources.

**H5—Learned residual value.** A small learned critic will improve detection of ambiguous violations over the rule-and-tool supervisor without exceeding a preregistered false-intervention ceiling.

The claim that learned weights outperform an instruction file is an ablation hypothesis, not a premise. No hypothesis requires a 3B parameter model.

## 5. Formal System Model

### 5.1 Task Contract

A task is represented as

\[
T = (G, C, S, O, R),
\]

where \(G\) is the goal, \(C\) the constraints, \(S\) the success criteria, \(O\) the explicitly out-of-scope set, and \(R\) the risk context. The raw user request is retained unchanged; normalized fields are derived and traceable.

The request is evidence, not an infallible specification. Pre-flight may identify ambiguity, internal conflict, unsafe intent, or a requirement that contradicts repository or higher-priority policy. Any material inferred requirement remains unresolved until the user confirms it. The supervisor is accountable to the versioned contract, evidence, and authorization hierarchy—not to uncritical agreement with either the requester or generator.

A run produces a sequence

\[
\tau = (a_1, o_1, p_1, e_1, \ldots, a_n, o_n, p_n, e_n),
\]

where \(a_i\) is an action, \(o_i\) an observation, \(p_i\) a patch or proposal, and \(e_i\) evidence. Evidence has provenance, timestamp, command or source, exit status, scope, and freshness.

### 5.2 Claim–Evidence Relation

For each completion claim \(q\), the supervisor evaluates:

\[
support(q) = f(E_q, C_q, freshness, provenance),
\]

where \(E_q\) is evidence attached to the claim and \(C_q\) is the subset of constraints it must satisfy. “Tests pass” requires a recorded successful command on the final patch. “Secure” cannot be established globally; it must be replaced by bounded statements such as “the configured analyzer reported no findings of severity high or critical, and security regression tests passed.”

### 5.3 Decision Policy

The decision set is

\[
D = \{accept, revise, block, escalate\}.
\]

- **Accept:** all mandatory checks have current supporting evidence and no blocking violation is present.
- **Revise:** a correctable defect or missing artifact has a specific remediation.
- **Block:** a hard policy, authorization, or safety constraint is violated.
- **Escalate:** the task requires authority, unavailable context, or judgment beyond calibrated confidence.

A pass is not proof of defect-free software. It means the declared contract and configured verification policy are satisfied by the available evidence.

### 5.4 Risk-Adaptive Intensity

Let normalized risk features be change surface \(x_s\), privilege/data sensitivity \(x_p\), reversibility \(x_r\), uncertainty \(x_u\), and historical failure rate \(x_h\). A simple interpretable score is

\[
\rho = \sigma(w_0 + w_sx_s + w_px_p + w_rx_r + w_ux_u + w_hx_h),
\]

where \(\sigma\) is the logistic function. Thresholds route tasks to light, standard, or deep scrutiny. Initial weights and thresholds are manually specified and preregistered; learned calibration is considered only after sufficient labeled runs.

## 6. Sheath Architecture

### 6.1 Essential Components

The minimal architecture has seven components:

1. **Contract normalizer:** converts a raw request into goals, constraints, success criteria, exclusions, and unresolved questions.
2. **State ledger:** stores immutable task fields, repository version, claims, actions, decisions, and evidence.
3. **Risk triage:** selects scrutiny intensity using visible task features.
4. **Generator adapter:** gives the same generator interface to every experimental condition.
5. **Sandboxed tool runner:** executes allowed builds, tests, linters, and analyzers and records complete outputs.
6. **Supervisor:** applies hard rules, checks claim–evidence links, and optionally invokes a learned critic for ambiguous cases.
7. **Decision and artifact exporter:** returns a verdict with reasons and writes the reproducibility record.

The components communicate through typed records rather than hidden conversational assumptions. The system does not require the supervisor to generate application code.

CyxCode CLI is the intended first user-facing coding-agent adapter. In that deployment, CyxCode hosts the coding model and interaction surface while Sheath owns pre-flight contracts, proposal validation, mandatory evidence, and verdicts. CyxCode is not a required research dependency: the adapter conforms to the same generator protocol used by every experimental condition. The repository now contains strict TypeScript execution/export parsing and a Python `CyxCodeGenerator` that maps canonical execution results through the trusted patch boundary. A deterministic local-provider fixture has exercised the real source entrypoint, but the pinned binary has not yet been joined to the Python adapter in a complete experiment run.

### 6.2 Pre-Flight, In-Flight, and Post-Flight

**Pre-flight** checks whether the task is sufficiently defined and safe, challenges contradictory or infeasible requirements, identifies local instructions and tests, freezes the confirmed task contract, and selects risk. It asks for clarification only when missing information or an inferred requirement would materially change the solution.

**In-flight** monitors proposed plans and tool actions. It blocks unauthorized destructive actions, detects changes outside the declared scope, and updates the evidence ledger. It does not interrupt every harmless choice.

**Post-flight** compares the final patch with the contract, requires fresh verification on the final state, runs risk-selected checks, and audits the final summary against recorded evidence.

### 6.3 Hybrid Governance

The architecture divides supervision by observability:

| Question | Preferred mechanism |
|---|---|
| Did the command succeed? | Exit status and captured output |
| Did hidden tests pass? | Isolated test harness |
| Were forbidden paths changed? | Diff/path policy |
| Was an unauthorized command requested? | Deterministic authorization policy |
| Does the patch preserve an API contract? | Tests plus structured/learned review |
| Is a change materially out of scope? | Contract diff plus calibrated critic |
| Is the rationale sufficient? | Rubric, critic, and sampled human audit |

This boundary is central. A probabilistic critic may suggest where to inspect, but it may not manufacture tool evidence.

The architecture is transport-neutral. Tools may be reached through direct process adapters, an MCP-compatible adapter, or another typed interface; no transport is itself a source of truth. Mandatory checks remain owned by the decision policy and cannot be bypassed merely because the generator also has direct tool access.

### 6.4 Human Control and Appeals

The user can inspect every blocking reason and evidence item, correct a normalized constraint, or approve a scoped exception. Overrides are logged rather than silently weakening policy. High-impact permissions and ambiguous security decisions remain human-controlled. This resolves the “who watches the supervisor?” problem pragmatically: validation uses deterministic checks, independent evaluation, sampled expert review, and an explicit appeal path rather than an infinite chain of supervisors.

## 7. Data and Learning Method

### 7.1 Data Unit

The central dataset unit is not a code blob. It joins:

- task and repository snapshot;
- explicit constraints and success criteria;
- generator proposal or patch;
- tool actions and observations;
- supported and unsupported claims;
- reviewer findings and severity;
- final outcome and hidden-test result.

The machine-readable contract is defined in `schemas/task_record.schema.json`; run evidence is defined in `schemas/run_record.schema.json`.

### 7.2 Sources

Initial examples should come from repositories with permissive research-compatible licenses, reproducible builds, tests, and traceable issue-to-fix histories. Candidate sources include issue/patch pairs, review comments, CI failures, compiler diagnostics, security fixes, and deliberately constructed constraint-conflict tasks. Repository instructions and published engineering texts may be used only when their licenses or explicit permissions allow the intended extraction, training, and redistribution; access alone is not permission to convert a work into training data. The first corpus focuses on C, C++, and Python as specified in the original research scope.

Synthetic examples may expand coverage but cannot be the sole source. Each synthetic violation must pass deterministic parsing/build checks where applicable and human sampling. Repository-family and temporal splits reduce leakage; near-duplicate detection is applied across splits.

### 7.3 Annotation

Annotators record observations before labels. Each blocking label requires a quoted constraint, affected location, severity, expected evidence, and remediation. At least two annotators label the validation and test subsets. Agreement is reported per category; ambiguous cases are adjudicated without altering the held-out outcome after model inspection.

The provisional ten-pattern taxonomy is evaluated through open coding of real review threads. A category is promoted to the main ontology only if it has an operational definition, sufficient prevalence, acceptable agreement, and demonstrated relevance to an engineering outcome.

### 7.4 Learning Stages

**Stage 0—No learned supervisor.** Implement hard policies, schemas, evidence binding, and tool routing. This is the causal baseline for the architecture.

**Stage 1—Small residual critic.** Fine-tune a suitable open model or encoder on ambiguous pass/revise/block/escalate decisions, missing-artifact classification, and scope/constraint entailment. Parameter-efficient adaptation such as LoRA is preferred for the first experiment [10].

**Stage 2—Risk calibration.** Calibrate intervention probabilities on a held-out calibration set. Choose thresholds from the declared cost of false acceptance and false intervention.

**Stage 3—Conditional specialization.** Only if Stage 1 shows domain interference or unacceptable latency/accuracy trade-offs, compare separate adapters or a sparse expert design. Routing quality, total and active parameters, memory, latency, and expert collapse must be measured [11].

No continual-learning mechanism is enabled in the confirmatory experiment. Updating weights during evaluation would destroy comparability. New organization rules remain explicit until a separately evaluated update is released.

## 8. Implementation with CyxWiz

### 8.1 Role of CyxWiz

The local documents designate CyxWiz as the research execution layer for ingestion, preprocessing, training, evaluation, visualization, and artifact export. Those are requirements, not verified facts about the engine version available elsewhere. Integration begins with a capability audit. Missing nodes are implemented through narrow external-runner adapters that read and write the same versioned records.

### 8.2 Reproducible Graphs

The desired graph set is:

1. **Ingest:** repository/issue/review sources → normalized raw tables.
2. **Curate:** license and quality filters → generated-file removal → deduplication → split assignment.
3. **Label:** task contracts and reviewer annotations → validated records.
4. **Train:** frozen manifest → tokenizer/model/adaptation configuration → checkpoints and curves.
5. **Evaluate:** frozen tasks and conditions → isolated runners → metrics and run records.
6. **Report:** immutable results → tables, figures, failure analysis, and provenance index.

Every graph export must include source revision, graph revision, schema version, random seeds, environment image, dependency lock, model identifier, prompt/policy hash, dataset manifest, and artifact checksums.

### 8.3 Minimal Runtime Loop

```text
receive raw task
normalize and freeze task contract
inspect repository instructions and test entry points
compute risk and choose required checks

for attempt in 1..attempt_budget:
    request generator proposal or revision
    validate proposed tool actions against policy
    execute allowed actions in sandbox and record observations
    compare patch and claims with contract and evidence

    if hard policy violated: return BLOCK
    if authority or essential context missing: return ESCALATE
    if correctable gaps exist: issue concrete revision and continue
    if all required checks have fresh evidence: return ACCEPT

return ESCALATE with unresolved findings and complete run record
```

The loop must have attempt, time, token, and tool budgets. “Continue until correct” is not an executable stopping rule.

### 8.4 Delivery Gates

- **Gate A:** schemas validate and one task can be replayed from its record.
- **Gate B:** rule/tool supervisor completes a 20-task engineering smoke set.
- **Gate C:** four experimental conditions run identically through the harness.
- **Gate D:** pilot reliability and annotation agreement are adequate for a powered study.
- **Gate E:** learned critic beats Stage 0 on its residual task without excessive false interventions.
- **Gate F:** confirmatory analysis is executed from a frozen preregistration and manifest.

The detailed component interfaces and folder layout appear in [Implementation_Blueprint.md](Implementation_Blueprint.md).

## 9. Evaluation Methodology

### 9.1 Experimental Conditions

Each held-out task is run under matched conditions with the same generator, decoding settings, repository snapshot, resource limit, and safe tool access:

- **A—Direct:** generator receives the task and standard tool interface.
- **B—Instruction file:** generator also receives the repository engineering rules in context.
- **C—Self-reflection:** generator critiques and revises its own result using a fixed protocol.
- **D0—Stage-0 Sheath:** independent state, policy, risk routing, and mandatory tool/evidence checks, without a learned critic.
- **D1—Learned Sheath:** D0 plus the residual critic, run only if its pilot gate is met.

D0 isolates the value of the supervisory architecture without model training; D1 versus D0 measures whether learned ambiguity handling earns its added complexity. If budget permits, full-intensity and risk-adaptive variants test H4.

Task-condition order and seeds are randomized. Sandboxes are reset between runs. A task's hidden tests and reference outcome are inaccessible to the generator and supervisor.

### 9.2 Task Set

The pilot begins with 50 tasks to validate infrastructure, not to support definitive claims. A power analysis based on the paired pilot outcomes determines the confirmatory sample. The local 100-task proposal is a useful stratification target: compile/build repair, failing-test repair, small feature, test writing, refactor, security fix, and documentation/understanding. The final distribution and minimum effect size are frozen before confirmatory evaluation.

Repositories are split by repository family, not random files. Tasks that overlap training data, public solutions known to the evaluated models, or each other through near-duplicate patches are flagged and excluded or reported in a separate contaminated stratum.

### 9.3 Primary Outcome

For task \(i\), define verified success:

\[
VS_i = I(test_i) \cdot I(constraint_i) \cdot I(security_i),
\]

where each indicator is one only if mandatory hidden/visible tests pass, no blocking explicit constraint is violated, and no predefined severe security regression is found. Documentation-only tasks use a preregistered executable or blinded rubric substitute; they are not mixed into the primary code-task estimate without stratification.

The primary comparison is the paired difference in \(VS\) between the preregistered Sheath condition (D0 or D1) and A. Secondary confirmatory comparisons are the chosen Sheath condition versus B and C; D1 versus D0 tests H5.

### 9.4 Secondary Metrics

- compile and visible/hidden test pass rate;
- blocking violations by category and severity;
- patch size and unrelated-file count;
- severe static-analysis findings introduced;
- attempts, tool calls, tokens, latency, and estimated cost;
- false-intervention rate on valid proposals;
- precision, recall, F1, AUROC, and area under the precision–recall curve for supervisor findings;
- Brier score and reliability diagram for calibrated intervention probability;
- escalation and human-override rate;
- evidence completeness and final-summary factuality.

The thesis reports both false acceptance and false intervention. A supervisor that blocks everything is safe-looking but useless.

### 9.5 Analysis

Paired binary outcomes are analyzed with McNemar's test and paired bootstrap confidence intervals for absolute success-rate differences. Count and continuous outcomes use paired bootstrap intervals and a preregistered paired nonparametric or mixed-effects model as appropriate. Repository and task category are treated as grouping factors. Multiple secondary comparisons use a declared correction or are labeled exploratory.

Effect sizes and confidence intervals are primary; p-values are not presented alone. Failed infrastructure runs are distinguished from agent failures. Missing outcomes, retries, exclusions, and manual overrides are reported transparently.

### 9.6 Ablations

The following removals identify the source of any gain:

1. remove independent critic but retain tools and ledger;
2. remove executable tools but retain language critique;
3. remove persistent constraints/state;
4. replace the independent critic with same-model self-critique;
5. replace learned rules with an in-context instruction file;
6. disable risk adaptation and run full scrutiny;
7. remove each high-level category of checks.

An ablation is added only if it answers an RQ; a combinatorial sweep is avoided.

## 10. Validity, Ethics, and Safety

### 10.1 Internal Validity

Potential confounds include unequal context length, extra compute in supervised conditions, stochastic generation, task-order effects, leaked solutions, and evaluator bias. Controls include matched budgets, repeated seeds where feasible, randomized order, frozen snapshots, repository-level splits, hidden tests, and blinded human review. Because D0 and D1 may use more compute, results are shown both at fixed budgets and as quality–cost frontiers.

### 10.2 Construct Validity

Tests do not prove general correctness, static analyzers do not prove security, and code-review labels can be subjective. The thesis therefore uses a conjunctive bounded outcome, reports each component separately, and avoids treating “wisdom” as directly measured. The five supervisory dimensions must be represented by multiple tasks rather than a single proxy.

### 10.3 External Validity

The initial C, C++, and Python repositories cannot represent all languages, organizations, or proprietary systems. Public issue fixes may differ from greenfield development. Results are restricted to the sampled repositories, task types, models, and tool environment. Cross-language and cross-model tests are replications, not assumptions.

### 10.4 Data and Licensing

The frozen Phase-6 manifest records exact revision and digests, publication and collection dates, SPDX license expression and list version [22, 23], license evidence, lineage, contamination, and artifact-specific rights. OSI approval [24] is evidence that a software license passed the Open Source Definition process; it is not treated as an automatic project-specific decision about dataset analysis, redistribution, or model training. Those uses are recorded separately as allowed, prohibited, or unknown. Unknown research-analysis rights cause quarantine. Secrets, personal data, generated binaries, vendored code, and repository content incompatible with the declared use are excluded. Books, articles, and instruction files are not mined merely because they are readable. Security examples are defensive repair tasks in isolated environments; exploit-enabling artifacts are not released when doing so would create material risk. The 100–300-case seed is development-only and cannot enter confirmatory testing.

### 10.5 Tool Safety

Execution occurs in disposable sandboxes with resource limits, network disabled by default, path restrictions, command allow/deny policy, and complete logs. Destructive or external side effects require explicit authorization and are absent from benchmark tasks. Model text never grants itself permission.

## 11. Expected Results and Reporting Plan

No empirical result is available. The following outcomes are plausible and must be distinguished:

- **Positive:** the preregistered Sheath condition improves verified success over A and C with acceptable false interventions; the central hypothesis is supported for the tested scope.
- **Tool-driven:** D0 improves over A, while D1 adds no material gain; the value lies in state and external verification, not a learned critic.
- **Prompt-equivalent:** B matches the chosen Sheath condition; instruction files are sufficient under the tested context and budget, weakening the internalization claim.
- **Overhead-limited:** Sheath improves quality but loses on cost or latency; the useful result is a risk threshold or a restricted high-stakes use case.
- **Null/negative:** Sheath does not improve or harms outcomes; failure analysis identifies whether the critic, contract extraction, policy, or feedback loop caused the result.

The final results chapter must include a task flow diagram, exclusions, dataset table, condition configuration, primary outcome with confidence interval, secondary metrics, calibration plot, cost frontier, ablations, category-level results, and representative successes and failures. All examples should link to immutable run IDs.

## 12. Limitations

The Sheath adds another fallible component. Independence does not guarantee correctness, and a small critic may fail on reasoning that exceeds its capacity. Hard rules can be brittle; learned rules can be opaque and miscalibrated. External tools cover only properties they can observe. Human review remains necessary for high-impact ambiguity.

The original design's fixed model size, expert count, sub-20-ms latency, and superiority to larger models have no evidence in this repository. Model weights also cannot replace changing local policy: rules encoded only in weights are hard to audit, revoke, and update. A hybrid design is more defensible than “the model is the rulebook.”

The provisional reasoning taxonomy may reflect the debate prompt more than software practice. The dataset may encode reviewer preferences, popular-project norms, and historical security blind spots. Public code can contaminate model pretraining in ways that are difficult to detect. Benchmark success may overestimate open-ended maintenance performance.

Finally, the thesis does not demonstrate AGI. At most, it tests a general systems principle: a capable but fallible generator may become more reliable when paired with explicit state, tools, independent challenge, and human-governed boundaries. Broader transfer requires separate evidence.

## 13. Work Plan

| Phase | Output | Exit criterion |
|---|---|---|
| 1. Specification | Frozen schemas, ontology draft, safety policy | Records validate; task can be replayed |
| 2. Corpus pilot | 100–300 curated examples and annotation guide | Agreement and provenance thresholds met |
| 3. Rule/tool MVP | Minimal supervisor and isolated runner | 20-task smoke suite completes reproducibly |
| 4. Experimental pilot | 50 paired tasks across A–D | Harness stable; effect and variance estimated |
| 5. Learned critic | Stage-1 adapted critic and calibration report | Residual benefit exceeds false-intervention gate |
| 6. Confirmatory study | Frozen task set, preregistration, complete runs | Primary analysis reproduced from manifests |
| 7. Thesis completion | Results, discussion, artifacts, paper draft | Claims trace to evidence and reviewer checklist |

Dates depend on available compute, CyxWiz capability, annotation capacity, and institutional deadlines. The schedule should be converted to calendar milestones only after those constraints are known.

## 14. Conclusion

This thesis begins with an intuitive observation: knowing many programming patterns is not the same as exercising engineering judgment. It converts that observation into a narrower scientific proposition. Generated code is a proposal; tests, tools, constraints, and review supply the evidence needed to accept it.

The Sheath is an independent evidence boundary around a coding agent. Its essential innovation is not a metaphor, a large taxonomy, or a predetermined model architecture. It is the disciplined separation of generation from acceptance, implemented through an immutable task contract, explicit state, sandboxed observation, calibrated critique, and auditable decisions.

The research succeeds only if the controlled experiment shows a meaningful reliability gain at an acceptable cost. If a simple rule-and-tool system creates that gain, the lean result is stronger than an unnecessarily complex model. If a small learned critic adds residual value, the data will justify it. If neither helps, the negative result will still clarify which supervisory assumptions fail. In every case, evidence—not fluency—determines the conclusion.

## References

The numbered bibliography is maintained in [References.md](References.md).
