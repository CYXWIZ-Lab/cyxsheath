# Environment and Operations

## Repository Locations

- `sheath/`: Python Stage-0 package, tests, and smoke scripts.
- `integrations/`: public integration boundary and optional local worktrees.
- `Thesis/pilot_data/`: Phase-6 records, validators, tests, and evidence.
- `usage/`: operator documentation and small examples.

Run commands from the repository root unless a section says otherwise. The optional `integrations/cyxcode/` worktree is deliberately excluded from the public checkpoint; see [`integrations/README.md`](../integrations/README.md).

## Prerequisites

- Python 3.11 or newer; the current suite is verified on 3.12 and 3.14.
- Docker Desktop for optional container smokes and adapter execution.
- Bun 1.3.11 only for the separate CyxCode integration checkout.
- PowerShell and `rg` for the documented Windows workflow.

Check the local tools:

```powershell
py -3.12 --version
py -3.14 --version
docker version  # optional
bun --version   # optional
```

Sheath has no third-party Python runtime dependencies. Set its source path in each new PowerShell session:

```powershell
$env:PYTHONPATH='sheath\src'
```

When working from `sheath/`, use `$env:PYTHONPATH='src'` instead.

## Safe Operating Rules

- Treat task snapshots and protected `.cyxcode`/`.opencode` metadata as immutable inputs.
- Use only digest-pinned images for evidence-producing Docker runs.
- Keep raw model responses in adapter-owned artifact locations; do not copy them into thesis prose.
- Do not send pilot candidates, SWE-bench rows, replay data, source snapshots, repository history, or `same_hello_query_plus.md` to a provider without a passed admission gate.
- Preserve the append-only candidate ledger. Add a new event; do not rewrite history.

## Output Locations

Smoke commands accept `--artifact-root`. Relative paths are created beneath the command's working directory. Use a distinct folder per run, for example:

```powershell
Set-Location sheath
$env:PYTHONPATH='src'
py -3.12 scripts\run_snapshot_smoke.py --image <digest-pinned-image> --artifact-root smoke-artifacts\snapshot-01
```

Research records belong under `Thesis/pilot_data/`; disposable caches and raw provider artifacts remain outside the curated evidence set, normally under `.replay_cache`.

## Troubleshooting

`ModuleNotFoundError: No module named 'sheath'` means `PYTHONPATH` is missing or relative to the wrong working directory. From the root use `sheath\src`; from `sheath/` use `src`.

If the Sheath suite creates `sheath\tmpXXXXXXXX` folders and then reports `WinError 5`, the calling process gave those temporary workspaces unusable ACLs. This can occur inside a managed filesystem sandbox; changing `TEMP` does not help because the tests deliberately stage snapshots beside the package. Run the same documented command from a normal or elevated PowerShell terminal. Do not interpret the permission errors as test assertion failures.

If Docker reports a daemon or named-pipe error, confirm Docker Desktop is running with `docker version`. A managed shell may lack pipe permission even when Docker is healthy; retry from the normal/elevated terminal that owns Docker access.

If a pinned image is absent, inspect with `docker image inspect <image-digest>`. Do not silently replace the digest: a different image creates different evidence.

If the separate CyxCode checkout is present and Bun cannot resolve its workspace packages, install from `integrations/cyxcode/`:

```powershell
bun install --frozen-lockfile --ignore-scripts --no-progress
```

Run typechecks and tests from a package directory, never from the CyxCode repository root.

The synthetic canary runner now rejects another attempt because its gate records `completed_single_attempt`. That is intentional, not a runtime failure. The benchmark proposal runner is also intentionally blocked before task access until provider and case-rights admission succeeds.
