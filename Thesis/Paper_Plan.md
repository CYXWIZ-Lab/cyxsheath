# Paper Plan

## Proposed Title

**The Sheath: Does Evidence-Grounded Independent Supervision Improve Software-Engineering Agents?**

Use a question title until the confirmatory result is known. A title that asserts improvement is justified only by the completed analysis.

## One-Sentence Contribution

We isolate and measure the effect of an independent, stateful supervisor that binds a coding agent's completion claims to explicit constraints and executable evidence.

## Paper Structure

1. **Introduction:** repository agents produce proposals whose acceptance requires evidence; state the central contrast and contributions.
2. **Related Work:** repository benchmarks, agent–computer interfaces, self-reflection, tool-grounded critique, constitutions, and learned-judge limitations.
3. **Method:** task contract, state/evidence ledger, risk-adaptive policy, hybrid rule/tool/critic design.
4. **Experiment:** conditions A, B, C, D0, and gated D1; held-out repositories, outcomes, budgets, randomization, and analysis.
5. **Results:** primary paired effect, reliability–cost frontier, false interventions, calibration, and ablations.
6. **Failure Analysis:** representative cases where supervision helps, harms, or escalates.
7. **Limitations and Ethics:** contamination, evaluator fallibility, bounded security claims, data licenses, and external validity.
8. **Conclusion:** restrict the claim to the tested system and scope.

## Required Figures

- Minimal Sheath flow: contract → generator → sandbox/tools → evidence ledger → decision.
- Paired verified-success plot with confidence intervals.
- Quality–cost frontier across conditions.
- Supervisor reliability/calibration plot.
- Optional error taxonomy only if validated on real review data.

## Required Tables

- Task and repository composition.
- Exact condition/configuration comparison.
- Primary and secondary outcomes.
- Ablations.
- Common false acceptances and false interventions.

## Publication Gate

Do not submit the work as an empirical systems paper until:

- the protocol is frozen and all conditions have completed;
- the primary result is reproducible from immutable run records;
- at least one independent reviewer checks outcome adjudication;
- negative and null results are retained;
- every quantitative claim maps to a table, figure, or released artifact;
- CyxWiz's actual role is documented rather than inferred from the proposal.

If implementation is incomplete, submit only as a position or research-agenda paper and label the architecture and results as proposed.

## Claim Language

Prefer: “Under the tested models, repositories, and budgets, supervision changed verified success by …”

Avoid: “guarantees reliable code,” “proves wisdom,” “makes any model AGI-level,” or “eliminates the need for engineering instructions.”

## Reusable Thesis Material

- Manuscript Sections 1–4 become the introduction and related work.
- Sections 5–8 become the method.
- Section 9 and `Experiment_Protocol.md` become the experiment.
- Sections 10–12 become validity, ethics, and limitations.
- The final paper discussion must be rewritten from actual results; it should not reuse the manuscript's hypothetical outcomes as findings.
