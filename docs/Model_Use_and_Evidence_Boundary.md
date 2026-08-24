# Model Use and Evidence Boundary

## Purpose

CyxSheath tests whether an independent supervisory layer improves the verified behavior of coding agents. Model availability, experimental admissibility, and production suitability are different decisions. A model can be accessible and technically capable without producing valid evidence for a specific thesis comparison.

## Roles in CyxSheath

```text
Task
  -> coding generator (CyxCode + selected model)
  -> proposed workspace change
  -> Sheath Stage 0 supervision
  -> independent checks, evidence, revision, and verdict
```

The coding model proposes changes. Deterministic Sheath Stage 0 controls contracts, tools, isolation, patch extraction, tests, evidence, and acceptance. The downloaded Qwen model is a generator; it is not the future learned Sheath critic. A CyxSheath-D1 residual critic is conditional work for Phases 9–10 after the Stage-0 pilot identifies a stable problem that rules and tools cannot resolve.

## What the Experiment Needs

The experiment needs a **capable but imperfect** coding model, not a deliberately poor one. A model that is too weak creates a floor effect: Sheath can reject its failures but cannot supply missing programming competence. A model that already solves nearly every task—or has memorized public solutions—creates a ceiling or contamination effect that hides whether supervision helped.

The core comparison holds the generator, task, snapshot, and budget constant:

```text
same model without Sheath  vs.  same model with Sheath
```

Support for the hypothesis requires repeated, paired improvement in independently verified correctness or constraint adherence, with the added latency and cost reported. One successful patch does not establish the claim, and a null or negative result remains a valid research outcome.

## Why Some CyxCode Models Are Benchmark-Blocked

“Blocked” means not admitted for the current evidence-producing operation. It does not mean the model is poor or permanently rejected.

| Question | Synthetic infrastructure task | Thesis benchmark task |
|---|---|---|
| Was the exact answer previously public? | No; authored for the check | Often yes |
| Could the model have trained on it? | Negligible for a fresh fixture | Frequently unknown |
| May a cloud provider retain the input? | Acceptable only for approved public input | Must satisfy task rights and protocol |
| Must the model identity be fixed? | Preferred | Required for reproducibility |
| Does success measure coding quality? | No; it proves the pipeline works | Only after all admission gates pass |

CyxCode can expose many free or frontier models. “Free” describes price, not data treatment, version stability, training history, or scientific suitability. Public SWE-bench tasks and solutions may have appeared in a model's training corpus. If the model returns a known patch, the experiment cannot distinguish reasoning from memorization. Cloud submission can also expose repository content or contaminate later runs.

The completed free MiMo canary used only a generated public arithmetic fixture. It proved the CyxCode response-and-patch path without authorizing MiMo, GPT-family aliases, Big Pickle, Qwen, or any other generator for real benchmark input. Testing every free catalog model would add cost without answering the primary Sheath hypothesis.

## Why Use the Downloaded Qwen Model

Qwen2.5-Coder-7B-Instruct Q4_K_M was selected as a small, code-specialized, reproducible local generator. Its exact repository revision, file, byte size, checksum, quantization, and license are recorded. Local execution avoids provider quotas and outbound prompt retention while fitting the available host memory.

Local execution does not solve benchmark contamination: Qwen's exact training membership is undisclosed. It must first pass runtime and synthetic gates, then receive a separate contamination decision before any quarantined candidate is exposed.

Current evidence records verified download/import and one earlier service-side load/unload within resource limits, but load-health protocol acceptance remains failed. A dependency-free synchronous Python transport now passes fixtures and an identity-only temporary-client `lms --help` probe with numeric exit 0, bounded output, unchanged identity, and no residual process or listener. A separate [transport-integration decision](../Thesis/pilot_data/review_evidence/phase6_load_health_transport_integration_decision.json) freezes short synchronous controls, one monitored load child, exact service ownership, resource and inventory checks, and fail-safe cleanup. This proves design readiness only. Runner implementation and harmless fixtures are authorized; LM Studio runtime, inference, HTTP serving, and the local synthetic canary remain blocked.

## Production Use of Frontier Models

Production optimizes useful, safe outcomes rather than a clean causal benchmark comparison. After the thesis mechanism is validated, Sheath can supervise frontier models, including models excluded from a thesis benchmark because of possible benchmark exposure.

```text
low-risk task  -> local generator -> Sheath verification -> accept or escalate
hard task      -> frontier model  -> Sheath verification -> revise or review
high-risk task -> strict Sheath policy -> mandatory human approval
```

Benchmark contamination is usually not a production defect when solving a genuinely new company task. Provider data terms, repository authorization, secrets, model stability, latency, cost, and operational evaluation still matter. Free cloud models may suit public, non-sensitive work but remain unsuitable for proprietary repositories when their retention or training terms are incompatible.

Evidence that Sheath improves one small generator does not automatically establish the same numerical benefit for a frontier model. Each production generator needs model-specific regression and safety evaluation. Even when a frontier model rarely needs revision, Sheath may add value through independent tests, file-scope enforcement, constrained tools, provenance, abstention, and fail-closed deployment decisions.

## Decision Rules

1. Separate **available**, **synthetically usable**, **benchmark-admitted**, and **production-approved** states.
2. Do not select a deliberately weak generator to manufacture an improvement.
3. Do not interpret public-benchmark success as uncontaminated reasoning without evidence.
4. Keep the same generator and budget across paired Sheath comparisons.
5. Admit additional models only when they answer a research or production question.
6. Keep hidden checks, gold patches, and verification evidence outside model context.
7. Treat local execution, provider approval, contamination clearance, and production approval as separate gates.

The authoritative current sequence is maintained in the [research and implementation roadmap](../Thesis/Research_and_Implementation_Roadmap.md); operating restrictions are maintained in the [usage guide](../usage/README.md).
