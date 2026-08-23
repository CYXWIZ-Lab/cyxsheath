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
python -m unittest discover -s Thesis\pilot_data -p 'test_*.py' -v
```

The validators are dependency-free. They check strict record shapes, hashes, revisions, URIs, reason/disposition compatibility, contiguous sequence numbers, supersession chains, baseline/gold oracle behavior, report digests, privacy-minimized review evidence, conservative rights/contamination states, and admission gates. Regenerating the review artifact additionally requires the pinned replay environment because it reads Parquet with PyArrow.

The non-replay artifact is reproducible after append-only ledger growth by selecting its original 23-event boundary:

```powershell
& .\.tools\swebench-7a21e057\Scripts\python.exe Thesis\pilot_data\review_candidate_artifacts.py --ledger Thesis\pilot_data\candidate_events.jsonl --ledger-through 23 --multilingual .replay_cache\datasets\multilingual-846e647.parquet --verified .replay_cache\datasets\verified-78f471b.parquet --output Thesis\pilot_data\review_evidence\phase6_non_replay_review.json --decisions Thesis\pilot_data\review_evidence\phase6_non_replay_decisions.json --candidate phase6-cal-001 --candidate phase6-cal-008 --candidate phase6-cal-014 --recorded-at 2026-08-20T17:20:00Z
```

## Append-Only Update Rule

Never edit an earlier decision to change its meaning. Append a `reviewed` event with the same `candidate_id` and `supersedes_event_id` equal to that candidate's latest event. Promote a case only after case-scoped rights, privacy, secret, safety, lineage, contamination, artifact, image-digest, and replay checks pass.

Source-snapshot capture is complete. Redis and fmt prompts were submitted to `opencode/big-pickle`, but quota failures produced no model output or patch; Astropy was never submitted. Big Pickle remains blocked before input access. The completed `opencode/mimo-v2.5-free` canary used only a generated public arithmetic fixture and proved the external adapter path without authorizing benchmark input. Current official provider evidence says free MiMo inputs may be used to improve the model, so its benchmark route remains blocked while case model-training rights are unknown. Design decision `phase6-generator-boundary-001` selects CyxCode's existing local OpenAI-compatible seam as the primary path. The exact Qwen2.5-Coder weight is now checksum-verified in ignored `.local_models/`, symbolically imported without a second copy, and below the estimate-only 12 GiB ceiling. No model prompt ran. Because LM Studio reported a low-confidence GPU-memory label despite 0% offload, a bounded load-only health gate must measure actual RAM/VRAM and cleanup before any synthetic canary is separately authorized. The canary and benchmark routes remain blocked. The gold patches remain replay oracles, not generator proposals. Do not spend resources on the other 17 until the local generator identity and contamination treatment are pinned. SWE-bench Multilingual has only two C++ repository families, so later sourcing must add at least three more C++ families to satisfy the frozen seed-coverage gate.
