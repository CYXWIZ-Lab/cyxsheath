# Phase 5 Completion Snapshot - 2026-08-20

## Completed

- Added the canonical Python `SubprocessCyxCodeExecutor`, which sends the complete `GenerationRequest` through JSON stdin without a shell and verifies the returned prompt, model, title, variant, redacted configuration, and executable digest.
- Added a narrow TypeScript JSON bridge and Docker proxy. The proxy rehashes `/usr/local/bin/cyxcode`, mounts only the disposable snapshot and isolated state, forwards an explicit environment allowlist, and removes adapter-owned Docker metadata before Windows cleanup.
- Drove immutable CyxCode image `sha256:8a797f1541bc715f362d0e42981c12d57aa599ee4b6ba38ea5e8332a4c06539a` through the full Python coordinator, deterministic local provider, explicit session export, trusted patch extractor, verifier, and schema-v1.7 record export.
- Captured an `accept` record with digest `sha256:6696088aea38a8b7c3bdab05129c8375aa776c473483a4b76eba80e131184d0f`. The source was unchanged, the canonical prompt reached the provider, and `fixture-secret` was absent from the response artifact.

## Verification

- Python 3.12: 138/138 tests pass.
- Python 3.14: 138/138 tests pass.
- CyxCode adapter: 9/9 tests pass with 69 assertions.
- CyxCode package typecheck passes.
- The pinned accepted record validates against Draft 2020-12 run-record schema v1.7 with date-time formats.

## Next Pickup

Phase 6 is active. Freeze corpus inclusion, licensing, task eligibility, annotation, rejection, split, contamination, and agreement rules in `Dataset_and_Model_Plan.md` before collecting examples. Then resolve only pilot-critical fields in `Experiment_Protocol.md` and prepare the D0 baseline.

Do not begin critic training yet. D1 remains conditional on a stable measured residual error set that deterministic rules and tools cannot resolve. External-provider behavior, cancellation/process-tree guarantees, token/cost capture, and benchmark effectiveness are still unevidenced.
