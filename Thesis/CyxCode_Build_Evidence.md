# CyxCode Build Evidence

## Scope

This record establishes a reproducible CyxCode CLI artifact for Sheath Phase 5. It does not demonstrate provider-backed generation or thesis effectiveness. The separate upstream source was read only; all work occurred in the independent `integrations/cyxcode` checkout on `sheath-integration`.

## Pinned Inputs

| Input | Identity |
|---|---|
| CyxCode commit | `42676876b63ed5a18957e3318272eb0d875a95fc` |
| Package/version | `cyxcode` 2.3.8 |
| Bun builder | `oven/bun:1.3.11-alpine` digest `sha256:7ed9f74c326d1c260abe247ac423ccbf5ac92af62bb442d515d1f92f21e8ea9b` |
| Runtime base | `alpine` digest `sha256:28bd5fe8b56d1bd048e5babf5b10710ebe0bae67db86916198a6eec434943f8b` |
| Channel | `sheath` |
| Target | `linux-x64-baseline-musl` |
| Model catalog | JSON derived inside the builder from checked-in `models-snapshot.js`; SHA-256 `CD0F0E01726D815076405BA145DEE44B852408FD3A95C6D4926C5FC9929A36BE` |
| Git dependency | `ghostty-web` commit `20bd361` |

`ghostty-web` previously used a floating `main` manifest while the lock contained `20bd361`. Pinning the manifest and lock to that audited commit made `bun install --frozen-lockfile --ignore-scripts` pass. Both `packages/app` and `packages/opencode` typechecks pass.

## Reproduction

From `integrations/cyxcode`:

```powershell
docker build --progress=plain `
  --file packages/opencode/Dockerfile.sheath-build `
  --tag sheath-cyxcode:4267687 .

docker run --rm sheath-cyxcode:4267687 --version
docker run --rm sheath-cyxcode:4267687 --help
docker run --rm sheath-cyxcode:4267687 run --help
```

The adjacent `Dockerfile.sheath-build.dockerignore` scopes the context without changing normal Docker behavior. The builder fixes all identity inputs and invokes only one target. A Windows-native attempt reached compilation but Bun twice failed to extract `bun-linux-x64-musl-baseline-v1.3.11`; native Linux compilation therefore supplies the supported reproducible path.

## Results

Two clean image builds produced the same executable:

| Field | Recorded value |
|---|---|
| Executable SHA-256 | `E9E88C1635C5C357395FD2E46C211C20C5C1B99D11D81CE83EA67FCE580234B0` |
| Executable size | 137,739,694 bytes |
| First image ID | `sha256:8a797f1541bc715f362d0e42981c12d57aa599ee4b6ba38ea5e8332a4c06539a` |
| Replay image ID | `sha256:f0e92ed28ca87cae9e6ceec7217ea061bca150fe3e766c3169a83fd714073ede` |
| Runtime image size | 52,495,487 bytes |
| Version smoke | `2.3.8` |
| Help smokes | top-level and `run --help` exited 0 |

The image IDs differ because BuildKit emitted distinct provenance attestations. The identical executable digest is the content identity used by the adapter. The exported host artifact is ignored build output at `packages/opencode/dist/cyxcode-linux-x64-baseline-musl/bin/cyxcode`.

## Limitations and Next Gate

The Vite builds warn about one invalid-looking `:selected` pseudo-class, large chunks, and stale browser data; these warnings do not fail the CLI build. After the two completed builds, the same resolved base digests were written explicitly into the permanent Dockerfile. A cache-invalidated verification of that pin-only edit timed out during clean dependency installation after 304 seconds and produced no new tag; it neither reached compilation nor contradicts the completed artifact comparison.

The full Windows test suite remains non-clean. The baseline digest above remains the reproducible Phase-5 build identity; later pilot-specific behavior is recorded separately below.

## Phase-6 Pilot Derivative

The blinded pilot required two narrow corrections in the integration copy: HTTP 429 `FreeUsageLimitError` is terminal instead of silently retried, and `CYXCODE_DISABLE_STATE_CONTEXT=1` suppresses resume/memory/graph/wiki context plus state commits. Ordinary transient retry behavior and normal interactive state behavior remain enabled by default.

| Field | Recorded value |
|---|---|
| Pilot image ID | `sha256:f0a466626dcb1f123645ea9a40e2e7ef55c046dd7b76b8726d603605751b560c` |
| Runtime image size | 52,495,598 bytes |
| Pilot executable SHA-256 | `8C9D82AD1DC42961666470248E9A2241A45EEB1F0327FA6EC6AEFE61C6C1A31E` |
| Version smoke | `2.3.8` |
| Validation | CLI typecheck; 9 adapter tests; 19 retry tests; 18 pilot-data tests |

This derivative has one successful build, so its image/executable hashes are pins rather than a repeated-build reproducibility claim. The later rights/provider audit supersedes the quota-retry plan: Big Pickle is blocked from further benchmark submission. A named, versioned replacement must pass the retention, training-use, identity, and exposure gate before a synthetic non-benchmark canary.
