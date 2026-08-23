# CyxCode Adapter Contract

## Decision and Scope

Implement CyxCode as an external Sheath `GeneratorAdapter`. CyxCode may generate and edit only a disposable `WorkspaceSnapshot`; it does not normalize requirements, select mandatory checks, accept artifacts, or issue verdicts. The separate upstream checkout remains read-only.

The audited implementation is commit `42676876b63ed5a18957e3318272eb0d875a95fc`, package `cyxcode` 2.3.8, with Bun 1.3.11. Use the commit as the authoritative code identity. The CLI exposes no seed option, so `RunMetadata.seed` must remain `null` unless a provider-specific, verified mechanism is later added.

## Invocation

The production adapter must launch an absolute, pinned executable without a shell. Source-mode commands are audit-only. The intended call is equivalent to:

```text
cyxcode run --dir <snapshot> --format json \
  --model <provider/model> [--variant <variant>] --title <run-id>
```

Send the canonical prompt through closed-after-write standard input, not command-line arguments. Set the process working directory to the snapshot and impose wall-time, output-byte, and child-process cleanup limits. Do not invoke a model until the provider, model, and authentication source are explicit.

## Per-Run Isolation

Create fresh directories and set `XDG_DATA_HOME`, `XDG_CACHE_HOME`, `XDG_CONFIG_HOME`, and `XDG_STATE_HOME`. Also set `CYXCODE_TEST_HOME` and `CYXWIZ_TEST_HOME` to the isolated home. Disable unrelated variability with:

- `CYXCODE_DISABLE_AUTOUPDATE=1`;
- `CYXCODE_DISABLE_MODELS_FETCH=1`;
- `CYXCODE_DISABLE_LSP_DOWNLOAD=1`;
- `CYXCODE_DISABLE_DEFAULT_PLUGINS=1`;
- `CYXCODE_DISABLE_EXTERNAL_SKILLS=1`; and
- `CYXCODE_DISABLE_PROJECT_CONFIG=1`;
- `CYXCODE_DISABLE_STATE_CONTEXT=1`.

The state-context switch suppresses resume, memory, graph, wiki, state commits, and drift reinforcement for blinded runs. Supply a minimal explicit `CYXCODE_CONFIG_CONTENT`. Inject only the selected provider credential, redact it from artifacts, and never copy a personal CyxCode home. Container/network policy remains the authoritative containment boundary; CyxCode's internal permissions are not a substitute.

## Input and Output Rules

Build the prompt deterministically from the confirmed `TaskContract`, attempt number, source digest, and ordered feedback. Store its exact bytes and digest before launch.

`run --format json` writes NDJSON events. Accept only JSON objects with one consistent `sessionID`; bound line and aggregate sizes. Recognized types are `step_start`, `step_finish`, `tool_use`, `text`, optional `reasoning`, and `error`. Preserve unknown well-formed events but do not infer success from them. Malformed JSON, mixed session IDs, truncation, an `error` event, timeout, cancellation, or nonzero exit is a failed generation.

Exit code zero is necessary but insufficient: the audited `run.ts` accumulates `session.error` data yet does not convert it to a final nonzero exit. After a nominal run, execute `cyxcode export <sessionID>` with the same working directory and isolated state. Require valid JSON, matching session identity, complete messages/parts, and no terminal assistant error. Never call `export` without an ID because that path is interactive.

## Proposal and Artifact Mapping

On success, store a canonical response envelope containing the executable/commit identity, sanitized argv, environment digest, model and variant, timestamps, exit status, raw NDJSON, stderr, parsed events, and exported session. Do not discard tool failures or reasoning metadata. Derive no claims initially; `GeneratorProposal.claims` may remain empty.

Extract the workspace delta through a supplied trusted patch-extractor boundary, preferably `DockerPatchExtractor`; do not call private `_build_patch_record` from the adapter. Return a content-derived proposal ID bound to:

- the adapter `generator_id`;
- request revision and attempt;
- the response artifact; and
- the canonical patch artifact.

Sheath then revalidates response integrity, source immutability, changed paths, and the result-tree digest before verification.

## Failure and Cleanup Semantics

Terminate the process tree on timeout or cancellation, wait for exit, close all streams, and remove isolated state after artifacts are secured. Rehash the immutable source and proposal snapshot at the boundary. A process failure is recorded as an experimental infrastructure/generator outcome, not converted into an empty proposal. `GeneratorError` may carry verified response artifacts, and both coordinators now include those artifacts in schema-v1.7 failed records before raising `CoordinatorError`.

## Acceptance Gate

Before provider-backed use, automated tests must cover NDJSON chunking, malformed and oversized output, mixed sessions, explicit error events with exit zero, export mismatch, timeout, cancellation, process-tree cleanup, credential redaction, source-write attempts, and patch-extractor failure. A deterministic fake-provider fixture must repeat with identical prompt, response-envelope, patch, and result digests. A separate real-model smoke must produce a schema-valid proposal-to-verdict record without requiring identical model output.

Current evidence: app and CLI package typechecks pass; 115 focused CLI/session tests pass outside sandbox; no-model version/help/export checks pass with isolated state. Nine TypeScript adapter tests pass, including the real CyxCode source entrypoint against a deterministic local provider and capture of a model-visible request without state-context blocks. Nineteen retry tests verify that exhausted free usage terminates while ordinary transient failures remain retryable. Five focused Python tests cover canonical envelope validation, subprocess prompt preservation, trusted patch/proposal mapping, deterministic `.cyxcode`/`.opencode` restoration, repeatability, accepted-record export, and failure-response retention. Both 138-test Sheath suites pass. The lock drift is resolved by pinning `ghostty-web`; two baseline Linux builds produced the same executable SHA-256 and passed container version/help smokes. The concrete Python executor drove the pinned image through a schema-valid accepted proposal-to-verdict smoke with prompt preservation, secret redaction, source preservation, and disposable-state cleanup. See [CyxCode_Build_Evidence.md](CyxCode_Build_Evidence.md) and [CyxCode_Adapter_Fixture_Evidence.md](CyxCode_Adapter_Fixture_Evidence.md). Cancellation/process-tree evidence, token/cost capture, and a successful external-provider proposal remain open. The full Windows suite is diagnostic rather than a release gate.
