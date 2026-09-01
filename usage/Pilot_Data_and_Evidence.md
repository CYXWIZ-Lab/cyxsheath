# Pilot Data and Evidence

## Current Phase-6 State

The pilot package has frozen schemas, an append-only ledger with 29 events for 20 revision-pinned C, C++, and Python candidates, a three-case vertical replay, source snapshots, bounded non-replay review, provider-policy records, and the completed synthetic canary record. Supplemental official project evidence now permits internal analysis of the Astropy case while preserving its exact card as `NOASSERTION`. All 20 candidates remain quarantined. No genuine model-backed benchmark proposal or benchmark result is claimed.

The authoritative status is [`Research_and_Implementation_Roadmap.md`](../Thesis/Research_and_Implementation_Roadmap.md). File roles and evidence boundaries are described in [`Thesis/pilot_data/README.md`](../Thesis/pilot_data/README.md).

## What Astropy Means Here

Astropy is an open-source Python library for astronomy and astrophysics. In this project it is an external codebase used by SWE-bench Verified to define realistic software-maintenance tasks; it is not Sheath, CyxCode, a critic model, or a training framework.

The completed Python vertical slice uses `astropy__astropy-12907` (candidate `phase6-cal-014`). Its controlled baseline replay reproduced the expected failing tests, and its gold-patch replay made those tests pass. This demonstrates that the pinned evaluation harness can distinguish the known broken and repaired states. It does **not** show that CyxCode generated the repair or that Sheath solved the task.

The case remains quarantined for incomplete proposal artifacts and uncertain model contamination. Internal research analysis is allowed, but redistribution and model-training rights remain unknown. Therefore:

- Running the validators below only checks curated evidence records; it does not execute or submit the Astropy task.
- Do not send its issue text, source, tests, hints, or patches to a model provider.
- Do not run the benchmark proposal path until the candidate-admission, generator-identity, and contamination gates are recorded as passed.

## Validate the Curated Records

