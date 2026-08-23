# Phase 6 CyxCode Free-Model Canary — 2026-08-20

## Completed Slice

The pinned CyxCode 2.3.8 image exposes six zero-price, text-output, tool-capable `opencode` entries. Live isolated smokes showed that registry presence is not equivalent to current public availability:

- `opencode/big-pickle` accepted the built-in `public` token, returned `OK`, and reported cost `0`;
- `opencode/gpt-5-nano` returned HTTP 401 even with that token; and
- the four advertised `*-free` Mimo, MiniMax, and Nemotron identifiers returned `Model not found`.

The pilot runner now pins `opencode/big-pickle`, materializes the exact content-addressed source archive, exposes only the problem statement and pilot contract, and excludes the gold patch, test patch, evaluation script, and blinded checks. Raw responses and patches remain under `.replay_cache`; public evidence contains hashes and bounded metadata only.

## Canary Results and Corrected Diagnosis

The original Redis attempt with `gpt-5-nano` failed authentication and is preserved in [phase6_cal_001_cyxcode_proposal.json](../pilot_data/proposal_evidence/phase6_cal_001_cyxcode_proposal.json). Public-token Big Pickle attempts for Redis and fmt reached the 900-second bound, but the first bridge version surfaced Windows cleanup `EACCES` instead of the underlying provider result. Those records remain preserved and quarantined:

- [phase6_cal_001_cyxcode_proposal_public.json](../pilot_data/proposal_evidence/phase6_cal_001_cyxcode_proposal_public.json)
- [phase6_cal_008_cyxcode_proposal_public.json](../pilot_data/proposal_evidence/phase6_cal_008_cyxcode_proposal_public.json)
- [phase6_cal_008_cyxcode_proposal_public_1800s.json](../pilot_data/proposal_evidence/phase6_cal_008_cyxcode_proposal_public_1800s.json)

Inspection during the 1,800-second fmt attempt found the actual provider response: HTTP 429 `FreeUsageLimitError` with `Rate limit exceeded. Please try again later.` An independent trivial `OK` smoke reproduced the same response. The cloud returned the error in seconds; CyxCode then treated it as retryable and continued silently, making the TUI/bridge appear slow. The session diff was empty (`[]`). The diagnostic logs contained no task or patch body and were not retained as public artifacts.

No canonical proposal patch has been captured. These are quota/generator-infrastructure observations, not benchmark outcomes or evidence of model latency.

## Cleanup Correction and Validation

The bridge protocol now supplies an explicit cleanup command. The Docker wrapper records the exact container ID, force-removes that container on timeout, erases container-owned state inside the pinned image, and only then permits host cleanup. A 30-second populated-state fmt timeout returned `run-timeout`, retained a bounded response artifact, left no container, and left no `cyxcode-pilot-*` directory.

CyxCode now treats exhausted free usage as terminal while preserving retries for ordinary transient 429 responses. A separate `CYXCODE_DISABLE_STATE_CONTEXT=1` experiment switch disables resume, memory, graph, wiki, and state commits. This prevents the current prompt from being auto-committed and reintroduced as apparent previous-session context. A deterministic local-provider test captures the complete model-visible request and confirms those state blocks are absent.

- Pilot runner SHA-256: `37adcea3e630be23db6134cd52077dac13f115cca98fb5fd2b3e1a13a081f565`
- CyxCode runner SHA-256: `1859e5db417f0860c9799024a5343ba3ebc01b6ccba08c9b4114be59f75195f3`
- Docker wrapper SHA-256: `5d5ae1a4a42fe0ed44b6a8d26179f2edf71ba5260e9bde0a80d9d8f71239e1ff`
- Image ID: `sha256:f0a466626dcb1f123645ea9a40e2e7ef55c046dd7b76b8726d603605751b560c`
- Executable SHA-256: `8c9d82ad1dc42961666470248e9a2241a45eeb1f0327fa6ec6aefe61c6c1a31e`
- Validation: CyxCode typecheck passes; 9/9 adapter tests and 19/19 retry tests pass together; 138/138 Sheath tests pass on Python 3.12 and 3.14; 18/18 pilot-data tests pass.

## 2026-08-21 Fail-Fast Confirmation

One new fmt canary used the rebuilt pinned image with a 180-second wall-time. It completed after approximately 136 seconds with one terminal error event rather than entering the former retry loop. The retained response envelope confirms HTTP 429 `FreeUsageLimitError`, no timeout, no model output, zero changed files, successful isolated-state removal, and no remaining adapter container.

- Public evidence: [phase6_cal_008_cyxcode_proposal_public_short_canary.json](../pilot_data/proposal_evidence/phase6_cal_008_cyxcode_proposal_public_short_canary.json)
- Public evidence SHA-256: `2c6b297bb1a6525a9fd9acf2317b7933bbd9f75fb16c9d6f3672b98b58d2eea2`
- Restricted response artifact: `sha256:2b7e6b730180171732a4288ef46873ff25283aaf27cf0a6355b182e25580ca21`
- Proposal status: not produced; candidate remains quarantined and no ledger event is appended.

## Next Bounded Step

The 2026-08-21 rights/provider audit supersedes the quota-retry plan. Do not submit more benchmark content to Big Pickle: the official documentation describes it as a stealth model, does not fix its underlying identity or revision, and states that free-period data may be used to improve the model. The runner now blocks provider submission before reading task inputs. The later two-candidate review remains the benchmark-grade gate. Its paid-credential requirement for a synthetic canary was subsequently corrected: one MiMo-V2.5 Free attempt may use only a generated public non-sensitive fixture through CyxCode's public-token path. See [2026-08-23_phase6_free_synthetic_canary_correction.md](2026-08-23_phase6_free_synthetic_canary_correction.md).
