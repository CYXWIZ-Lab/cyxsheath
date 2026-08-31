# Environment and Operations

## Repository Locations

- `sheath/`: Python Stage-0 package, tests, and smoke scripts.
- `integrations/`: public integration boundary and optional local worktrees.
- `Thesis/pilot_data/`: Phase-6 records, validators, tests, and evidence.
- `usage/`: operator documentation and small examples.

Run commands from the repository root unless a section says otherwise. The optional `integrations/cyxcode/` worktree is deliberately excluded from the public checkpoint; see [`integrations/README.md`](../integrations/README.md).

## Prerequisites

- Python 3.11 or newer; the current suite is verified on 3.12 and 3.14.
- Docker Desktop for optional container smokes and adapter execution.
- Bun 1.3.11 only for the separate CyxCode integration checkout.
- PowerShell and `rg` for the documented Windows workflow.

Check the local tools:

```powershell
py -3.12 --version
py -3.14 --version
docker version  # optional
bun --version   # optional
```

Sheath has no third-party Python runtime dependencies. Set its source path in each new PowerShell session:

```powershell
$env:PYTHONPATH='sheath\src'
```

When working from `sheath/`, use `$env:PYTHONPATH='src'` instead.

## Safe Operating Rules

- Treat task snapshots and protected `.cyxcode`/`.opencode` metadata as immutable inputs.
- Use only digest-pinned images for evidence-producing Docker runs.
- Keep raw model responses in adapter-owned artifact locations; do not copy them into thesis prose.
- Do not send pilot candidates, SWE-bench rows, replay data, source snapshots, repository history, or `same_hello_query_plus.md` to a provider without a passed admission gate.
- Preserve the append-only candidate ledger. Add a new event; do not rewrite history.

## Output Locations

Smoke commands accept `--artifact-root`. Relative paths are created beneath the command's working directory. Use a distinct folder per run, for example:

```powershell
Set-Location sheath
$env:PYTHONPATH='src'
py -3.12 scripts\run_snapshot_smoke.py --image <digest-pinned-image> --artifact-root smoke-artifacts\snapshot-01
```

Research records belong under `Thesis/pilot_data/`; disposable caches and raw provider artifacts remain outside the curated evidence set, normally under `.replay_cache`.

## Phase-6 Capacity Check

The completed privacy-minimized audit is a curated record, not a command to redetect or change the host. Validate it from the repository root:

```powershell
python Thesis\pilot_data\validate_host_capacity_and_connectivity.py Thesis\pilot_data\review_evidence\phase6_host_capacity_and_connectivity.json
```

The recorded Docker-to-host TCP probe passed. LM Studio CLI was installed but not ready, Ollama was absent, and the audit itself authorized no runtime installation or model download. The subsequent decision selected the installed llama.cpp backend and one exact Qwen2.5-Coder weight. The separately approved activation preflight has now downloaded and verified that weight without running inference.

Validate that decision without downloading anything:

```powershell
python Thesis\pilot_data\validate_local_runtime_model_decision.py Thesis\pilot_data\review_evidence\phase6_local_runtime_model_decision.json
```

The verified weight is stored at `D:\Dev\code agent\.local_models\qwen2.5-coder-7b-instruct-q4_k_m.gguf`. It is 4,683,073,536 bytes, Git-ignored, and pinned to SHA-256 `509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c`. LM Studio's existing `D:\Open_models` tree contains only a symbolic link to that file, so there is no second 4.68 GB copy. Do not redownload, rename, replace, move, or commit the weight.

Validate the curated activation record without hashing or loading the local weight:

```powershell
python Thesis\pilot_data\validate_local_model_activation_preflight.py Thesis\pilot_data\review_evidence\phase6_local_model_activation_preflight.json
```

The CPU-only estimate reported 4.36 GiB total, below the 12 GiB ceiling, but its confidence was `LOW` and it labeled 4.36 GiB as GPU memory despite 0% offload. No model or HTTP server remained active. A one-attempt load-only health decision now freezes the exact command, observed RAM/VRAM ceilings, timeout, and cleanup requirements:

```powershell
python Thesis\pilot_data\validate_local_model_load_health_decision.py Thesis\pilot_data\review_evidence\phase6_local_model_load_health_decision.json
```

Do not run `lms` manually, load the model, or send a prompt. The temporary-client `--help` probe and the later Python load-health execution have both consumed their one-shot authorizations. Engine inventory now uses normalized relative POSIX paths ordered by raw UTF-8 bytes. The authorized CPU-only run loaded the exact model, captured the exact 8,192-token inventory, completed all 15 samples, passed RAM/GPU ceilings, and unloaded successfully without inference or an HTTP listener. Overall acceptance still failed because `daemon down` returned 1 and bounded forced cleanup was required. The corrected fixture path now requires standalone `isDaemon: true` status and vendor PID ownership before load; shutdown requires empty inventory, one down call, and a final `not-running` status. Desktop mode fails before load. This implementation has not run against LM Studio, and the consumed failure is unchanged. No retry, standalone installation, prompt, HTTP server, CyxCode invocation, or benchmark input is authorized.

Validate the shutdown decision without touching LM Studio:

```powershell
python Thesis\pilot_data\validate_shutdown_contract_review_decision.py Thesis\pilot_data\review_evidence\phase6_shutdown_contract_review_decision.json
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
```

The first monitored attempt failed closed before daemon start because its initial NVIDIA sample was unavailable. Cleanup passed and two read-only repetitions then succeeded. The validator-backed recovery record authorizes one corrected attempt with at most three one-second GPU reads per required sample; no model or resource setting changed:

