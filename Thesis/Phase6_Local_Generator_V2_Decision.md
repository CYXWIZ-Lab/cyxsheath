# Phase-6 Local Generator v2 Decision

## Decision

Decision `phase6-local-generator-v2-001` replaces the rate-limited cloud generator only for the next synthetic feasibility gate. It reuses the existing local assets:

- Qwen2.5-Coder-7B-Instruct Q4_K_M, 4,683,073,536 bytes, SHA-256 `509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c`;
- LM Studio's already installed CLI and pinned 2.29.1 llama.cpp engine inventory;
- CyxCode commit `42676876b63ed5a18957e3318272eb0d875a95fc` and its existing `@ai-sdk/openai-compatible` provider seam; and
- the existing Stage-0 coordinator, artifact store, snapshot boundary, and network-disabled Docker verifier.

No model, runtime, package, or integration source may be downloaded, installed, upgraded, or edited.

## Execution Boundary

The canary runner will invoke the clean, revision-pinned CyxCode source through the existing Bun executable on the host. LM Studio will bind only to `127.0.0.1:1234`; CyxCode will use `http://127.0.0.1:1234/v1`. This supersedes the earlier container-to-host `0.0.0.0` design for this canary, so an unauthenticated non-loopback listener is never created. CORS and LM Studio MCP access remain disabled.

CyxCode receives an isolated temporary state root and `CYXCODE_DISABLE_STATE_CONTEXT=1`. Its permission policy allows task-local read/list/search/edit operations only. Shell execution, web fetch/search, external-directory access, subagents, skills, and MCP are denied. The local generator workspace is disposable; independent visible and hidden checks still run in the pinned network-disabled Docker verifier.

The runner must bind the Git-clean CyxCode commit, Bun executable digest/version, bridge digest, LM Studio CLI/engine/model identities, task snapshot digest, configuration, and cleanup observations. Raw prompts, responses, and patches remain under `.replay_cache`.

## One-Canary Gate

After the runner and generated fixture pass deterministic tests and are committed, exactly one model call is authorized. The fixture must be original, public, non-sensitive, non-benchmark Python and permit one implementation file to change. Limits remain 8,192 context tokens, 2,048 output tokens, CPU-only loading, one parallel prediction, 600-second idle TTL, and 900 seconds total.

Success requires a CyxCode proposal, an allowed-path patch, passing visible and hidden checks, source preservation, model unload, stopped server/service, closed port 1234, removed temporary state, and no residual CyxCode container or process. A generation, verification, identity, resource, or cleanup failure consumes the attempt and stops the path without retry or model substitution.

## Interpretation and Next Gate

A passing canary proves only that the local model can traverse the exact CyxCode-to-Sheath seam. It does not establish model quality or the thesis hypothesis. Only after it passes may a separate v2 protocol freeze a paired A/D0 schedule. The failed cloud v1 remains immutable and is not pooled with local results.

The standalone llmster/Authenticode branch, another cloud provider, benchmark input, dataset admission, critic training, and CyxWiz model-building integration are deferred because none is needed to answer this immediate feasibility question.

Current LM Studio documentation states that `lms server start` defaults to loopback, supports an explicit `--bind` address, and leaves CORS off unless requested: <https://lmstudio.ai/docs/cli/serve/server-start>. Its server settings documentation treats authentication as necessary when broader clients are allowed: <https://lmstudio.ai/docs/developer/core/server/settings>.
