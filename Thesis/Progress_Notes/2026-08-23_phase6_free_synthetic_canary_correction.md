# Phase 6 Free Synthetic-Canary Correction — 2026-08-23

## Outcome

The provider policy now has two explicit tiers. A free CyxCode model may be used once for an infrastructure canary when every input is generated locally, public, non-sensitive, and unrelated to the thesis corpus. That single canary completed and captured a proposal changing only `arithmetic.py`. Benchmark submission remains fail-closed. No paid Zen account or credential was used.

## Correction

The earlier provider-replacement review applied benchmark-grade data-use requirements to the synthetic canary. That was unnecessarily strict: disclosed provider improvement use is acceptable for a disposable synthetic prompt that contains no user, thesis, repository-history, or benchmark data. The earlier record remains valid for benchmark admission and is not rewritten.

The selected route is `opencode/mimo-v2.5-free`. It is explicitly configured because the pinned CyxCode catalog predates the current Zen listing. CyxCode's provider implementation supplies its `public` token path when no paid key is present. The completed canary establishes operational availability only for this dated infrastructure observation.

## Enforced Boundary

[run_cyxcode_synthetic_canary.py](../pilot_data/run_cyxcode_synthetic_canary.py) generates a two-file arithmetic fixture and accepts no candidate ID, ledger, dataset, replay-evidence, or source-snapshot arguments. It permits one bounded attempt, stores raw response and patch artifacts only under `.replay_cache`, and writes only digest-level evidence to the thesis package. Its unit tests reject benchmark markers and confirm the free explicit route.

The benchmark runner remains blocked before task access. Redis, fmt, Astropy, and the other calibration candidates are not authorized by this correction. The source digest remained unchanged, response and canonical patch artifacts were retained under `.replay_cache`, and a post-run Docker query found no container derived from the pinned CyxCode image.

## Evidence and Validation

- [phase6_synthetic_canary_gate.json](../pilot_data/review_evidence/phase6_synthetic_canary_gate.json) SHA-256: `3a0e6960938906908327426ad05f5a5b6ce9ba75d2553ddd9e57c5b21151c5e0`.
- Validator SHA-256: `6bb36c3e0ea711c639a684bcc51e38ef3a5daa7b378d1c506613defc7509d672`.
- Runner SHA-256: `55c269852df4c8aec5c729d0ecc17a5fa33d8057d16b15e5b8fdfba9d9acfeab`.
- [phase6_synthetic_free_canary.json](../pilot_data/proposal_evidence/phase6_synthetic_free_canary.json) SHA-256: `b4891e6d46617852f8625d69c1746179fd1cd1cdc6f6142f0bf44d2715694829`.
- All 40 pilot-data tests pass after the recorded attempt.

## Next Gate

Treat the completed result only as infrastructure evidence. Next, resolve outbound provider-use rights and generator exposure/contamination for Redis and fmt. Establish Astropy's research-analysis basis or replace it. No benchmark proposal may run before those independent gates pass.
