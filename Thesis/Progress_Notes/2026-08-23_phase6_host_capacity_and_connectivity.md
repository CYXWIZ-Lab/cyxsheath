# Phase-6 Host Capacity and Connectivity Audit

## Scope

This audit closes the capacity portion of roadmap step 12 without installing a runtime, downloading a model, starting a benchmark run, or authorizing the local canary. It records only the minimum facts needed for the next runtime/model design decision.

## Findings

The host has a 6-core/12-thread Intel i7-8750H, 47.86 GiB of RAM, and an NVIDIA GTX 1050 Ti with 4 GiB of VRAM. Docker Desktop exposes 12 logical processors and 23.40 GiB of memory. Free storage was constrained at audit time: 9.48 GiB on `C:` and 41.87 GiB on `D:`. A later runtime decision must place model weights and caches on `D:` and set an explicit storage ceiling.

The hardware makes a small quantized CPU-oriented model canary plausible, but does not establish usable speed or quality. Four GiB of VRAM supports only a small model or partial offload; it does not justify a large GPU-resident coding-model claim.

LM Studio's `lms` CLI is installed at commit `71bd99c`, but its server was not running. A bounded model-inventory query timed out while waking the service, and no LM Studio process remained afterward. Ollama and the surveyed standalone llama runtimes were not installed. The runtime is therefore `not_ready`, and no local model is selected.

## Docker Probe

A temporary TCP listener and the already-pinned Python image tested `host.docker.internal` on Docker's bridge network. The alias resolved, the container connected, the host accepted the connection, and the named probe container was absent afterward. No model, benchmark, candidate, prompt, or response data was used. The first preflight command contained an invalid Docker output format and stopped before creating a container; the corrected identity check and probe passed.

## Evidence and Validation

The privacy-minimized record is [phase6_host_capacity_and_connectivity.json](../pilot_data/review_evidence/phase6_host_capacity_and_connectivity.json). It excludes machine identity, serials, usernames, credentials, and the resolved address. Validate it with:

```powershell
python Thesis\pilot_data\validate_host_capacity_and_connectivity.py Thesis\pilot_data\review_evidence\phase6_host_capacity_and_connectivity.json
python -m unittest discover -s Thesis\pilot_data -p 'test_*.py' -v
```

The direct validator passes. The full pilot-data suite passes 53/53 tests on Python 3.12 and 3.14, including seven capacity-record mutation tests. The unchanged Sheath core also passes 138/138 tests on both versions when run outside the managed Windows filesystem sandbox; the sandbox-only run encountered the already-documented temporary-directory ACL limitation.

## Decision Boundary

The audit does not authorize installation, model download, the synthetic local canary, or benchmark input. The next action is a separate design record that pins the runtime and model identity, weights digest, license, context and tool capability, resource and disk ceilings, and contamination treatment.
