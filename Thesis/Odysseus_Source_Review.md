# Odysseus Source Review

## Review Status

This review covers the official `odysseus-dev/odysseus` repository as contemporary implementation prior art. The inspected default `dev` branch is pinned at commit `7026cf40b5f96f166f6b76e4236527d7dce243b1`; the curated `main` branch is pinned at `451900fc151554f4c8654d1e4d3dadc1d029b047`. Sources were accessed on 2026-08-26. No repository was cloned, no Odysseus code or dependency was imported, and no CyxSheath runtime or experiment condition changed.

Odysseus is a broad self-hosted AI workspace for chat, agents, local and API models, tools, MCP, memory, research, documents, email, and model-serving workflows. CyxSheath is narrower: it is an independent evidence and decision boundary for repository-level coding agents. CyxCode remains the first coding-agent adapter, and CyxWiz Engine remains the proposed future data, training, and evaluation platform.

## Relevant Implementation Patterns

| Odysseus pattern | Relevance to CyxSheath | Boundary |
|---|---|---|
| Digest-bound tool approvals | Supports the value of sealing an action to owner, session, run, input, workspace, document state, effects, and integrity metadata | Its task/chat continuation scopes are not equivalent to Sheath's benchmark and one-shot runtime contracts |
| Teacher escalation | Demonstrates a practical student-failure, stronger-teacher, reusable-procedure loop | Regex or LLM judgment plus skill persistence is not independent executable verification or a trained Sheath critic |
| Untrusted-context wrappers | Reinforces treating web, email, memory, skill, document, and tool text as data rather than authority | Prompt instructions mitigate but do not eliminate injection or replace sandboxing |
| Adaptive context budget | Offers a simple model-window-aware policy for local models | Future adapter concern; not required for the current load-only health gate |
| Foreground/background resource gate | Shows how shared local-model capacity can prioritize interactive work | Operational scheduling, not evidence of model or supervisor quality |
| Blind model comparison | Useful interface inspiration for paired model inspection | Does not replace randomized, preregistered, artifact-backed thesis conditions |

## Adopt Now

1. **Cite exact-action approval as related implementation prior art.** Retain CyxSheath's stronger immutable authorization, evidence, and replay requirements rather than copying the implementation.
2. **Add teacher escalation to the related-work distinction.** It is a useful example of a stronger model correcting a weaker one and producing reusable instructions. The thesis must distinguish this from D0 tool-grounded supervision and the future D1 residual critic.
3. **Preserve untrusted-data provenance.** Any future learned critic, skill generator, or escalation trace must receive provenance-marked data, exclude secrets and hidden tests, and pass independent replay before becoming trusted guidance.
4. **Keep context budgeting as a later adapter requirement.** The effective prompt budget should depend on verified model capacity and declared experiment limits, with the exact model-visible prompt retained for replay.

## Defer Behind Evidence Gates

- An Odysseus user interface or external orchestration adapter.
- Automatic teacher escalation in production.
- Converting successful traces into candidate Sheath procedures.
- Background model scheduling and hardware-aware serving recommendations.
- MCP, memory, document, email, calendar, or general assistant features.

These are outside the Phase-6 local-generator activation path. Revisit them only after the CyxCode baseline identifies a measured limitation and after their effect can be isolated experimentally.

## Reject for the Current Thesis

- Replacing CyxCode, the Sheath core, or the controlled experiment with Odysseus.
- Treating a teacher model's confidence, a regex match, or a generated skill as correctness evidence.
- Persisting model-generated procedures directly into trusted policy without replay, review, provenance, and revocation.
- Running benchmark tasks through an unsandboxed shell or filesystem tool boundary.
- Copying the large agent loop or adopting the full workspace architecture. At the inspected revision, `src/agent_loop.py` is 6,442 lines; the repository roadmap also identifies prompt bloat, integration reliability, provider probing, and refactoring work.
- Inferring maturity or scientific validity from popularity, feature count, commits, or community activity.

## Security and Licensing Decision

The official threat model describes Odysseus as a privileged private-network admin console and acknowledges open gaps including no shell/filesystem sandbox, an SSRF route, duplicated search modules, and coarse token scopes. These boundaries make it unsuitable as the thesis benchmark sandbox without separate hardening and validation.

The official repository is licensed `AGPL-3.0-or-later`. CyxSheath currently has no repository-wide license. Therefore:

- ideas, public behavior, and architecture may be analyzed and cited;
- no Odysseus source is copied, modified, vendored, or linked into CyxSheath now;
- any future integration requires a written licensing decision and, where appropriate, qualified legal review; and
- a clean-room implementation must not be described as avoiding license obligations without legal confirmation.

## Design Decision

Retain Odysseus as related implementation prior art, not a dependency or experimental baseline. The most valuable research connection is the contrast between *teacher-generated reusable advice* and *independent evidence-grounded acceptance*. Odysseus shows that escalation and skill distillation are practical product mechanisms; CyxSheath must test whether immutable constraints, external evidence, calibrated intervention, and a residual critic improve verified coding outcomes.

This review does not alter Phase 6. The next implementation slice remains the locale-independent engine-inventory correction and a repeated execution decision.

## Verified Primary Sources

- Odysseus contributors, [official repository README](https://github.com/odysseus-dev/odysseus/tree/7026cf40b5f96f166f6b76e4236527d7dce243b1), architecture, features, branch policy, and AGPL license.
- Odysseus contributors, [threat model](https://github.com/odysseus-dev/odysseus/blob/7026cf40b5f96f166f6b76e4236527d7dce243b1/THREAT_MODEL.md), trust boundary and known gaps.
- Odysseus contributors, [tool approvals](https://github.com/odysseus-dev/odysseus/blob/7026cf40b5f96f166f6b76e4236527d7dce243b1/src/tool_approvals.py), digest binding, scope, claim, and expiry behavior.
- Odysseus contributors, [teacher escalation](https://github.com/odysseus-dev/odysseus/blob/7026cf40b5f96f166f6b76e4236527d7dce243b1/src/teacher_escalation.py), failure detection, escalation, untrusted-trace handling, and skill persistence.
- Odysseus contributors, [context budgeting](https://github.com/odysseus-dev/odysseus/blob/7026cf40b5f96f166f6b76e4236527d7dce243b1/src/context_budget.py), model-window-aware input budgeting.
- Odysseus contributors, [roadmap](https://github.com/odysseus-dev/odysseus/blob/7026cf40b5f96f166f6b76e4236527d7dce243b1/ROADMAP.md), acknowledged reliability, context, security, and refactoring work.
