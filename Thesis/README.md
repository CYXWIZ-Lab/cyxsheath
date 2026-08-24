# Sheath Thesis Package

This folder turns the repository's exploratory notes into a falsifiable, implementation-ready thesis. The canonical manuscript is [Thesis_Manuscript.md](Thesis_Manuscript.md). Supporting documents separate engineering detail from the academic argument so the manuscript remains readable.

For practical setup, commands, component behavior, and operating boundaries, see the repository [usage guide](../usage/README.md).

## Documents

- [Research_and_Implementation_Roadmap.md](Research_and_Implementation_Roadmap.md): master status tracker with completed evidence, next-session pickup state, pending phases, dependencies, and exit gates.
- [Thesis_Manuscript.md](Thesis_Manuscript.md): complete thesis draft from research problem through implementation, evaluation, limitations, and conclusion.
- [Implementation_Blueprint.md](Implementation_Blueprint.md): minimal system architecture, interfaces, decision loop, CyxWiz mapping, and delivery stages.
- [Dataset_and_Model_Plan.md](Dataset_and_Model_Plan.md): data sources, labeling, quality control, model stages, and training gates.
- [Pilot_Data_Specification.md](Pilot_Data_Specification.md): frozen Phase-6 seed-case, admission, rights, rejection, lineage, contamination, annotation, agreement, split, and replay rules.
- [Experiment_Protocol.md](Experiment_Protocol.md): preregistration-ready comparison, metrics, statistical analysis, ablations, and reproducibility checklist.
- [Paper_Plan.md](Paper_Plan.md): a concise paper derived from the thesis after results exist.
- [Findings_and_Traceability.md](Findings_and_Traceability.md): synthesis of the existing files, claim status, design decisions, and provenance.
- [Context_Audit.md](Context_Audit.md): complete source registry and sequential range ledger for both large transcripts and all supporting files.
- [Smoke_Test_Evidence.md](Smoke_Test_Evidence.md): environment, command, digests, observations, and limitations for the first live container isolation check.
- [Snapshot_Smoke_Test_Evidence.md](Snapshot_Smoke_Test_Evidence.md): provenance and results for writable-copy staging, patch extraction/application, source isolation, and cleanup.
- [CyxCode_Integration_Pipeline.md](CyxCode_Integration_Pipeline.md): intended CyxCode adapter role, typed boundary, trust model, unknowns, and acceptance criteria.
- [CyxCode_Local_Workspace.md](CyxCode_Local_Workspace.md): pinned local clone, preserved worktree changes, exclusions, verified CLI facts, and integration decision gates.
- [CyxCode_Adapter_Contract.md](CyxCode_Adapter_Contract.md): executable invocation, isolation, NDJSON parsing, artifact mapping, failure semantics, and adapter acceptance tests.
- [CyxCode_Adapter_Fixture_Evidence.md](CyxCode_Adapter_Fixture_Evidence.md): fixture, subprocess, pinned-image, schema, digest, cleanup, and limitation evidence for the completed Phase-5 gate.
- [CyxCode_Build_Evidence.md](CyxCode_Build_Evidence.md): lock reconciliation, pinned Linux build inputs, executable and image identities, replay evidence, and smoke results.
- [Progress_Notes/2026-08-20_phase5_complete.md](Progress_Notes/2026-08-20_phase5_complete.md): concise handoff from the completed adapter phase to active pilot-data governance.
- [Progress_Notes/2026-08-20_phase6_specification.md](Progress_Notes/2026-08-20_phase6_specification.md): frozen data-governance milestone, schema identities, validation evidence, and calibration-batch handoff.
- [pilot_data/README.md](pilot_data/README.md): append-only candidate-ledger boundary, validation commands, current 20-case balance, limitations, and replay handoff.
- [Progress_Notes/2026-08-20_phase6_candidate_inventory.md](Progress_Notes/2026-08-20_phase6_candidate_inventory.md): pinned source revisions, license evidence, validation results, quarantine status, and next three-case replay slice.
- [Progress_Notes/2026-08-20_phase6_vertical_replay.md](Progress_Notes/2026-08-20_phase6_vertical_replay.md): pinned harness/environment/image identities, baseline/gold outcomes, Windows LF deviation, validation, and non-replay-gate handoff.
- [Progress_Notes/2026-08-20_phase6_non_replay_review.md](Progress_Notes/2026-08-20_phase6_non_replay_review.md): privacy-minimized artifact/lineage scan, bounded manual decisions, licensing boundary, append-only events, and remaining blockers.
- [Progress_Notes/2026-08-20_phase6_source_snapshots.md](Progress_Notes/2026-08-20_phase6_source_snapshots.md): network-disabled base-commit resolution, canonical source-archive identities, validation, and provider-backed proposal handoff.
- [Progress_Notes/2026-08-20_phase6_cyxcode_free_model_canary.md](Progress_Notes/2026-08-20_phase6_cyxcode_free_model_canary.md): credential-free model discovery, genuine canary failures, explicit Docker timeout cleanup, and bounded failure validation.
- [Progress_Notes/2026-08-21_phase6_rights_and_provider_exposure.md](Progress_Notes/2026-08-21_phase6_rights_and_provider_exposure.md): exact-card rights decisions, outbound-submission history, Big Pickle block, and the replacement-provider gate.
- [Progress_Notes/2026-08-23_phase6_provider_replacement_gate.md](Progress_Notes/2026-08-23_phase6_provider_replacement_gate.md): historical benchmark-grade two-model review; its synthetic credential conclusion is superseded by the correction below.
- [Progress_Notes/2026-08-23_phase6_free_synthetic_canary_correction.md](Progress_Notes/2026-08-23_phase6_free_synthetic_canary_correction.md): correction separating the free synthetic infrastructure canary from benchmark-provider admission.
- [Progress_Notes/2026-08-23_phase6_outbound_and_astropy_decision.md](Progress_Notes/2026-08-23_phase6_outbound_and_astropy_decision.md): supplemental Astropy rights decision, free-cloud benchmark block, and local-generator path selection.
- [Progress_Notes/2026-08-23_phase6_host_capacity_and_connectivity.md](Progress_Notes/2026-08-23_phase6_host_capacity_and_connectivity.md): privacy-minimized host resources, Docker-to-host TCP evidence, runtime readiness boundary, and model-decision handoff.
- [Progress_Notes/2026-08-23_phase6_local_runtime_model_decision.md](Progress_Notes/2026-08-23_phase6_local_runtime_model_decision.md): exact LM Studio/llama.cpp and Qwen2.5-Coder selection, resource/security ceilings, contamination boundary, and activation handoff.
- [Progress_Notes/2026-08-23_phase6_local_model_activation_preflight.md](Progress_Notes/2026-08-23_phase6_local_model_activation_preflight.md): verified weight download, symbolic import, estimate anomaly, cleanup, and load-health handoff.
- [Progress_Notes/2026-08-23_phase6_local_model_load_health_decision.md](Progress_Notes/2026-08-23_phase6_local_model_load_health_decision.md): one-shot CPU-only load contract, observed resource ceilings, zero-inference boundary, and cleanup gate.
- [Progress_Notes/2026-08-23_phase6_local_model_load_health_recovery.md](Progress_Notes/2026-08-23_phase6_local_model_load_health_recovery.md): fail-closed preload measurement attempt, read-only diagnostic, and one bounded recovery decision.
- [Progress_Notes/2026-08-23_phase6_local_model_daemon_recovery.md](Progress_Notes/2026-08-23_phase6_local_model_daemon_recovery.md): pre-load daemon lifecycle failure, exact manual cleanup, and final fail-safe root-capture decision.
- [Progress_Notes/2026-08-23_phase6_local_model_load_health_result.md](Progress_Notes/2026-08-23_phase6_local_model_load_health_result.md): observed load/unload and resource bounds, failed protocol acceptance, engine drift, CLI lock, and blocked retry.
- [Progress_Notes/2026-08-24_phase6_engine_cli_recovery_decision.md](Progress_Notes/2026-08-24_phase6_engine_cli_recovery_decision.md): repinned engine identity, temporary CLI-copy mechanism, unchanged safety contract, and one authorized load-health execution.
- [Tolook_Source_Review.md](Tolook_Source_Review.md): verified review of `tolook.md`, separating useful DeepSeek Harness/Cordis ideas from unsupported or premature additions.
- [References.md](References.md): working bibliography of primary research and project sources.
- [schemas/task_record.schema.json](schemas/task_record.schema.json): machine-readable task and constraint contract.
- [schemas/run_record.schema.json](schemas/run_record.schema.json): machine-readable proposals, execution, evidence, decisions, and artifacts.
- [schemas/patch_record.schema.json](schemas/patch_record.schema.json): canonical binary-safe add, modify, and delete artifact format.
- [schemas/dataset_manifest.schema.json](schemas/dataset_manifest.schema.json): machine-readable admission, rights, integrity, lineage, contamination, annotation-status, and split manifest.
- [schemas/annotation_record.schema.json](schemas/annotation_record.schema.json): machine-readable double-label and adjudication record.

