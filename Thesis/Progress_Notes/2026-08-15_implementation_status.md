# Implementation Progress Snapshot - 2026-08-15

## What is done

- Stage-0 Sheath core is in place: contracts, states, generator boundary, single + bounded coordinators, tool-backed verification, snapshots/stager, canonical patch extraction, run-record schema-v1.7 export.
- Runtime hardening for coordination failures is implemented: coordinator now emits schema-valid `failed` run records on generator/stager/runtime errors, with stable `failure_reason_codes` and protocol deviation findings.
- CyxCode workspace integration prep is documented and pinned: independent checkout at `42676876b63ed5a18957e3318272eb0d875a95fc`, pinned Linux build digest, and lockfile drift resolved for `ghostty-web`.
- Research package has moved through roadmap updates to the concrete adapter phase and lock/reproducibility evidence is recorded.
- The concrete execution layer now launches `run` and explicit-ID `export` in isolated state with stdin-only prompts, absolute commands, timeout/output limits, strict session mapping, and cleanup.
- Eight CyxCode adapter tests pass with 58 assertions, including a real CyxCode CLI run against a deterministic local provider; the package typecheck passes.
- The Python `CyxCodeGenerator` validates canonical envelopes, restores protected project metadata, invokes the trusted patch extractor, derives content-bound proposal IDs, and preserves response artifacts in failed run records.
- Both Sheath suites now pass 137/137 on Python 3.12 and 3.14. Success records export proposal/response/patch provenance and failure records retain the generator response.

## What is currently active

- Concrete CyxCode adapter slice (Phase 5).
- Fixture and live execution/export coverage are complete for the TypeScript subprocess boundary, and Python proposal/failure mapping is complete.
- Remaining work is concentrated on the concrete Python executor bridge to the pinned binary and one complete pinned-binary proposal-to-verdict smoke.

## What is still pending

### Data and protocol

1. Freeze corpus inclusion/eligibility rules and contamination controls in `Dataset_and_Model_Plan.md`.
2. Resolve all pilot-critical placeholders in `Experiment_Protocol.md`.
3. Completed: add deterministic fake-provider and real-CLI success/failure fixture evidence.
4. Run baseline smoke, validate proposal-record determinism, and begin D0 data collection once provenance gates are frozen.

### Model/learning (not started yet)

- No residual critic/model training artifacts exist yet.
- No D1 admission decision has been made; data-driven evidence and residual error set are required first.
- No CyxWiz capability audit or model pipelines are executed yet.

## Next `continue` checkpoints

1. Completed: add minimal fake-provider fixture files for NDJSON/events and exported session payloads.
2. Completed: add/verify adapter parsing and mapping assertions (success + error event cases).
3. Completed: run the live fixture end-to-end in disposable isolation and capture content identities in `CyxCode_Adapter_Fixture_Evidence.md`.
4. Completed: map the execution artifact and workspace delta into Sheath success/failure records with deterministic metadata restoration.
5. Drive the pinned binary through the Python executor boundary, then resume dataset/protocol freeze work.
