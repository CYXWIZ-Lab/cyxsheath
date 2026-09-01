# Phase-6 Minimum Scientific POC Protocol

## Purpose

This development pilot tests the thesis-critical mechanism: whether deterministic Stage-0 Sheath review and one evidence-guided revision can improve the same coding model's verified result. It is not a confirmatory experiment and cannot establish general effectiveness.

## Frozen Comparison

- **Tasks:** three original, public, non-benchmark Python repair tasks under `pilot_data/poc_tasks/`.
- **Generator:** CyxCode 2.3.8 with `opencode/mimo-v2.5-free` and the already pinned CyxCode image/executable.
- **A — Direct:** one model call followed by visible and hidden scoring. Verification is not returned to the generator.
- **D0 — Stage-0 Sheath:** at most two model calls. After attempt one, the independent verifier returns only canonical failed-check reason codes; hidden test source and raw output remain unavailable.
- **Order:** POC-001 A→D0, POC-002 D0→A, POC-003 A→D0.
- **Model-call timeout:** 180 seconds per call. No automatic provider retry.
- **Verification timeout:** 30 seconds per check in a pinned, network-disabled Docker sandbox.

The different call ceiling is deliberate: bounded evidence-guided revision is the mechanism being tested. Model calls and wall time must therefore be reported with success.

## Tasks and Blinding

Each task contains a staged `source/` directory with the defective implementation and visible tests. Its `hidden_tests.py` remains outside that directory and is passed to the isolated verifier only after a proposal. The task request states the required behavior; the hidden checks test declared edge cases rather than undisclosed requirements.

The tasks were authored for this pilot and are not SWE-bench inputs. They cannot enter later confirmatory evaluation or critic training/test splits without an explicit role change.

## Outcomes

The primary descriptive outcome is paired final `verified_success`, requiring:

1. only the allowed implementation file changed;
2. visible tests passed;
3. hidden tests passed; and
4. the final Stage-0 decision accepted.

Also record attempts, wall time, changed-path count, final verdict, infrastructure failures, and whether D0 recovered after a failed first attempt. Three pairs are too few for significance testing; report the task-level table and paired difference only.

## Failure and Evidence Rules

Provider, bridge, Docker, or runner failures are infrastructure outcomes, not task failures. Do not silently rerun or select a better response. Raw prompts, responses, patches, and tool output stay under `.replay_cache`; the public result contains digests, bounded failure codes, aggregate metrics, and task-level pass/fail values only.

The protocol and task snapshot must be committed before the first model call. Any later change creates a new pilot version.
