# Phase-6 Local Model Load-Health Recovery

## Fail-Closed Attempt

The first authorized load-health attempt ended during its preload baseline, before the LM Studio daemon or load command started. The monitor could not obtain its first NVIDIA used-memory sample and therefore stopped rather than loading without a required measurement.

No model was loaded, no observation sample was accepted, and no inference, HTTP server, CyxCode process, or Docker container ran. Post-attempt checks found no LM Studio/LMS process, port-1234 listener, partial weight, or retained raw CLI file. This is a measurement-harness failure, not evidence about LM Studio or Qwen model health.

## Diagnostic and Recovery Decision

Two read-only repetitions of the same `nvidia-smi` query then exited successfully and each reported 0 MiB used. That does not establish why the first sample failed, so the anomaly remains recorded as transient rather than explained.

One recovery attempt is authorized because the first attempt ended before daemon or model activation and cleanup passed. Only GPU sampling changes: the executable is resolved once, and each required sample may make at most three attempts separated by one second. Every model identity, CPU-only setting, context, memory/GPU ceiling, timeout, zero-inference boundary, and cleanup requirement from the original decision remains unchanged. Missing GPU data still fails closed.

Validate the recovery decision with:

```powershell
python Thesis\pilot_data\validate_local_model_load_health_recovery_decision.py Thesis\pilot_data\review_evidence\phase6_local_model_load_health_recovery_decision.json
python -m unittest discover -s Thesis\pilot_data -p 'test_*.py' -v
```
