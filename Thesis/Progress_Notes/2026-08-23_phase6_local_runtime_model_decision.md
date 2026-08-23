# Phase-6 Local Runtime and Model Decision

## Decision

The first local synthetic feasibility path will reuse the installed LM Studio OpenAI-compatible server and its installed llama.cpp CUDA/AVX2 backend 2.28.2. The selected canary model is the first-party `Qwen/Qwen2.5-Coder-7B-Instruct-GGUF` Q4_K_M file at revision `13fb94b`, pinned by SHA-256. This decision installs nothing, downloads nothing, starts no service, and makes no model call.

The selection is intentionally limited to one generated public arithmetic fixture. It is not the trained Sheath critic and is not admitted for SWE-bench or other benchmark input.

## Why This Model

The [pinned Qwen model card](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF/raw/13fb94bfda8c8cf22497dc57b78f391a9acb426a/README.md) describes a 7.61B code-specialized model for generation, reasoning, fixing, and code-agent foundations, with a 32,768-token GGUF limit and Apache-2.0 license. The [exact Q4_K_M file](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF/blob/13fb94bfda8c8cf22497dc57b78f391a9acb426a/qwen2.5-coder-7b-instruct-q4_k_m.gguf) is 4.68 GB and publishes SHA-256 `509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c`.

[LM Studio's tool-use documentation](https://lmstudio.ai/docs/developer/openai-compat/tools) demonstrates Qwen2.5 through `/v1/chat/completions`, but the exact Coder GGUF through CyxCode remains unverified; that is what the synthetic canary must test. Qwen3-Coder 30B A3B is the sole bounded fallback because it explicitly targets agentic coding, but it is deferred: its LM Studio package needs at least 15 GB RAM and uses a larger community GGUF. It may be reconsidered only after a capability-specific 7B failure and a new decision.

## Resource and Security Boundary

The exact weight may later be downloaded once to ignored `repository_root/.local_models` on `D:` and symbolically imported, avoiding a second copy on constrained `C:`. The download ceiling is 6 GiB; total local-model storage is capped at 8 GiB with at least 32 GiB remaining on `D:`. SHA-256 verification is required before import.

Before loading, LM Studio must report an estimate at or below 12 GiB for 8,192 context tokens, CPU-only execution, one parallel prediction, and a 600-second idle TTL. The canary output is capped at 2,048 tokens and 900 seconds. The server must use a per-run API token, disable CORS and MCP, and stop after the run; the model must unload and the port and container must disappear. Binding beyond localhost is required for the Docker bridge and therefore cannot proceed without authentication.

## Contamination Boundary

The model card describes 5.5 trillion training tokens including source code but does not disclose exact membership. Because this model postdates the selected SWE-bench tasks, benchmark overlap remains uncertain. Synthetic authored input is unaffected, but benchmark admission stays blocked until a separate case-and-model contamination decision.

## Evidence and Next Action

The validator-backed record is [phase6_local_runtime_model_decision.json](../pilot_data/review_evidence/phase6_local_runtime_model_decision.json). Run:

```powershell
python Thesis\pilot_data\validate_local_runtime_model_decision.py Thesis\pilot_data\review_evidence\phase6_local_runtime_model_decision.json
python -m unittest discover -s Thesis\pilot_data -p 'test_*.py' -v
```

The direct validator passes, and the full pilot-data suite passes 60/60 tests on Python 3.12 and 3.14. The unchanged Sheath core passed 138/138 tests on both versions earlier in the same Phase-6 checkpoint.

The next action requires operator approval for the single 4.68 GB download. After download and SHA verification, an estimate-only preflight must pass before a separate record may authorize the synthetic canary.
