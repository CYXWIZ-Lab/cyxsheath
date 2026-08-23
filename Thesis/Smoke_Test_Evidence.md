# Container Smoke-Test Evidence

## Purpose

This record documents the current typed-workspace live evidence run of the Sheath Docker adapter. The run tests two narrow claims: the repository bind mount rejects writes, and the fixture's outbound TCP probe cannot connect. It is infrastructure evidence, not a software-task benchmark or complete sandbox-security assessment.

## Environment and Invocation

- Execution date: 2026-08-14
- Host: Windows with Docker Desktop Linux containers
- Docker client/server: `29.1.3/29.1.3`
- Platform: `linux/amd64`
- Image: `python@sha256:dd29372629eeba2dd003fd9e9d35a5b8236c44727875a0364254b5127af88e65`
- Executable: `/usr/local/bin/python`
- Limits: 1 CPU, 256 MiB memory, 64 PIDs, 16 MiB `/tmp`
- User: `65534:65534`
- Action timeout: 30 seconds

```powershell
$env:PYTHONPATH = "src"
python scripts/run_container_smoke.py --image "python@sha256:dd29372629eeba2dd003fd9e9d35a5b8236c44727875a0364254b5127af88e65"
```

The adapter also used `--pull never`, `--network none`, a read-only root filesystem and repository mount, dropped all capabilities, enabled `no-new-privileges`, and removed the disposable container.

## Result and Artifacts

The current run started at `2026-08-14T16:38:17.050751Z` and ended at `2026-08-14T16:38:18.547472Z`. It exited with code 0 without timeout or truncation. Authorization, runner evidence, and both fixture assertions passed. A post-run `docker ps -a --filter name=sheath-` check returned no containers. The sandbox environment digest binds the adapter implementation sources as well as Docker, image, and resource configuration.

- Sandbox digest: `sha256:13d52119a7b106f4a3b9821b079e394969a5c1ef53f6cbcc7e25804f67f624d6`
- Observation: `observation:action-container-smoke`
- Manifest artifact digest: `sha256:8923a03647c5e5798d41f222efcded45e3ebed91c1918dcc5574577f105a4cb6`
- Stdout artifact digest: `sha256:2f7255ddca40b737b0282d34d0b2ba205bdafc6cf48bd586de5e7e21338a4bfe`
- Stderr was empty: `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

The stdout payload was `{"network_blocked":true,"workspace_write_blocked":true}`.

## Interpretation Limits

This single run supports only the exercised configuration and probes. It does not test every network path, kernel boundary, resource-limit failure mode, malicious image, repository workload, or host platform. Those require separate adversarial and repeated integration tests.

A preceding current-adapter attempt used the original 10-second action allowance and failed closed with empty output before the container completed. Its retained failure-manifest digest is `sha256:500bbf56a4a5aaabaf6dc31dc78e552f5483414e967bb863294e8f56e345a2d9`. The smoke allowance was raised to 30 seconds to cover Docker Desktop startup variance; the fixture's own network probe remains bounded at 0.25 seconds.
