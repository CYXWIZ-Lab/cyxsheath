# Using the CyxCode Adapter

## Role in the Thesis

CyxCode is the coding-agent generator, while Sheath owns the task contract, isolation, trusted patch extraction, verification, evidence, and verdict. The Python adapter is public under `sheath/src/sheath/cyxcode.py`. The experimental full CyxCode checkout under `integrations/cyxcode/` is an independent, ignored worktree and is not vendored in this repository.

The pinned integration baseline is commit `42676876b63ed5a18957e3318272eb0d875a95fc` on branch `sheath-integration`, package version 2.3.8, with Bun 1.3.11.

## Data Flow and Trust Boundary

1. Sheath builds a canonical, model-visible prompt from the frozen task contract.
2. `SubprocessCyxCodeExecutor` calls the Bun bridge `sheath-bridge.ts`.
3. `runner.ts` runs `cyxcode run` as an isolated JSON stream, explicitly exports the matching session, parses it, redacts secrets, hashes artifacts, and removes adapter state.
4. `sheath-docker.ts` enforces the pinned image/executable, mount policy, state isolation, timeout, and container cleanup.
5. Sheath restores protected `.cyxcode` and `.opencode` roots, then a trusted Docker extractor derives the canonical patch from the workspace delta.
6. The proposal enters normal Sheath verification. Model text never counts as verification evidence by itself.

## Public Adapter Check

The dependency-free Python tests exercise envelope validation, prompt preservation, proposal mapping, artifact handling, and protected-state restoration without requiring the CyxCode checkout:

```powershell
Set-Location sheath
$env:PYTHONPATH='src'
py -3.12 -m unittest tests.test_cyxcode_adapter -v
```

## Maintainer-Only Integration Check

The following commands require the separately maintained experimental checkout. They are retained for provenance and are not a clean-clone public reproduction path yet.

Install workspace dependencies once from the integration root:

```powershell
Set-Location integrations\cyxcode
bun install --frozen-lockfile --ignore-scripts --no-progress
```

Then use package-local checks:

```powershell
Set-Location packages\opencode
bun typecheck
bun test test/cyxcode-adapter.test.ts test/cyxcode-adapter-live.test.ts
```

The recorded focused result is 9 passing adapter tests with 69 assertions. Run the application typecheck separately if its code changes:

```powershell
Set-Location ..\app
bun typecheck
```

