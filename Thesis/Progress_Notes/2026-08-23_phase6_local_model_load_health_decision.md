# Phase-6 Local Model Load-Health Decision

## Decision

One load-only health check is authorized for the already verified Qwen2.5-Coder-7B-Instruct Q4_K_M weight. The operation may start the existing LM Studio daemon and load the exact model into memory, but it may not start the HTTP server, send an inference request, invoke CyxCode, or run a Docker container.

The load is fixed at 8,192 context tokens, CPU-only, one parallel prediction, a 600-second idle TTL, speculative decoding disabled, and identifier `cyxsheath-qwen25-coder-7b-q4km`. A different model, quantization, context, offload setting, or retry requires a new decision.

## Resource Gate

The host baseline has 51,387,342,848 bytes physical memory with 30,894,665,728 bytes available, a 4,096 MiB GTX 1050 Ti reporting 0 MiB used, no LM Studio process, and no listener on port 1234.

The check fails closed if preload available memory is below 20 GiB; observed available memory falls below 16 GiB; available-memory loss, activation-tree private memory, or activation-tree working set exceeds 12 GiB; GPU used-memory increases by more than 512 MiB; the exact loaded identity cannot be proven; an HTTP listener appears; any required measurement is missing; or cleanup fails.

## Cleanup and Evidence

After a 15-second observation window, the exact identifier must unload, loaded inventory must be empty, and only the process tree started for this activation may be stopped. Graceful termination precedes any forced cleanup. Port 1234, activation processes, and partial weight files must be absent afterward.

Curated evidence may retain only aggregates, bounded process basenames, identities, outcomes, and deviations. It may not retain raw CLI output, prompts, responses, credentials, task content, source, tests, or patches.

Validate the frozen decision with:

```powershell
python Thesis\pilot_data\validate_local_model_load_health_decision.py Thesis\pilot_data\review_evidence\phase6_local_model_load_health_decision.json
python -m unittest discover -s Thesis\pilot_data -p 'test_*.py' -v
```
