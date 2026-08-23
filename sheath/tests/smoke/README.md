# Container Smoke Fixture

This fixture is the first live check for the Docker sandbox adapter. It succeeds only when the repository bind mount is read-only and its outbound TCP probe is unavailable.

The run requires a locally available, digest-pinned Python image and an operational Docker Linux engine. The adapter uses `--pull never`, so running the smoke check never downloads an image implicitly. A successful run was recorded on 2026-08-14 with Docker 29.1.3 and the image documented in [../../../Thesis/Smoke_Test_Evidence.md](../../../Thesis/Smoke_Test_Evidence.md). The check is narrow: it does not by itself prove complete sandbox security or benchmark performance.

`writable_snapshot/` is the source for a second fixture. Its runner stages a verified copy, mounts only that copy as writable, confirms the container can change and create files, checks that the source digest did not change, and confirms cleanup removed the staged tree. Its recorded result is in [../../../Thesis/Snapshot_Smoke_Test_Evidence.md](../../../Thesis/Snapshot_Smoke_Test_Evidence.md).
