# Phase-6 Minimum POC v1 Result

## Outcome

The immutable six-run schedule completed once from runner commit `7914e2288872867a2b330bddd303b06d05f6505e`. One direct-condition call returned a proposal; independent verification rejected it. The other five scheduled runs produced no proposal because the anonymous CyxCode provider returned HTTP 429 `APIError` responses with `Rate limit exceeded. Please try again later.` No automatic provider retry occurred.

| Task | Condition | Status | Attempts | Verified | Wall seconds |
|---|---:|---|---:|---:|---:|
| range merge | A | completed / revise | 1 | no | 49.171 |
| range merge | D0 | infrastructure failure | 0 | no | 16.610 |
| query redaction | D0 | infrastructure failure | 0 | no | 16.547 |
| query redaction | A | infrastructure failure | 0 | no | 16.188 |
| retry delays | A | infrastructure failure | 0 | no | 18.547 |
| retry delays | D0 | infrastructure failure | 0 | no | 16.985 |

The five failed response envelopes each contain one CyxCode error event and a terminal assistant error with status 429 and `isRetryable=true`; none includes a `Retry-After` or rate-limit-reset header. Raw envelopes remain under `.replay_cache`. The public [curated result](../pilot_data/poc_evidence/phase6_minimum_poc_v1.json) retains only task-level measurements, bounded coordinator reason codes, identities, and digests.

## Interpretation

This is a provider-capacity feasibility failure, not a negative Sheath result. With five of six cells missing and no completed D0 run, neither a paired difference nor recovery rate can be computed. The result explicitly sets `inferential_claim_authorized=false`; it must not be cited as evidence that Sheath helps or harms coding performance.

The v1 schedule is consumed and must not be rerun. The next thesis-critical gate is a new versioned decision for the already pinned local Qwen2.5-Coder model through CyxCode's existing OpenAI-compatible seam. It must first pass one synthetic local canary, then may execute a newly frozen paired schedule. No additional cloud-provider comparison, runtime installation, model download, critic training, or Authenticode work is part of that slice.

## Validation

The dependency-free result validator checks source hashes, the predetermined six-cell order, internal summaries, failure consistency, unique record digests, and absence of raw-artifact fields. Seven mutation tests pass on Python 3.12 and 3.14.
