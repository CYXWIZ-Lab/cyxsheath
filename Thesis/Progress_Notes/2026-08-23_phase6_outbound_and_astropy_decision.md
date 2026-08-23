# Phase 6 Outbound-Use and Astropy Decision — 2026-08-23

## Outcome

Astropy is retained for internal research analysis, free MiMo remains blocked from benchmark input, and the existing CyxCode local OpenAI-compatible seam is selected as the primary proposal path. This is a project research-policy decision, not legal advice. It does not admit a case, authorize a model installation, or authorize benchmark execution.

## Case-Rights Decision

The exact SWE-bench Verified card remains `NOASSERTION`; it was not rewritten. Supplemental evidence is pinned to official SWE-bench commit `7a21e05772954cc81471ae19d56f436cecf43c54`: its [README](https://raw.githubusercontent.com/SWE-bench/SWE-bench/7a21e05772954cc81471ae19d56f436cecf43c54/README.md) describes the repository as code and data, identifies the Verified release, documents model inference, and applies the repository's [MIT license](https://raw.githubusercontent.com/SWE-bench/SWE-bench/7a21e05772954cc81471ae19d56f436cecf43c54/LICENSE). The [official Verified release description](https://openai.com/index/introducing-swe-bench-verified/) independently identifies it as a released subset of the original SWE-bench test set for model evaluation.

Under the frozen internal policy, that is sufficient for `research_analysis=allowed` for `phase6-cal-014`. It does not establish permission to redistribute metadata, labels, or source, or to use the case for model training. Append-only event `phase6-cal-review-009` preserves the exact card's `NOASSERTION`, removes only `license.unclear`, and leaves the case quarantined for `artifact.incomplete` and `contamination.uncertain`.

## Generator-Boundary Decision

Pinned [OpenCode Zen documentation](https://raw.githubusercontent.com/anomalyco/opencode/3a31c4ea801915c0b050df4b3842997ea62b6e93/packages/web/src/content/docs/zen.mdx) states that MiMo-V2.5 Free inputs may be used to improve the model. Because all three cases retain `model_training=unknown`, the free route cannot receive benchmark content. The earlier synthetic canary remains valid because its input was generated, public, non-sensitive, and non-benchmark.

CyxCode already documents a custom OpenAI-compatible local endpoint and its provider implementation accepts that configuration. The Docker proxy also exposes `host.docker.internal`, so the smallest design is to reuse this seam rather than add a provider abstraction. Decision `phase6-generator-boundary-001` selects local/offline generation as the primary Phase-6 path. Ollama was not installed during the audit; runtime installation, model selection, and benchmark access remain unauthorized.

## Evidence Identities

- SWE-bench README SHA-256: `7f6c99470e27965d4220a41f703766fb98ae2bf1b3bc5633deed76d6b30d1088`
- SWE-bench license SHA-256: `2bd2e08df7147f67a69b42c10efae09bd4bf119df397371036187d5dd1b02f57`
- OpenCode Zen document SHA-256: `7a4009299eb55513cb58d37a9bd898c74a43ad5813dc8594d0c257d54fa2129f`
- [decision record](../pilot_data/review_evidence/phase6_outbound_and_astropy_decision.json) SHA-256: `4e8c53c930008e2fb4b42e62663f479be2b956e3411a0ed7afdb13426974970d`
- Candidate ledger SHA-256 after event 29: `787caaf64e40f21c57a7fc67c14fc38c7defdffd8235ec50ed76b927658559db`
- Validator SHA-256: `181323589558fb52cb30a6b7421990a6db43971e9f0f402c8f787bbd12c45948`

## Validation and Limits

The new validator accepts the pinned decision and six mutation tests reject raw benchmark content, free-route authorization, training-right overclaim, premature local readiness, and license rewriting. The full pilot-data suite passes 46 tests. The candidate validator accepts 29 events, 20 quarantined candidates, the 7/6/7 language balance, and 10 repository families.

Preexisting generator exposure remains `unknown` because no selected local model identity or training-corpus evidence exists. Redis/fmt's earlier Big Pickle submissions are recorded as project exposure with no model output; Astropy was not submitted. No claim of contamination clearance or model quality is made.

## Next Gate

Audit host CPU, RAM, GPU, storage, and Docker-to-host connectivity. Then make an explicit runtime/model design decision covering model identity, weights digest, license, context/tool capability, resource ceiling, and contamination treatment. Only after that decision may one generated public non-benchmark fixture exercise the local seam. Benchmark input remains blocked until the local synthetic feasibility gate passes.