```powershell
python Thesis\pilot_data\validate_local_model_load_health_recovery_decision.py Thesis\pilot_data\review_evidence\phase6_local_model_load_health_recovery_decision.json
```

The earlier final recovery reached service-side load and unload, but the gate failed on CLI extraction, observation/inventory proof, and engine identity. The subsequent temporary-client execution recorded no bounded-window extraction-lock event but stopped before model load because no numeric daemon-client exit was observable. Final safety cleanup passed, while forced cleanup and missing exit evidence failed the protocol. Validate the result chain with:

```powershell
python Thesis\pilot_data\validate_local_model_load_health_result.py Thesis\pilot_data\review_evidence\phase6_local_model_load_health_result.json
python Thesis\pilot_data\validate_local_engine_cli_recovery_decision.py Thesis\pilot_data\review_evidence\phase6_local_engine_cli_recovery_decision.json
python Thesis\pilot_data\validate_local_engine_cli_recovery_result.py Thesis\pilot_data\review_evidence\phase6_local_engine_cli_recovery_result.json
```

Do not retry, change the engine preference, update the CLI, or start the HTTP server without a new explicit design decision.

The synchronous transport decision may be validated without invoking LM Studio:

```powershell
python Thesis\pilot_data\validate_cli_exit_transport_decision.py Thesis\pilot_data\review_evidence\phase6_cli_exit_transport_decision.json
python Thesis\pilot_data\validate_cli_exit_transport_result.py Thesis\pilot_data\review_evidence\phase6_cli_exit_transport_result.json
python Thesis\pilot_data\validate_load_health_transport_integration_decision.py Thesis\pilot_data\review_evidence\phase6_load_health_transport_integration_decision.json
python Thesis\pilot_data\validate_load_health_runner_implementation_result.py Thesis\pilot_data\review_evidence\phase6_load_health_runner_implementation_result.json
python Thesis\pilot_data\validate_load_health_runner_execution_review.py Thesis\pilot_data\review_evidence\phase6_load_health_runner_execution_review.json
python Thesis\pilot_data\validate_load_health_runner_one_shot_correction_result.py Thesis\pilot_data\review_evidence\phase6_load_health_runner_one_shot_correction_result.json
python Thesis\pilot_data\validate_load_health_runner_fresh_execution_decision.py Thesis\pilot_data\review_evidence\phase6_load_health_runner_fresh_execution_decision.json
python Thesis\pilot_data\validate_load_health_runner_execution_decision.py Thesis\pilot_data\review_evidence\phase6_load_health_runner_execution_decision.json
python Thesis\pilot_data\validate_load_health_runner_execution_result.py Thesis\pilot_data\review_evidence\phase6_load_health_runner_execution_result.json
python -m unittest Thesis.pilot_data.test_cli_transport Thesis.pilot_data.test_validate_cli_exit_transport_decision -v
python -m unittest Thesis.pilot_data.test_monitored_process Thesis.pilot_data.test_run_local_model_load_health -v
```

These validation commands do not repeat either consumed execution or invoke LM Studio. Running `run_local_model_load_health.py` again exits with code 2 before host access because the retained claim already exists. There is no authorized runtime command. Standalone `llmster` release `0.0.21-2` and its direct archive checksum are pinned. Acquisition and both metadata decisions are consumed. The corrected inventory accepted 3,614 entries. The owned staging implementation passes generated fixtures only; real member reads, extraction, installation, runtime, and retry remain unauthorized.

That one call has now succeeded and is consumed. The ignored archive is at `.replay_cache\llmster_acquisition\0.0.21-2-win32-x64.full.zip`; it is 867,394,409 bytes with SHA-256 `e6556e8edd7240c43da28aa555bac12197ba3e2199247bba773c81c6ae94170c` and the pinned published SHA-512. Do not rerun acquisition. The first metadata inventory failed closed; after fixture correction, one fresh inventory accepted 3,614 entries without member reads. The marker-owned staging module and generated fixtures are implemented, but no real-staging decision exists. Do not call it with the real archive, install files, inspect signatures, or execute binaries.

## Troubleshooting

`ModuleNotFoundError: No module named 'sheath'` means `PYTHONPATH` is missing or relative to the wrong working directory. From the root use `sheath\src`; from `sheath/` use `src`.

If the Sheath suite creates `sheath\tmpXXXXXXXX` folders and then reports `WinError 5`, the calling process gave those temporary workspaces unusable ACLs. This can occur inside a managed filesystem sandbox; changing `TEMP` does not help because the tests deliberately stage snapshots beside the package. Run the same documented command from a normal or elevated PowerShell terminal. Do not interpret the permission errors as test assertion failures.

If Docker reports a daemon or named-pipe error, confirm Docker Desktop is running with `docker version`. A managed shell may lack pipe permission even when Docker is healthy; retry from the normal/elevated terminal that owns Docker access.

If a pinned image is absent, inspect with `docker image inspect <image-digest>`. Do not silently replace the digest: a different image creates different evidence.

If the separate CyxCode checkout is present and Bun cannot resolve its workspace packages, install from `integrations/cyxcode/`:

```powershell
bun install --frozen-lockfile --ignore-scripts --no-progress
```

Run typechecks and tests from a package directory, never from the CyxCode repository root.

The synthetic canary runner now rejects another attempt because its gate records `completed_single_attempt`. That is intentional, not a runtime failure. The benchmark proposal runner is also intentionally blocked before task access until provider and case-rights admission succeeds.