Do not run a full test command from the CyxCode repository root. General CLI features are documented by the separate [CyxCode project](https://github.com/code3hr/cyxcode), but that guide is not evidence that every feature has been validated for Sheath.

## Deterministic Adapter Smoke: Maintainer Only

From `sheath/`:

```powershell
$env:PYTHONPATH='src'
py -3.12 scripts\run_cyxcode_smoke.py --artifact-root smoke-artifacts\cyxcode-local
```

This command requires the unpublished experimental bridge files in `integrations/cyxcode/`. A clean public clone should run the public adapter test above instead. The live bridge becomes a public reproduction path only after its CyxCode revision is reviewed and released.

The default Phase-5 runtime identity is image `sha256:8a797f1541bc715f362d0e42981c12d57aa599ee4b6ba38ea5e8332a4c06539a`, executable `sha256:e9e88c1635c5c357395fd2e46c211c20c5c1b99d11d81ce83ea67fce580234b0`, and patch image `python@sha256:dd29372629eeba2dd003fd9e9d35a5b8236c44727875a0364254b5127af88e65`.

## Phase-6 Pilot Derivative

The later pilot image is `sha256:f0a466626dcb1f123645ea9a40e2e7ef55c046dd7b76b8726d603605751b560c` with executable `sha256:8c9d82ad1dc42961666470248e9a2241a45eeb1f0327fa6ec6aefe61c6c1a31e`. It makes free-quota failures terminal and supports `CYXCODE_DISABLE_STATE_CONTEXT=1` for blinded pilot isolation. It has one successful build, so these are pins, not a repeated-build reproducibility claim.

## Free-Model Canary: Completed, Do Not Rerun

One bounded canary used `opencode/mimo-v2.5-free` through CyxCode's public-token route. Its only input was a generated, public, non-sensitive arithmetic fixture; no paid credential or benchmark data was used. It captured a one-file proposal and preserved the source.

The gate now records `completed_single_attempt`, so `run_cyxcode_synthetic_canary.py` correctly rejects a second attempt. Consult the curated [gate](../Thesis/pilot_data/review_evidence/phase6_synthetic_canary_gate.json) and [result](../Thesis/pilot_data/proposal_evidence/phase6_synthetic_free_canary.json), not transient TUI output.

The genuine benchmark runner remains blocked before task access. Do not alter that guard or submit quarantined candidates until the benchmark provider-exposure and case-rights gates pass. Before operating on the Python pilot, read [What Astropy Means Here](Pilot_Data_and_Evidence.md#what-astropy-means-here).

## Selected Local Path: Weight Verified, Inference Still Blocked

Design decision `phase6-generator-boundary-001` selects CyxCode's existing custom OpenAI-compatible provider seam as the primary benchmark-generation path. The integration already documents an Ollama-style endpoint and the Docker proxy exposes `host.docker.internal`; no new core abstraction is approved.

The capacity audit found 47.86 GiB host RAM, 4 GiB VRAM, constrained storage, and a working Docker-to-host TCP path. The decision reuses LM Studio CLI 1.3.3 and its installed llama.cpp CUDA/AVX2 backend 2.28.2; no Ollama installation or new CyxCode abstraction is needed.

The selected synthetic model is first-party `Qwen/Qwen2.5-Coder-7B-Instruct-GGUF` at revision `13fb94b`, file `qwen2.5-coder-7b-instruct-q4_k_m.gguf`, SHA-256 `509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c`, under Apache-2.0. Its GGUF context limit is 32,768 tokens, but the first canary is capped at 8,192 context and 2,048 output tokens with GPU off, one prediction, and a 12 GiB estimated-memory ceiling. The exact Coder model's tool behavior through CyxCode remains unverified.

The exact file is now stored at `D:\Dev\code agent\.local_models\qwen2.5-coder-7b-instruct-q4_k_m.gguf`, with the pinned size and SHA-256 verified before import. It is Git-ignored and symbolically linked into LM Studio's existing `D:\Open_models` root, so no duplicate weight copy was created.

The estimate-only preflight passed the 12-GiB memory ceiling. The exact CPU-only runner later loaded the model, captured the expected 8,192-token inventory, completed 15 samples, passed RAM/GPU ceilings, and unloaded without inference or HTTP serving. Graceful desktop-service shutdown failed and required forced cleanup, so standalone `llmster` was selected. Its exact archive was acquired once. After a preserved path-policy rejection and fixture correction, the fresh metadata inventory accepted 3,614 entries with no member reads. CyxCode, HTTP serving, extraction staging, installation, and the synthetic canary remain blocked. Any later server run still requires a new execution decision, per-run authentication, non-loopback binding, and CORS/MCP disabled.

Superseding update (2026-08-30): the unused prior request authorization is retired. Only the versioned storage-policy module may make one request, with a 1-GiB ceiling, 9-GiB pre-request floor, 8-GiB final reserve, and no retry. All runtime and benchmark boundaries remain unchanged.

Acquisition result (2026-08-30): the sole request succeeded, the 867,394,409-byte archive matches its published SHA-512, the CLI/engine/model identities are unchanged, and the authorization is consumed. CyxCode and LM Studio were not invoked. Archive inventory and every later runtime step remain separately gated.

Qwen3-Coder 30B A3B is deferred unless the 7B canary fails for a demonstrated model-capability reason and a new decision approves the added cost. Both models remain blocked from benchmark input until contamination is separately resolved.
