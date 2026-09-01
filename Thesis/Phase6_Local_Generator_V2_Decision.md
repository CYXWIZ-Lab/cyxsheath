# Phase-6 Local Generator v2 Decision

## Decision

Decision `phase6-local-generator-v2-001` replaces the rate-limited cloud generator only for the next synthetic feasibility gate. It reuses the existing local assets:

- Qwen2.5-Coder-7B-Instruct Q4_K_M, 4,683,073,536 bytes, SHA-256 `509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c`;
- LM Studio's already installed CLI and pinned 2.29.1 llama.cpp engine inventory;
- CyxCode commit `42676876b63ed5a18957e3318272eb0d875a95fc` and its existing `@ai-sdk/openai-compatible` provider seam; and
- the existing Stage-0 coordinator, artifact store, snapshot boundary, and network-disabled Docker verifier.

No model, runtime, package, or integration source may be downloaded, installed, upgraded, or edited.

## Execution Boundary

Pre-implementation inspection found that the separate CyxCode development checkout contains the expected experimental bridge plus other uncommitted work. It is read-only but not a reproducible clean host executable. Therefore this decision corrects the unexecuted host-source plan: the canary will retain the already pinned CyxCode Docker image and executable used by v1.

LM Studio remains bound only to `127.0.0.1:1234`. A dependency-free, runner-owned HTTP proxy may bind `0.0.0.0:1235` only for the canary so the CyxCode container can reach it as `http://host.docker.internal:1235/v1`. The proxy requires a freshly generated 256-bit bearer token, retains no token or bodies, strips authorization before loopback forwarding, accepts only `/v1/models` and `/v1/chat/completions`, caps request/response bytes and time, emits no CORS headers, and stops before final cleanup checks. Thus LM Studio itself is never exposed beyond loopback, and the transient non-loopback seam is authenticated and narrowly allowlisted.

CyxCode receives an isolated temporary state root and `CYXCODE_DISABLE_STATE_CONTEXT=1`. Its permission policy allows task-local read/list/search/edit operations only. Shell execution, web fetch/search, external-directory access, subagents, skills, and MCP are denied. The generator workspace is disposable; independent visible and hidden checks still run in the pinned network-disabled Docker verifier.

The runner must bind the CyxCode image/executable, proxy source, LM Studio CLI/engine/model identities, task snapshot digest, configuration, and cleanup observations. Raw prompts, responses, patches, and proxy traffic remain under `.replay_cache` or memory and never enter curated evidence.

## One-Canary Gate

After the runner and generated fixture pass deterministic tests and are committed, exactly one CyxCode generation attempt is authorized. That attempt may contain the bounded internal model turns required for task-local read/edit tool use; it is not permission for a second proposal attempt. The fixture must be original, public, non-sensitive, non-benchmark Python and permit one implementation file to change. Limits remain 8,192 context tokens, 2,048 output tokens, CPU-only loading, one parallel prediction, 600-second idle TTL, and 900 seconds total.

Success requires a CyxCode proposal, an allowed-path patch, passing visible and hidden checks, source preservation, model unload, stopped server/service, closed port 1234, removed temporary state, and no residual CyxCode container or process. A generation, verification, identity, resource, or cleanup failure consumes the attempt and stops the path without retry or model substitution.

## Interpretation and Next Gate

A passing canary proves only that the local model can traverse the exact CyxCode-to-Sheath seam. It does not establish model quality or the thesis hypothesis. Only after it passes may a separate v2 protocol freeze a paired A/D0 schedule. The failed cloud v1 remains immutable and is not pooled with local results.

The standalone llmster/Authenticode branch, another cloud provider, benchmark input, dataset admission, critic training, and CyxWiz model-building integration are deferred because none is needed to answer this immediate feasibility question.

Current LM Studio documentation states that `lms server start` defaults to loopback, supports an explicit `--bind` address, and leaves CORS off unless requested: <https://lmstudio.ai/docs/cli/serve/server-start>. Its server settings documentation treats authentication as necessary when broader clients are allowed: <https://lmstudio.ai/docs/developer/core/server/settings>.