## Current Status

The authoritative phase status and next work queue are maintained in [Research_and_Implementation_Roadmap.md](Research_and_Implementation_Roadmap.md). This is a thesis proposal with a partial Stage-0 implementation, not a completed experimental thesis. The dependency-free core in [../sheath/README.md](../sheath/README.md) implements immutable contracts, explicit run states, generator-neutral coordination, snapshot-bound verification, disposable workspaces, canonical patch replay, constrained tools, content-addressed artifacts, mandatory-check decisions, and schema-v1.7 run records. The concrete CyxCode path maps canonical model-visible inputs and trusted workspace deltas through the pinned Linux image into content-derived proposals while restoring protected metadata and retaining failure artifacts. Phase 5 is complete. Phase 6 has a frozen specification, validated schemas, 29 append-only events for 20 revision-pinned calibration candidates, and passed baseline/gold replays for one C, one C++, and one Python case. Those three also have content-addressed source archives and pass privacy, secret, safety, lineage, and upstream file-scope review. Pinned supplemental official SWE-bench evidence now permits internal research analysis of Astropy while its exact card remains `NOASSERTION`; redistribution and model-training rights remain unknown. A free MiMo-V2.5 canary used only a generated public arithmetic fixture and captured a one-file proposal through CyxCode's public-token path, proving that a paid Zen account is unnecessary for that infrastructure check. Current provider terms still block free MiMo from benchmark input. The exact Qwen2.5-Coder-7B-Instruct Q4_K_M weight is checksum-verified and symbolically imported. The final load-health attempt observed service-side load/unload at 8,192 context with zero offload layers; resource and cleanup bounds passed without inference or HTTP serving. Protocol acceptance failed because CLI self-extraction produced nonzero clients, post-load inventory/window proof was incomplete, and active llama.cpp drifted from approved 2.28.2 to unapproved 2.29.1. A validator-backed decision now adopts the installed 2.29.1 engine and authorizes one load-health execution using a hash-verified temporary copy of the unchanged client; inference and the synthetic canary remain blocked. Model-training-corpus overlap is undisclosed, so contamination and genuine benchmark proposals remain blocked. All 20 cases remain quarantined. No real seed corpus is claimed. The present Sheath implementation is the deterministic Stage-0 supervisor; learned D1 critic design and training are conditional Phases 9 and 10 after the Stage-0 pilot exposes a stable residual task. CyxWiz graphs, trained critics, external-provider validation, and benchmark outcomes remain unimplemented. These runs are infrastructure evidence only; result placeholders must be replaced only after the protocol is run.

## Core Claim

For repository-level software tasks, an independent, evidence-grounded supervisory layer can improve verified correctness and constraint adherence over direct generation and same-model self-critique, while a risk-adaptive policy can control the added cost.

“Wisdom” is the motivating metaphor. The measured construct is **engineering supervision**: epistemic restraint, constraint fidelity, evidence seeking, impact awareness, and calibrated intervention.

## Lean Build Order

1. Freeze the task/run schemas and label a small pilot set.
2. Implement the rule-and-tool supervisor without training a new model.
3. Run the controlled pilot and analyze failures.
4. Fine-tune a small critic only for ambiguous judgments that tools cannot settle.
5. Consider MoE or continual learning only if ablations justify their complexity.
