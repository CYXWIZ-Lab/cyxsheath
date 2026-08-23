# Phase 6 Rights and Provider-Exposure Audit — 2026-08-21

## Outcome

The audit partially resolves case rights and blocks further Big Pickle benchmark submission. All 20 candidates remain quarantined. This is an internal research-policy decision, not legal advice.

## Pinned Dataset Evidence

The [exact SWE-bench Multilingual card](https://huggingface.co/datasets/SWE-bench/SWE-bench_Multilingual/blob/846e647b9f33c0b51b739d005d13d85493c9af09/README.md) at revision `846e647b9f33c0b51b739d005d13d85493c9af09` declares MIT (README SHA-256 `c8b96ca94b43344556c610bcc4e836ef6b5472e2e1f9ca561aebd5cc011e3a14`). Combined with passed upstream file-scope review, this permits `research_analysis` for Redis `phase6-cal-001` and fmt `phase6-cal-008`. It does not establish permission to redistribute metadata, labels, or source, or to use the cases for model training; those decisions remain `unknown`.

The [exact SWE-bench Verified card](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified/blob/78f471bf655a3137b2e8a75af1501690ec009ec3/README.md) at revision `78f471bf655a3137b2e8a75af1501690ec009ec3` contains no license declaration (README SHA-256 `923e6b481ff75c709737251e602bdc311a9be49235b5c20107366747f5640fe4`). Astropy `phase6-cal-014` therefore retains `research_analysis=unknown` and `license.unclear`.

## Provider Decision

[OpenCode Zen documentation](https://opencode.ai/docs/zen) identifies Big Pickle as a stealth model and says data collected during its free period may be used to improve the model. Neither the underlying model identity, a weights revision, its training corpus, nor preexisting benchmark exposure is disclosed. Big Pickle is therefore blocked for further benchmark submission. Redis and fmt prompts were previously submitted but returned no model output; Astropy was not submitted.

The proposal runner now fails before reading task inputs while `PROVIDER_SUBMISSION_APPROVED` is false. A replacement must be named and versioned, disclose acceptable retention and training-use behavior, and permit a defensible benchmark-exposure assessment. Its first CyxCode check must use a synthetic non-benchmark fixture.

## Evidence and Validation

- Append-only ledger events 27–28 record the Redis/fmt rights changes; ledger SHA-256: `60975f9416bc044403ebee2a66f6df1d48947154dcec96d3d9b581769bf555ea`.
- [phase6_rights_and_provider_exposure.json](../pilot_data/review_evidence/phase6_rights_and_provider_exposure.json) SHA-256: `a0a8ee46a6521c880e33a935f6cf98c1ee155fa22f57b29442b72902f6d74221`.
- Rights/provider validator SHA-256: `0e82ba8db63556b1d3a178b20cd4714e7ad9cc5b50bdbb86072e9da5a00232b0`.
- Guarded proposal runner SHA-256: `37b8afa5dbc43de4797b7bcdba1122c6dcab40e4fba258c6fc2381d2db45118d`.
- Validation passed: 28 ledger events, 20 quarantined candidates, zero admitted cases, and 24/24 pilot-data tests.

## Next Gate

This two-candidate review is complete; see [2026-08-23_phase6_provider_replacement_gate.md](2026-08-23_phase6_provider_replacement_gate.md). MiMo-V2.5 Free was rejected, and GLM 5.2 is conditional for synthetic input only. An explicitly authorized paid credential and fixed CyxCode configuration are now required. Redis/fmt contamination and Astropy research-analysis rights remain unresolved.

> **Later resolution:** The synthetic credential conclusion was superseded by the completed free canary, and [2026-08-23_phase6_outbound_and_astropy_decision.md](2026-08-23_phase6_outbound_and_astropy_decision.md) later retained Astropy using supplemental official project evidence and selected the local OpenAI-compatible path. This paragraph is preserved as historical state, not current instruction.
