# `tolook.md` Source Review

## Review Status

This review covers all 1,060 lines of `tolook.md` (SHA-256 `520268B73ACAC56C4F4E03F376A447EE6900A8AF5B9ACEADADEA1148B444E8CB`). The file is an exploratory conversation, not a citable research source. It combines a mistaken DeepSeek-R1 analysis, unsupported guesses about DeepSeek Harness, a later Cordis discussion, generated pseudocode, and a speculative stitched thesis. Encoding damage also makes several equations unreliable.

Primary-source checking establishes that DeepSeek Harness is a developer-preview agent harness built as a Cordis plugin tree. Its model adapter, tool registry, session log, and agent loop are replaceable plugins. Cordis separately formalizes runtime composition through reversible effects and reactive coeffects. Neither source establishes the trajectory-control experiments, cost equations, or Sheath performance claims attributed to it in `tolook.md`.

## Adopt Now

1. **Reconstructable model context.** DeepSeek Harness states that model-visible inputs must be derivable from its append-only session log. Sheath now persists the exact canonical prompt and redacted model-visible configuration alongside their digests in the completed pinned-image executor path.
2. **Typed interception seams.** `agent/pre-step`, request, turn, and tool pre/post-execution events demonstrate a practical host interface for pre-flight, in-flight, and post-flight supervision. This supports the existing transport-neutral adapter design; it does not require a new core abstraction.
3. **Deployment alternative.** A future DeepSeek Harness plugin could be compared with the external CyxCode adapter if native in-flight interception becomes necessary. It must be separately pinned and audited because the project explicitly warns of breaking changes.
4. **Direct efficiency outcomes.** Keep tool calls, tokens, attempts, wall time, cost, and false interventions. These already appear in the experiment protocol and are more reproducible than inferred “failures prevented.”

## Defer Behind Evidence Gates

- Cordis as a runtime substrate for loading and unloading optional Sheath components.
- Native DeepSeek Harness integration or migration away from CyxCode.
- Intra-turn learned trajectory control beyond deterministic action authorization.
- Dynamic expert loading, organization-specific adapters, and lifecycle benchmarks.

These become relevant only after the CyxCode baseline and D0 pilot identify a concrete limitation that the additional host or lifecycle machinery solves.

## Reject

- Treating DeepSeek Harness as a SWE-bench evaluation harness or a published lightweight trajectory controller.
- The invented controller-cost equation, “infinite ROI,” Governance Efficiency Rate, and `1 - tool_calls / optimal_tool_calls`; their denominators and counterfactuals are not operationally defined.
- The DeepSeek-R1/GRPO detour, mandatory visible `<think>` traces, and replacing DPO before a learned residual task exists. Private chain-of-thought is neither evidence nor a required artifact.
- Adding E15, fixing a 3B/14-expert MoE topology, training custom 110M experts, weekly LoRA updates, or continual learning before the existing residual-error gates pass.
- Arbitrary targets such as 95% accuracy, 20 ms latency, 50 ms dependency response, or fixed dataset percentages without pilot evidence.
- Claims of mathematical verification, perfect rollback, guaranteed reliability, AGI relevance, or demonstrated superiority. Reversible registration does not prove semantic compatibility, model quality, or recovery from every external side effect.
- The supplied mutable Python “inverse” sketch. It can lose overwritten values, depends on operation order, and does not capture filesystem, process, tool, or concurrent side effects.

## Amendments to Existing Work

| File | Amendment |
|---|---|
| `References.md` | Add the official DeepSeek Harness repository and Cordis preprint as distinct primary sources. |
| `Thesis_Manuscript.md` | Add related work on composable agent harnesses and explicitly separate host composition from supervisory correctness. |
| `Implementation_Blueprint.md` | Record DeepSeek Harness as an optional future host, not a replacement for the current CyxCode adapter. |
| `Research_and_Implementation_Roadmap.md` | Require reconstructable model-visible inputs in the next executor slice; keep host migration outside the immediate queue. |
| `Experiment_Protocol.md` | No amendment needed: direct cost, token, tool-call, retry, latency, and false-intervention outcomes already exist. |
| `Dataset_and_Model_Plan.md` | No amendment needed: it already excludes private chain-of-thought, gates MoE, and prohibits unreviewed continual learning. |
| Runtime code | No amendment now. Finish the pinned CyxCode executor before considering another host or plugin framework. |

## Decision

Retain DeepSeek Harness and Cordis as relevant related work and a conditional deployment option. Do not import either framework, change the experimental conditions, or expand the model architecture in the current phase. The smallest useful lesson is an auditable invariant: every input that can affect a model request must be versioned and reconstructable from stored artifacts.

## Verified Primary Sources

- DeepSeek AI, [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness), developer-preview repository and architecture documentation, accessed 2026-08-20.
- Cordiverse, [A Programming Paradigm for Spatiotemporal Composability](https://github.com/cordiverse/paper), preprint draft dated 2026-08-13 and under active revision, accessed 2026-08-20.