Run these dependency-free checks from the repository root:

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
python Thesis\pilot_data\validate_load_health_runner_execution_decision.py Thesis\pilot_data\review_evidence\phase6_load_health_runner_execution_decision.json
python Thesis\pilot_data\validate_load_health_runner_execution_result.py Thesis\pilot_data\review_evidence\phase6_load_health_runner_execution_result.json
python Thesis\pilot_data\validate_shutdown_observation_implementation_result.py Thesis\pilot_data\review_evidence\phase6_shutdown_observation_implementation_result.json
python Thesis\pilot_data\validate_runtime_lifecycle_selection_decision.py Thesis\pilot_data\review_evidence\phase6_runtime_lifecycle_selection_decision.json
python Thesis\pilot_data\validate_llmster_acquisition_preflight_decision.py Thesis\pilot_data\review_evidence\phase6_llmster_acquisition_preflight_decision.json
python Thesis\pilot_data\validate_llmster_acquisition_implementation_result.py Thesis\pilot_data\review_evidence\phase6_llmster_acquisition_implementation_result.json
python Thesis\pilot_data\validate_llmster_download_execution_review.py Thesis\pilot_data\review_evidence\phase6_llmster_download_execution_review.json
python Thesis\pilot_data\validate_llmster_download_execution_decision.py Thesis\pilot_data\review_evidence\phase6_llmster_download_execution_decision.json
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
python Thesis\pilot_data\validate_llmster_windows_authenticode_adapter_design_decision.py Thesis\pilot_data\review_evidence\phase6_llmster_windows_authenticode_adapter_design_decision.json
python Thesis\pilot_data\validate_llmster_windows_authenticode_adapter_implementation_result.py Thesis\pilot_data\review_evidence\phase6_llmster_windows_authenticode_adapter_implementation_result.json
python Thesis\pilot_data\validate_llmster_authenticode_execution_preflight_design_decision.py Thesis\pilot_data\review_evidence\phase6_llmster_authenticode_execution_preflight_design_decision.json
python -m unittest discover -s Thesis\pilot_data -p 'test_*.py' -v
```

The current pilot-data suite passes 585 tests on Python 3.12 and 3.14 when run sequentially. Validation proves structural and internal consistency; it does not convert quarantined cases into admitted data or turn infrastructure output into scientific results.

The frozen minimum POC is executed only once from its clean committed runner baseline:

```powershell
python Thesis\pilot_data\run_phase6_minimum_poc.py --recorded-at <UTC-ISO-8601>
```

Do not rerun automatically after a provider, bridge, Docker, or runner failure. The command keeps raw artifacts under `.replay_cache`, writes task-level public evidence under `Thesis/pilot_data/poc_evidence/`, and refuses an existing output.

## Evidence Layers

- Candidate events record discovery, review, rejection, quarantine, and later decisions without erasing history.
- Replay evidence tests whether pinned upstream baseline and gold patches reproduce in the controlled harness.
- Non-replay review checks bounded privacy, secret, safety, lineage, license, and file-scope properties.
- Source snapshots bind a candidate to a content-addressed repository state.
- Provider gates separate synthetic infrastructure permission from stricter benchmark admission.
- Capacity evidence records privacy-minimized host limits, runtime readiness, and Docker-to-host connectivity without selecting or downloading a model.
- The runtime/model decision pins one exact synthetic-only weight, engine, license, resource policy, security boundary, and contamination block without downloading or executing the model.
- The activation preflight binds the verified local weight, symbolic import, inventory, low-confidence estimate, and cleanup while explicitly blocking model load, prompts, and benchmark input.
- The load-health decision authorizes one exact CPU-only memory activation with observed resource and cleanup gates while retaining zero inference and zero HTTP-server permission.
- The recovery decision classifies the first preload measurement failure without calling it a model failure and authorizes one measurement-only correction while inheriting the original contract.
- The daemon-recovery decision records attempt 2's pre-load service-lifecycle failure and requires exact root/readiness capture and cleanup for one final attempt under the unchanged contract.
- The final load-health result separates observed service-side activation and passing resource/cleanup bounds from failed protocol acceptance caused by CLI lifecycle and engine-identity drift.
- The engine/CLI recovery decision adopts the installed 2.29.1 engine and authorizes one new load-health execution through a digest-identical temporary client; it does not authorize inference or another automatic retry.
- The recovery result records service startup, missing numeric daemon-exit evidence, zero model-load invocations, complete final safety cleanup, protocol failure, and a consumed attempt.
- The CLI exit-transport decision fixture-tests a dependency-free synchronous numeric-exit seam and authorizes one identity-only `lms --help` probe; it does not authorize the daemon or model.
- The CLI exit-transport result records numeric exit 0, bounded output digests, clean process/port state, unchanged client identity, complete temporary cleanup, and a consumed probe.
- The corrected runner execution decision pins raw UTF-8 engine ordering, corrected source identities, the clean baseline, exact CPU-only settings, and one execution while retaining zero-inference and zero-server boundaries.
- The corrected runner result records successful exact load/inventory observation and passing resource ceilings, but rejects overall acceptance because graceful daemon shutdown failed and forced cleanup was required. Final safety cleanup passed and the retry is blocked.
- The shutdown-observation implementation record pins the mode-aware parser, PID ownership, bounded diagnostics, and status-confirmed shutdown fixtures while keeping runtime and standalone installation blocked.
- The runtime-lifecycle selection record chooses standalone `llmster`, rejects incompatible alternatives, and requires a pinned acquisition preflight before any installer or archive download.
- The llmster acquisition preflight pins one direct archive and its published SHA-512, preserves existing identities, and authorizes only an acquisition module plus fixtures—not a download or extraction.
- The llmster acquisition implementation result pins the dependency-free module and network-free fixtures for bounded streaming, identity checks, partial ownership, and atomic placement while keeping download, extraction, and execution blocked.
- The llmster download execution review records a clean destination but blocks authorization because observed storage is below the frozen pre-request floor; no request or cleanup occurred.
- The superseding llmster download decision records the approved ignored-dependency cleanup, a fresh passing storage baseline, and one exact request authorization while keeping extraction and runtime blocked.
- The storage-policy supersession retires that unused authorization and authorizes only the versioned policy module for one request. It preserves the 1-GiB ceiling and requires 8 GiB free afterward; extraction and runtime remain blocked.
- The acquisition result records the sole successful request, exact archive hashes, atomic placement, final reserve, preserved identities, and consumed authorization. It grants no inventory, extraction, installation, runtime, or benchmark permission.
- The first inventory result preserves its consumed backslash-path rejection. The corrected second inventory accepts 3,614 aggregate entries with zero member reads. The owned staging implementation and 19 generated-ZIP fixtures enforce source stability, storage, containment, no-overwrite, content evidence, and marker-scoped rollback; real extraction and signature tooling remain blocked.
- The real-staging decision pins one empty ignored parent, one unique child, one exact staging call, a fresh passing storage baseline, immediate live validation, and no retry. It permits no signature tooling, installation, execution, network use, benchmark input, or member-path retention.
- The real-staging result records one consumed accepted call, exact aggregate payload counts and digests, a matching ownership marker, final storage reserve, 91 digest-bound signature candidates, and a retained owned child. It grants no retry, signature-tool, installation, execution, or cleanup authority.
- The Authenticode review design binds that result and freezes fixture-only candidate discovery, documented status normalization, aggregate privacy, literal-path handling, and a deferred externally contained Windows adapter. It does not authorize retained-child enumeration or signature-tool use.
- The Authenticode review implementation source-binds the platform-independent policy and unchanged staging ownership invariant. Generated fixtures prove manifest/candidate admission, typed outcomes, mutation detection, and path-free aggregate evidence without adding a platform process surface.
- The Windows Authenticode adapter design freezes an identity-bound executable and fixed literal-path script request, bounded transport, strict response parsing, no retry, and an external zero-egress prerequisite. It authorizes generated-fixture implementation only.
- The Windows Authenticode adapter implementation source-binds the unchanged policy/transport, fixed script, exact argument construction, strict response parser, and fake-transport fixtures. It adds real transport capability but does not authorize or claim any real invocation.
- The Authenticode execution-preflight design freezes pure validation of injected exact-PowerShell and Windows Defender Firewall/WFP observations, a 91-call/300-second batch bound, atomic one-shot semantics, and aggregate-only output. It does not read or mutate real host state.
- The minimum POC protocol freezes three original tasks and an A/D0 order before model output. Its runner keeps hidden test code outside CyxCode workspaces, uses the same isolated verifier for both conditions, and permits D0 at most one evidence-guided revision.
- Proposal evidence records what a generator returned; only independent verification can support an effectiveness result.

## Adding Evidence Safely

1. Identify the exact candidate, revision, source, and applicable schema.
2. Write raw or temporary artifacts only inside the approved boundary; provider artifacts currently remain under `.replay_cache` unless a curated, redacted record is specified.
3. Append a new candidate event instead of changing an earlier event.
4. Create the smallest evidence record needed for the claim.
5. Run its dedicated validator and the full pilot-data suite.
6. Update the roadmap and a dated progress note with commands, identities, findings, limitations, and next gate.

Do not regenerate the non-replay evidence during ordinary validation. Regeneration depends on the pinned PyArrow environment and dataset inputs; the committed record is intentionally validated separately.

## What May Run Now

Local validators, unit tests, generated-ZIP staging fixtures, generated owned-tree Authenticode-policy fixtures with fake inspector outcomes, source-preserving deterministic smokes, read-only aggregate metadata audits, and rights/exposure analysis are permitted. Archive acquisition, both metadata attempts, and the sole real-staging call are consumed and cannot retry. The retained child must not be enumerated, read, removed, or modified at this gate. Windows adapter implementation, signature-tool discovery or invocation, installation, daemon/model operations, target execution, prompts, HTTP serving, CyxCode benchmark invocation, and benchmark input remain unauthorized. The completed cloud canary and help probe must not be repeated.
