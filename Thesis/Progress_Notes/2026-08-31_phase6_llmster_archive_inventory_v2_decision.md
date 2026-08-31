# Phase 6 LLMster Archive Inventory V2 Decision

## Outcome

A fresh validator-backed decision authorizes exactly one second metadata-only invocation of `inspect_exact_archive`. It does not reuse the consumed first authorization and permits no automatic retry.

The decision binds the fixture-verified separator implementation at commit `c99f5cd`, the exact 867,394,409-byte archive identity, the earlier fail-closed result, and the unchanged ZIP size, compression, traversal, collision, and declared-expansion ceilings.

## Boundaries

- Allowed: archive identity hashing, end-of-central-directory preflight, and central-directory metadata parsing.
- Forbidden: member-content reads, individual path retention, extraction, installation, execution, networking, and benchmark use.
- Safe `/` and `\` separators canonicalize to `/` before segment and collision checks.
- The authorization is consumed at function entry on success, rejection, or interruption.

Ten mutation tests reject reuse, source or correction drift, weakened separator rules, additional invocations, retry, member reads, path retention, and extraction. The complete pre-execution suite passes 418/418 on Python 3.12 and 3.14.

```powershell
python Thesis\pilot_data\validate_llmster_archive_inventory_v2_decision.py Thesis\pilot_data\review_evidence\phase6_llmster_archive_inventory_v2_decision.json
```

Commit and revalidate this decision before the one invocation. Authenticode, extraction staging, installation, and runtime remain separate later gates regardless of the inventory outcome.
