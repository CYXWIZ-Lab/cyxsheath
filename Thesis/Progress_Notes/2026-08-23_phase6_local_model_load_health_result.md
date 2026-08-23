# Phase-6 Local Model Load-Health Result

## Outcome

The final authorized attempt reached the exact Qwen2.5-Coder Q4_K_M weight. LM Studio's service log records 8,192 context tokens, zero GPU-offload layers, model-loaded state, and later service-side unload. No inference request, HTTP server, CyxCode process, or Docker container ran.

Observed resources stayed within the frozen bounds: available memory never fell below 19,214,118,912 bytes; the maximum available-memory drop was 8,023,838,720 bytes; peak activation-tree private memory was 1,932,574,720 bytes; peak working set was 6,329,212,928 bytes; and maximum GPU used-memory increase was 271 MiB. Port 1234 never listened. Final inventory was empty and graceful cleanup left no activation process, port listener, partial weight, or raw CLI output.

## Why the Gate Failed

This is not an accepted load-health result. The `lms` client returned nonzero because LM Studio tried five times to replace the running `lms.exe` and received an `EPERM` unlink error. The service still loaded and unloaded the model, but the frozen protocol requires a zero load-client exit, exact post-load inventory capture, and 15 observation samples; the monitor captured only 13 before the client failure path.

LM Studio's active GGUF backend preference also drifted from the approved llama.cpp CUDA/AVX2 2.28.2 package to 2.29.1. That change was not authorized. Therefore the observed activation cannot be treated as evidence for the pinned-engine gate or as a scientific model-health result.

## Decision Boundary

No automatic retry is authorized. The synthetic canary, authenticated HTTP server, benchmark input, and candidate proposals remain blocked. The next action is an explicit design decision covering engine identity and the CLI self-extraction lifecycle before any further activation.

Validate the result with:

```powershell
python Thesis\pilot_data\validate_local_model_load_health_result.py Thesis\pilot_data\review_evidence\phase6_local_model_load_health_result.json
python -m unittest discover -s Thesis\pilot_data -p 'test_*.py' -v
```
