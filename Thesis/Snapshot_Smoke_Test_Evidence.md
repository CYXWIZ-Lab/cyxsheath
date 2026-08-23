# Writable-Snapshot Smoke-Test Evidence

## Purpose

This record covers verified writable-copy staging and canonical patch replay. It asks whether Sheath can copy a stable source tree, allow a non-root container to mutate only the copy, extract a bounded patch, reproduce that result on an independent fresh copy, prove that the source stayed unchanged, and remove both staged directories afterward. It is infrastructure evidence, not a repository-task benchmark.

## Environment and Invocation

- Execution date: 2026-08-14
- Docker client/server: `29.1.3/29.1.3`
- Platform: Docker Desktop Linux containers on Windows
- Image: `python@sha256:dd29372629eeba2dd003fd9e9d35a5b8236c44727875a0364254b5127af88e65`
- Executable: `/usr/local/bin/python`
- Source: `sheath/tests/smoke/writable_snapshot/`
- Source-tree digest: `sha256:8186defe1e7d4c375e133e9abb7c369112e5e74240170466103f8983dd7b7efb`

```powershell
$env:PYTHONPATH = "src"
python scripts/run_snapshot_smoke.py --image "python@sha256:dd29372629eeba2dd003fd9e9d35a5b8236c44727875a0364254b5127af88e65"
```

The stager hashed the source before and after copying and required the initial copy to have the same digest. Docker mounted only the copy as writable. A second locked-down container mounted the source and Sheath runtime read-only, revalidated their digests, and emitted a canonical patch through bounded stdout. The trusted host applier verified the registered patch artifact, applied it to another untouched snapshot, and required the declared result-tree digest. Networking, the container root, capabilities, privileges, and resources retained the original adapter restrictions.

## Result and Artifacts

The recorded mutation run started at `2026-08-14T16:39:13.016684Z` and ended at `2026-08-14T16:39:14.315622Z`. It exited with code 0 without timeout or truncation. Mutation and extraction evidence passed. Inside the first copy, the container changed `seed.txt` from `original` to `changed` and created `generated.txt`. The extracted patch contains exactly those two sorted changes and their base64-encoded bytes. Application to the independent fresh copy reproduced both bytes and result digest. After execution:

- the source-tree digest was unchanged;
- source `seed.txt` still contained `original`;
- the source contained no `generated.txt`;
- both staged directories were removed; and
- `docker ps -a --filter name=sheath-` returned no containers.

Evidence identifiers:

- Mutation sandbox: `sha256:ae7482662e5ffe4cb482b2566712af85eda20e17e04b1b74daff8df0d1c6a577`
- Extraction sandbox: `sha256:ae1229ee5bd355013119fa4e4d6cbfe44d996b8b6ec59a249268b861082e8c18`
- Observation: `observation:action-snapshot-smoke`
- Patch observation: `observation:action-patch-extract`
- Result-tree digest: `sha256:d6695cc78fb7e3ee1ebef4cd0fb16860b93bd54e6caad85438440c0d536f3f6a`
- Manifest digest: `sha256:a381494a0531d87d40e1b97883c5d6f959c606470d2a69039482cf3906b8bc01`
- Patch digest: `sha256:60ec634071434fead340257c3786ae26a08715e74370af4943987b46934d085e`
- Stdout digest: `sha256:9fdb8a82df147269cd9635f2e388850a536ff930812eb4679dc905a57185e896`
- Stderr was empty: `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

## Interpretation Limits

This proves staging, source isolation, binary-safe extraction, exact application, and cleanup for one small fixture and platform. Patch schema v1.0 preserves paths, entry kinds, sizes, content digests, symlink targets, and file bytes, but deliberately excludes host permission modes and ACLs because Windows and Linux bind mounts expose them differently. Extraction and application enforce the declared 4 MiB patch cap. Application requires a registered artifact, canonical forward-slash paths, the expected source digest, an untouched snapshot, matching before-states, valid directory parents, and the declared result digest; any failure discards the target. Rename detection, concurrent mutation resistance, permission replay, and large-repository scaling are not yet implemented.

The final fixture was run twice with independent random staging paths. Both runs produced the same source, result, patch, mutation-sandbox, extraction-sandbox, stdout, and stderr digests; both applications reconstructed the same two paths and result digest, while timestamps produced different manifest digests. The preceding replication manifest has digest `sha256:f9e03451edebfbea02ac8ba0e003bb9bb6b96178ca824b970054cc1959a96bc5`.
