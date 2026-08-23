# Phase 6 Vertical Replay Snapshot - 2026-08-20

## Completed in this slice

- Pinned the official SWE-bench harness at commit `7a21e05772954cc81471ae19d56f436cecf43c54`, package 5.0.2, under Python 3.12.8.
- Froze the installed environment in `pilot_data/replay_requirements.lock.txt` and verified it exactly matches `pip freeze`.
- Downloaded only the two revision-pinned parquet shards, verified their SHA-256 digests, and materialized the three selected rows into one restricted local file.
- Resolved and pulled exact Linux/amd64 image manifests for Redis, fmt, and Astropy.
- Ran marker-baseline and gold-patch pairs for C, C++, and Python.
- Appended replay review events 21–23 without modifying the original registrations.

## Replay outcomes

| Instance | Baseline F2P failed | Baseline P2P passed | Gold F2P passed | Gold P2P passed | Result |
|---|---:|---:|---:|---:|---|
| `redis__redis-10068` | 1 | 7 | 1 | 7 | Replay passed |
| `fmtlib__fmt-1683` | 1 | 42 | 1 | 42 | Replay passed |
| `astropy__astropy-12907` | 2 | 13 | 2 | 13 | Replay passed |

All six accepted runs applied their patch, completed without a harness-reported infrastructure failure, and removed their containers. Baselines remained unresolved; gold patches resolved.

## Deviation

The first Redis baseline/gold attempt is excluded. On Windows, the unmodified harness wrote CRLF `eval.sh` content and corrupted Linux shell commands and test-patch application. The narrow, recorded `swebench_windows_lf.patch` forces UTF-8 LF for generated `patch.diff` and `eval.sh`; corrected runs use new IDs and preserve the failed logs.

## Validation evidence

- Candidate ledger: `sha256:ef6705d38c58809f4996c2c650dec62463850c67572c6649838646718a4ab1ba`
- Replay evidence: `sha256:704021c2ba6eda889cc72ce9187867cd6a2f1d9425243135d6a79eaa06e1b0eb`
- Replay validator: `sha256:8b546bd6af2f63ebd536b998806453ccfe90064985bf758203f66bf7d08fbb2c`
- Requirements lock: `sha256:7ae8978fe6fb452b652a9c7ba92f57756d2b63bc058efe5c96d5b2449c6ddc16`
- Both validators pass; nine unit/negative tests pass.

## Limits and next pickup

Zero cases are admitted. The three replayed cases remain quarantined under `artifact.incomplete`, `license.unclear`, and `privacy.review_required`; their rights, privacy/secrets, safety, lineage/near-duplicate, contamination, and final artifact reviews are pending. Resolve those gates and append decisions before replaying the remaining 17. No annotation, training, critic, or benchmark-performance claim starts here.
