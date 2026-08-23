# Phase-6 Local Model Activation Preflight

## Outcome

The approved Qwen2.5-Coder-7B-Instruct Q4_K_M weight was downloaded once to ignored local storage at `D:\Dev\code agent\.local_models\qwen2.5-coder-7b-instruct-q4_k_m.gguf`. Its exact size is 4,683,073,536 bytes and its SHA-256 matches the pinned value `509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c`. The partial file was removed by atomic rename only after verification, and more than the required 32 GiB remained free on `D:`.

LM Studio imported the file into its existing `D:\Open_models` root through a symbolic link back to `.local_models/`; no second weight copy was created. Inventory identifies GGUF, Qwen2 architecture, Q4_K_M, and the expected byte count. It does not mark the model as trained for tool use, so the exact CyxCode tool path remains unverified.

## Estimate and Retained Anomaly

The estimate-only command used 8,192 context tokens, 0% GPU offload, one parallel prediction, and a 600-second TTL. LM Studio reported 4.36 GiB total, below the 12 GiB ceiling, but labeled the same 4.36 GiB as GPU memory while reporting 0% offload. Confidence was `LOW`. A clean host-context repeat produced the same estimate.

The model was never loaded and the HTTP server was never started. The existing daemon was used for inventory and its exact activation process tree was then stopped. A later status command tried to wake the service and timed out; process inspection confirmed no LM Studio or LMS process remained.

## Decision Boundary

The activation preflight passes, but the estimator anomaly requires an observed load-only health gate before any prompt. That next gate must cap context and parallelism, monitor actual RAM and VRAM, keep the HTTP server inactive until separately configured with authentication and CORS disabled, and unload cleanly. It is not yet authorized by this record.

The generated synthetic canary and all benchmark inputs remain blocked. No candidate, replay, source-snapshot, thesis, prompt, response, or model output was exposed.

## Evidence

The validator-backed record is [phase6_local_model_activation_preflight.json](../pilot_data/review_evidence/phase6_local_model_activation_preflight.json). Run:

```powershell
python Thesis\pilot_data\validate_local_model_activation_preflight.py Thesis\pilot_data\review_evidence\phase6_local_model_activation_preflight.json
python -m unittest discover -s Thesis\pilot_data -p 'test_*.py' -v
```
