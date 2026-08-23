# CyxCode Local Integration Workspace

## Acquisition Record

The original local CyxCode worktree was treated as an immutable source reference for this thesis project. Development occurred only in an independent `integrations/cyxcode/` checkout, whose public boundary is documented in [../integrations/README.md](../integrations/README.md).

| Field | Recorded value |
|---|---|
| Acquisition date | 2026-08-14 |
| Source branch | `sync/mcp-oauth-upstream-2026-06-28` |
| Local development branch | `sheath-integration` |
| Source and clone commit | `42676876b63ed5a18957e3318272eb0d875a95fc` |
| Package identity | `cyxcode` |
| Package version at commit | `2.3.8` |
| License | MIT |
| Public project remote | `https://github.com/code3hr/cyxcode.git` |
| OpenCode upstream remote | `https://github.com/anomalyco/opencode.git` |
| Local provenance remote | Fetch-only local source; push URL disabled |

The README mentions release `3.0.1`, while the checked-out package declares `2.3.8`. The commit hash—not either version string—is therefore the authoritative identity until the release relationship is audited.

## Copy Policy

The clone was created with full Git history and `--no-hardlinks`, so its object database is independent of the original worktree. Three tracked modifications and coherent untracked development material were overlaid byte-for-byte:

- the memory index and its matching new memory entry;
- upstream audit and repair-planning notes;
- tool notes;
- source-only demonstration projects; and
- the local lean-software-guardrails skill.

Machine state was deliberately excluded: `node_modules`, Turbo caches, root and package `.tmp` trees, truth-test homes, databases, logs, compiled `.obj`/`.exe` files, and the malformed `$null` artifact.

## Reproducibility and Test Audit

The lock drift was isolated to `ghostty-web`: the app manifest tracked GitHub `main`, while the audited lock resolved commit `20bd361`. The integration copy now pins that commit in both `packages/app/package.json` and `bun.lock`. With Bun 1.3.11, `bun install --frozen-lockfile --ignore-scripts` passes. This is an integration-only change; the immutable source remains unchanged.

From `packages/opencode` on 2026-08-14:

- `bun typecheck` passed in both `packages/opencode` and `packages/app`;
- a focused CLI/session set passed 115/115 outside the process-spawn sandbox;
- the unrestricted full suite reported 2,174 pass, 9 skip, 18 named failures, and 528 runner errors across 2,201 tests; and
- the sandboxed full run was invalidated by `EPERM` child-process restrictions.

The passing focused command was:

```powershell
bun test test/cli test/session/message-v2.test.ts `
  test/session/retry.test.ts test/session/prompt.test.ts --timeout 30000
```

The unrestricted failures include Windows path/shell behavior, session/storage cases, five 30-second provider-stream timeouts, and CyxWatch/tool cases. The full suite also removed the preserved untracked memory note and changed its index. Both were restored byte-for-byte from the immutable source; a final audit found zero mismatches across all 34 preserved files. The note SHA-256 is `A9B922717009745320F715CC3D0F2C2510FFB2EA6F73386925CFF297A5319E0A`. Until test isolation is repaired, run focused tests or snapshot the preserved overlay before the full suite.

## Pinned Build Identity

The Windows host consistently failed only at Bun's download/extraction of `bun-linux-x64-musl-baseline-v1.3.11`. The experimental checkout's `packages/opencode/Dockerfile.sheath-build` avoids that host-specific cross-compiler path by building under pinned `oven/bun:1.3.11-alpine`. It derives model JSON from the checked-in snapshot and fixes version `2.3.8`, channel `sheath`, and target `linux-x64-baseline-musl`. That bridge source is not part of the current public checkpoint.

Two clean image builds produced a bit-identical 137,739,694-byte executable with SHA-256 `E9E88C1635C5C357395FD2E46C211C20C5C1B99D11D81CE83EA67FCE580234B0`. The image smoke returned `2.3.8`; `--help` and `run --help` also exited successfully without a model. Docker image IDs differ because each build has a distinct provenance attestation, so the executable digest is the stable artifact identity. Exact commands, inputs, images, and limitations are recorded in [CyxCode_Build_Evidence.md](CyxCode_Build_Evidence.md).

## Verified CLI Boundary

The checked-out source exposes:

```text
cyxcode run [message...] --dir <snapshot> --model <provider/model>
  --variant <value> --format json

cyxcode export [sessionID]
```

`run --format json` emits newline-delimited events containing a timestamp and session ID. Current event types include `step_start`, `step_finish`, `tool_use`, `text`, optional `reasoning`, and `error`. `export` emits session metadata, messages, and parts as JSON.

The adapter must parse `error` events and validate the final session; it must not equate exit code zero with successful generation. It must also record the exact commit, package/runtime identity, model, variant, prompt digest, environment, event stream, timeout outcome, response artifact, and resulting patch.

No-model smoke checks confirmed `--version`, top-level help, `run --help`, and `export --help`. With XDG data, cache, config, and state redirected, all observed writes remained in the audit tree; help initialization populated only the isolated cache. The temporary tree was removed afterward.

## Integration Decision

Start with an **external `CyxCodeGenerator` adapter in Sheath**. It should invoke the pinned CLI only inside a disposable proposal snapshot and return the existing typed `GeneratorProposal`. Sheath continues to own contracts, tool evidence, patch validation, retries, decisions, and run-record export.

This boundary is smallest because it proves the research pipeline without changing CyxCode control flow. The alternatives remain open:

| Option | Use only when |
|---|---|
| External adapter | First end-to-end experiment and generator-neutral research conditions. |
| CyxCode plugin | Verified hooks can expose the required events or user interface without weakening Sheath's independent decision boundary. |
| Direct CyxCode integration | A proven adapter needs native pre/post-flight UX or control-flow enforcement that plugins cannot provide. |
| Upstream merge | The integration is isolated, tested, generally useful, and acceptable to CyxCode maintainers. |

CyxCode's own documentation states that plugins cannot short-circuit its model loop or intercept every shell path. That limits plugins for native enforcement, but does not prevent the external Sheath adapter from supervising the final proposal.

## Remaining Pre-Flight Audit

Before implementing the adapter:

1. determine provider authentication without copying personal state into experiments;
2. freeze model, variant, prompt, permissions, network policy, budgets, and retries;
3. test JSON framing, error propagation, cancellation, timeout, and child-process cleanup;
4. verify that CyxCode edits only the supplied snapshot;
5. add run-record export for generator/adapter failures; and
6. repeat a complete proposal-to-verdict fixture and compare every deterministic content-derived identity.

The executable requirements are frozen in [CyxCode_Adapter_Contract.md](CyxCode_Adapter_Contract.md).
