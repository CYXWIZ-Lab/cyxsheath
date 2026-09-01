# Phase-6 Candidate Inventory

## Status

`candidate_events.jsonl` is the append-only intake and decision ledger for the first calibration batch. Its 29 events cover 20 candidates: 7 C, 6 C++, and 7 Python tasks across 10 repository families. Events 21–23 record passed baseline/gold replay pairs for one case per language; events 24–26 close their privacy, secret, safety, lineage, and upstream file-scope reviews; events 27–28 record the exact-card research-analysis decisions for the two Multilingual cases; event 29 retains Astropy using pinned supplemental SWE-bench project evidence. Every current disposition remains `quarantined`; no record is an admitted seed case, annotation, or training example.

The candidates come from immutable revisions of [SWE-bench Multilingual](https://huggingface.co/datasets/SWE-bench/SWE-bench_Multilingual) and [SWE-bench Verified](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified). The former supplies C/C++; the latter supplies Python. Selection balances languages and repository families for pipeline calibration, not prevalence estimation or model evaluation. Public benchmark membership permanently excludes these cases from the confirmatory test set.

## Recorded Boundary

Each registration records the dataset and base revisions, instance and pull-request identity, source date, language, replay-image tag, exact upstream license-file URI and digest, separate rights decisions, and pending reviews. Dataset licensing is recorded separately from upstream source licensing: the pinned Multilingual card declares MIT, while the pinned Verified card has `NOASSERTION` because it contains no license declaration. JQ's mixed repository notice intentionally has `spdx_expression=null` pending file-scope review.

The 17 unreplayed cases retain `artifact.incomplete`, `license.unclear`, and `privacy.review_required`. The three replayed cases pass privacy/secrets/safety and 20-case exact/near-duplicate lineage review. Under the internal project policy, the exact pinned Multilingual card plus passed upstream file-scope evidence allow research analysis for Redis and fmt. The exact Verified card remains `NOASSERTION`; pinned supplemental evidence from the official SWE-bench project describes its code and data, identifies Verified, documents model inference, and applies its MIT license. That evidence permits internal research analysis of Astropy without rewriting the exact card or granting downstream rights. All three retain `artifact.incomplete` and `contamination.uncertain`. Redistribution of metadata, labels, or source and model training remain `unknown`; this is a conservative research decision, not legal advice.

The pinned official harness required [swebench_windows_lf.patch](swebench_windows_lf.patch) because Windows text translation corrupted the generated Linux `eval.sh`. The two affected Redis runs are preserved but excluded; corrected runs use new IDs. [replay_requirements.lock.txt](replay_requirements.lock.txt) freezes the exact isolated Python environment, and [phase6_vertical_slice.json](replay_evidence/phase6_vertical_slice.json) content-addresses the accepted reports and test outputs. [phase6_non_replay_review.json](review_evidence/phase6_non_replay_review.json) retains only hashes, paths, counts, bounded decisions, and lineage scores. [phase6_source_snapshots.json](proposal_evidence/phase6_source_snapshots.json) records the base commit, tree, pinned image, and SHA-256 of each exact canonical Git archive. [phase6_rights_and_provider_exposure.json](review_evidence/phase6_rights_and_provider_exposure.json) binds the pinned card hashes, per-use decisions, outbound-submission history, and provider block. [phase6_outbound_and_astropy_decision.json](review_evidence/phase6_outbound_and_astropy_decision.json) records the supplemental Astropy basis and selects the existing local OpenAI-compatible seam as the primary generator path. None of these derived records contains task, hint, patch, test, script, matched-substring, source, prompt, or response bodies. Raw rows and logs remain restricted local artifacts while rights are unresolved.

## Validation

From the repository root, run:

```powershell
python Thesis\pilot_data\validate_candidate_events.py Thesis\pilot_data\candidate_events.jsonl --expect-count 20 --expect-language C=7 --expect-language 'C++=6' --expect-language Python=7
python Thesis\pilot_data\validate_replay_evidence.py Thesis\pilot_data\replay_evidence\phase6_vertical_slice.json
python Thesis\pilot_data\validate_non_replay_review.py Thesis\pilot_data\review_evidence\phase6_non_replay_review.json
python Thesis\pilot_data\validate_source_snapshots.py Thesis\pilot_data\proposal_evidence\phase6_source_snapshots.json
python Thesis\pilot_data\validate_rights_and_provider_exposure.py Thesis\pilot_data\review_evidence\phase6_rights_and_provider_exposure.json
python Thesis\pilot_data\validate_outbound_and_astropy_decision.py Thesis\pilot_data\review_evidence\phase6_outbound_and_astropy_decision.json
python Thesis\pilot_data\validate_provider_replacement_gate.py Thesis\pilot_data\review_evidence\phase6_provider_replacement_gate.json
python Thesis\pilot_data\validate_synthetic_canary_gate.py Thesis\pilot_data\review_evidence\phase6_synthetic_canary_gate.json
python Thesis\pilot_data\validate_host_capacity_and_connectivity.py Thesis\pilot_data\review_evidence\phase6_host_capacity_and_connectivity.json
python Thesis\pilot_data\validate_local_runtime_model_decision.py Thesis\pilot_data\review_evidence\phase6_local_runtime_model_decision.json
python Thesis\pilot_data\validate_local_model_activation_preflight.py Thesis\pilot_data\review_evidence\phase6_local_model_activation_preflight.json
python Thesis\pilot_data\validate_local_model_load_health_decision.py Thesis\pilot_data\review_evidence\phase6_local_model_load_health_decision.json
python Thesis\pilot_data\validate_local_model_load_health_recovery_decision.py Thesis\pilot_data\review_evidence\phase6_local_model_load_health_recovery_decision.json
python Thesis\pilot_data\validate_local_model_load_health_daemon_recovery_decision.py Thesis\pilot_data\review_evidence\phase6_local_model_load_health_daemon_recovery_decision.json
python Thesis\pilot_data\validate_local_model_load_health_result.py Thesis\pilot_data\review_evidence\phase6_local_model_load_health_result.json
python Thesis\pilot_data\validate_cli_exit_transport_decision.py Thesis\pilot_data\review_evidence\phase6_cli_exit_transport_decision.json
python Thesis\pilot_data\validate_cli_exit_transport_result.py Thesis\pilot_data\review_evidence\phase6_cli_exit_transport_result.json
python Thesis\pilot_data\validate_load_health_transport_integration_decision.py Thesis\pilot_data\review_evidence\phase6_load_health_transport_integration_decision.json
python Thesis\pilot_data\validate_load_health_runner_implementation_result.py Thesis\pilot_data\review_evidence\phase6_load_health_runner_implementation_result.json
python Thesis\pilot_data\validate_load_health_runner_execution_review.py Thesis\pilot_data\review_evidence\phase6_load_health_runner_execution_review.json
python Thesis\pilot_data\validate_load_health_runner_one_shot_correction_result.py Thesis\pilot_data\review_evidence\phase6_load_health_runner_one_shot_correction_result.json
python Thesis\pilot_data\validate_load_health_runner_fresh_execution_decision.py Thesis\pilot_data\review_evidence\phase6_load_health_runner_fresh_execution_decision.json
python Thesis\pilot_data\validate_load_health_runner_execution_decision.py Thesis\pilot_data\review_evidence\phase6_load_health_runner_execution_decision.json
python Thesis\pilot_data\validate_load_health_runner_execution_result.py Thesis\pilot_data\review_evidence\phase6_load_health_runner_execution_result.json
python Thesis\pilot_data\validate_shutdown_observation_implementation_result.py Thesis\pilot_data\review_evidence\phase6_shutdown_observation_implementation_result.json
python Thesis\pilot_data\validate_runtime_lifecycle_selection_decision.py Thesis\pilot_data\review_evidence\phase6_runtime_lifecycle_selection_decision.json
python Thesis\pilot_data\validate_llmster_acquisition_preflight_decision.py Thesis\pilot_data\review_evidence\phase6_llmster_acquisition_preflight_decision.json
python Thesis\pilot_data\validate_llmster_acquisition_implementation_result.py Thesis\pilot_data\review_evidence\phase6_llmster_acquisition_implementation_result.json
python Thesis\pilot_data\validate_llmster_download_execution_review.py Thesis\pilot_data\review_evidence\phase6_llmster_download_execution_review.json
python Thesis\pilot_data\validate_llmster_download_execution_decision.py Thesis\pilot_data\review_evidence\phase6_llmster_download_execution_decision.json
python Thesis\pilot_data\validate_llmster_storage_policy_superseding_decision.py Thesis\pilot_data\review_evidence\phase6_llmster_storage_policy_superseding_decision.json
python Thesis\pilot_data\validate_llmster_archive_acquisition_result.py Thesis\pilot_data\review_evidence\phase6_llmster_archive_acquisition_result.json
python Thesis\pilot_data\validate_llmster_archive_inventory_decision.py Thesis\pilot_data\review_evidence\phase6_llmster_archive_inventory_decision.json
python Thesis\pilot_data\validate_llmster_archive_inventory_result.py Thesis\pilot_data\review_evidence\phase6_llmster_archive_inventory_result.json
python Thesis\pilot_data\validate_llmster_separator_canonicalization_decision.py Thesis\pilot_data\review_evidence\phase6_llmster_separator_canonicalization_decision.json
python Thesis\pilot_data\validate_llmster_separator_canonicalization_result.py Thesis\pilot_data\review_evidence\phase6_llmster_separator_canonicalization_result.json
python Thesis\pilot_data\validate_llmster_archive_inventory_v2_decision.py Thesis\pilot_data\review_evidence\phase6_llmster_archive_inventory_v2_decision.json
python Thesis\pilot_data\validate_llmster_archive_inventory_v2_result.py Thesis\pilot_data\review_evidence\phase6_llmster_archive_inventory_v2_result.json
python Thesis\pilot_data\validate_llmster_extraction_staging_design_decision.py Thesis\pilot_data\review_evidence\phase6_llmster_extraction_staging_design_decision.json
python Thesis\pilot_data\validate_llmster_extraction_staging_implementation_result.py Thesis\pilot_data\review_evidence\phase6_llmster_extraction_staging_implementation_result.json
python Thesis\pilot_data\validate_llmster_real_staging_execution_decision.py --historical Thesis\pilot_data\review_evidence\phase6_llmster_real_staging_execution_decision.json
python Thesis\pilot_data\validate_llmster_real_staging_execution_result.py Thesis\pilot_data\review_evidence\phase6_llmster_real_staging_execution_result.json
python Thesis\pilot_data\validate_llmster_authenticode_review_design_decision.py Thesis\pilot_data\review_evidence\phase6_llmster_authenticode_review_design_decision.json
python Thesis\pilot_data\validate_llmster_authenticode_review_implementation_result.py Thesis\pilot_data\review_evidence\phase6_llmster_authenticode_review_implementation_result.json
python -m unittest discover -s Thesis\pilot_data -p 'test_*.py' -v
```

The validators are dependency-free. They check strict record shapes, hashes, revisions, URIs, reason/disposition compatibility, contiguous sequence numbers, supersession chains, baseline/gold oracle behavior, report digests, privacy-minimized review evidence, conservative rights/contamination states, and admission gates. Regenerating the review artifact additionally requires the pinned replay environment because it reads Parquet with PyArrow.

The non-replay artifact is reproducible after append-only ledger growth by selecting its original 23-event boundary:

```powershell
& .\.tools\swebench-7a21e057\Scripts\python.exe Thesis\pilot_data\review_candidate_artifacts.py --ledger Thesis\pilot_data\candidate_events.jsonl --ledger-through 23 --multilingual .replay_cache\datasets\multilingual-846e647.parquet --verified .replay_cache\datasets\verified-78f471b.parquet --output Thesis\pilot_data\review_evidence\phase6_non_replay_review.json --decisions Thesis\pilot_data\review_evidence\phase6_non_replay_decisions.json --candidate phase6-cal-001 --candidate phase6-cal-008 --candidate phase6-cal-014 --recorded-at 2026-08-20T17:20:00Z
```

## Append-Only Update Rule

Never edit an earlier decision to change its meaning. Append a `reviewed` event with the same `candidate_id` and `supersedes_event_id` equal to that candidate's latest event. Promote a case only after case-scoped rights, privacy, secret, safety, lineage, contamination, artifact, image-digest, and replay checks pass.

Source-snapshot capture covers 20 quarantined calibration candidates; three have passed replay and review evidence, but none is admitted for model training or a claimed benchmark result. The free MiMo canary proved only the external adapter path and remains blocked from benchmark input. The local Qwen2.5-Coder weight and LM Studio engine are pinned. A CPU-only load-health attempt passed load, inventory, sampling, resource, and unload checks but failed graceful desktop-service shutdown, so standalone `llmster` was selected. The sole archive request has now succeeded with exact published-checksum verification and preserved CLI, engine, and model identities. The authorization is consumed. Archive inventory, extraction, installation, runtime, prompt, HTTP server, CyxCode execution, synthetic canary, and benchmark routes remain blocked. Do not process the remaining 17 candidates until the local generator and contamination gates pass.

Superseding update (2026-08-30): the earlier request authorization above was never invoked and is now non-executable. Only `llmster_archive_acquisition_v2` is authorized for one request. It retains the 1-GiB archive ceiling, requires 9 GiB free before and 8 GiB after the write, and permits no retry or extraction. The complete suite passes 331/331 on both supported Python versions.

Acquisition result (2026-08-30): that one request succeeded. The 867,394,409-byte ignored archive independently matches SHA-256 `e6556e8edd7240c43da28aa555bac12197ba3e2199247bba773c81c6ae94170c` and the published SHA-512. The final reserve and preserved-state checks pass, no partial remains, and the authorization is consumed. The complete suite passes 341/341 on both Python versions. Do not inspect, extract, install, or execute the ZIP before the next validator-backed decision.

Inventory decision (2026-08-31): one exact identity-plus-central-directory inspection is authorized after commit and immediate revalidation. Fifteen adversarial fixtures enforce zero member-content reads, zero extraction, traversal/collision/link rejection, supported compression, and bounded declared expansion. Authenticode, extraction, installation, execution, networking, and benchmark use remain blocked.

Inventory result (2026-08-31): the sole authorization was consumed and rejected on `member_backslash_rejected` after archive identity and central-directory preflight passed. No member contents were read and nothing was extracted, written, installed, executed, or submitted. Do not retry. A fresh validator-backed design must define separator canonicalization and collision/traversal behavior before another inventory decision.

Separator correction (2026-08-31): safe backslashes now canonicalize to `/` in generated fixtures; traversal, absolute paths, empty segments, non-NFC names, and canonical/case-folded collisions still fail closed. The real archive was not read. A fresh one-shot decision remains mandatory before another inventory.

Inventory-v2 decision (2026-08-31): one fresh identity-plus-central-directory invocation is authorized only after commit and immediate revalidation. It retains zero member reads, zero path retention, and zero extraction. The authorization is consumed at entry and cannot be retried.

Inventory-v2 result (2026-08-31): the consumed invocation accepted 3,614 metadata entries under `.bundle` and `llmster.exe`, with zero member reads or extraction. File-level review, Authenticode, staging, installation, and execution remain blocked.

Staging design (2026-08-31): generated-fixture implementation is authorized for an exclusive marker-owned staging child with storage, containment, no-overwrite, manifest, cleanup, and rollback gates. The real archive, Authenticode tooling, installation, and execution remain blocked.

Real-staging result (2026-09-01): the one authorized call succeeded and is consumed. One marker-owned ignored child retains 3,595 payload files and 91 digest-bound signature candidates. No signature tool, installer, or target binary ran, and the retained child must not be modified or removed.

Authenticode review design (2026-09-01): only a dependency-free policy module and generated-fixture fake inspection are authorized. The policy must reproduce the full content manifest and exact candidate digest before inspection, normalize all documented PowerShell signature statuses plus timeout/tool error, and emit aggregate counts and a digest without retaining paths. `Valid` means syntactically valid, not publisher-trusted. Retained-child enumeration, Windows adapter implementation, signature tooling, networking, installation, execution, and cleanup remain blocked. The complete suite passes 501/501 on both supported Python versions.

Authenticode review implementation (2026-09-01): the platform-independent policy and 14 generated owned-tree fixtures now enforce the frozen admission, normalization, mutation, and aggregate-privacy contract. Ten implementation-result mutations source-bind the policy and unchanged staging ownership invariant. The complete suite passes 525/525 on both supported Python versions. The retained child and Windows signature tooling were not accessed; adapter implementation and real review still require separate decisions.
