# Phase 6 Provider-Replacement Gate — 2026-08-23

> **Correction:** This record remains authoritative for benchmark-provider admission, but its synthetic-canary conclusion was too strict. [2026-08-23_phase6_free_synthetic_canary_correction.md](2026-08-23_phase6_free_synthetic_canary_correction.md) supersedes only that conclusion; a paid Zen credential is not required for a wholly generated public fixture.

## Outcome

Two candidates were evaluated, exhausting the roadmap's lean comparison limit. Neither is approved for benchmark submission, and no model call was made. MiMo-V2.5 Free is rejected. GLM 5.2 is conditional for a synthetic non-benchmark canary only.

## Evidence Boundary

The audit pins the [OpenCode Zen source document](https://github.com/anomalyco/opencode/blob/bcf1103a8c8653acd7afdd5fc2ebd9f6e5486b3c/packages/web/src/content/docs/zen.mdx) at commit `bcf1103a8c8653acd7afdd5fc2ebd9f6e5486b3c`, SHA-256 `7a4009299eb55513cb58d37a9bd898c74a43ad5813dc8594d0c257d54fa2129f`. It also records the pinned CyxCode catalog separately because that catalog predates the current Zen listings.

Current Zen documentation says MiMo-V2.5 Free is offered while its team collects feedback and improves the model, and lists it as an exception to the general zero-retention/no-training policy. `opencode/mimo-v2.5-free` therefore fails the prompt-use gate even for a synthetic canary.

Zen lists `opencode/glm-5.2` as a paid, OpenAI-compatible route covered by the general zero-retention/no-training statement. [Z.ai's GLM 5.2 release record](https://z.ai/blog/glm-5.2) identifies the model and describes agentic coding post-training and public coding-benchmark evaluation. It does not establish absence of the three calibration cases from pretraining or post-training data. Benchmark exposure therefore remains `unknown`.

## Operational Result

No `OPENCODE_API_KEY` or other direct provider key is present. The pinned CyxCode catalog does not contain current `glm-5.2`, so an explicit configuration pin is required. No local inference runtime is installed; the detected GPU has 4 GiB VRAM. The project did not create an account, add billing, download weights, update the CyxCode catalog, or submit any prompt.

GLM 5.2 may receive only a synthetic fixture after an explicitly authorized Zen credential and a tested fixed configuration are supplied. That canary cannot authorize SWE-bench use; contamination remains a separate fail-closed gate.

## Validation

- [phase6_provider_replacement_gate.json](../pilot_data/review_evidence/phase6_provider_replacement_gate.json) SHA-256: `9e4990bd3272d478dd49b5e55a9f9d47cee09ff46ef85cfc54b5365797d8c604`.
- Validator SHA-256: `9755dc2fa8343dd7c56e40685224bb30322a073c1137b39c7d06e7e3b68fcdb2`.
- Six mutation tests prevent prompt retention, free-model admission, stale-catalog claims, unrecorded execution, and benchmark admission with unknown exposure.
- All 30 pilot-data tests pass; all 20 dataset candidates remain quarantined.

## Next Gate

The next action requires user authority because Zen access entails an account, credential, and paid usage. If authorized, configure a strict spending limit, inject the key only into isolated state, pin `glm-5.2` explicitly, and run one minimal synthetic fixture. Do not send Redis, fmt, Astropy, or any other benchmark case.
