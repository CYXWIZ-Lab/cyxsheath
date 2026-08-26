# Phase 6 Load-Health Runner Implementation

## Outcome

The exact Python activation runner is implemented and fixture-tested without invoking LM Studio. The implementation is pinned in `phase6_load_health_runner_implementation_result.json`. It is not an accepted load-health result and does not authorize a daemon, model load, inference request, HTTP server, CyxCode invocation, Docker container, synthetic prompt, or benchmark input.

## Lean Module Boundary

`monitored_process.py` owns one direct child from start through numeric exit, timeout, sampled output breach, monitor failure, termination, and raw-output deletion. `lm_studio_windows.py` owns privacy-minimized Windows process/resource observation, file and engine identity, PID-plus-creation-time ownership, and exact forced-stop mechanics. `run_local_model_load_health.py` owns only the frozen LM Studio command sequence, resource policy, graceful cleanup, acceptance, and local result.

This split was made after the first concrete runner reached 799 lines. The final runner remains 613 lines because it contains one cohesive protocol plus a large declarative result record; platform mechanics and generic process lifecycle no longer grow that file. No framework, thread, third-party dependency, or Sheath-core change was added.

## Safety Gate

The runner requires a future `phase6_load_health_runner_execution_decision.json` whose integration, runner, monitor, and Windows-adapter digests and exact settings match. That record does not exist. Without it, `main()` returns exit code 2 before host access or cache creation. An existing result also blocks another attempt.

## Validation and Limits

Eight monitored-child fixtures and six runner fixtures pass on Python 3.12 and 3.14. Ten implementation-result tests reject code drift, dependency or thread growth, fixture overclaims, runtime invocation, unrecorded authorization, inference, and live-adapter overclaims. The full pilot-data suite passes 170/170 on both versions.

The Windows adapter and LM Studio command sequence were not exercised live in this checkpoint. The 1 MiB output limit is sampled, not a zero-overshoot disk quota, and the single-thread timeout cannot interrupt a monitor callback already in progress. These limitations remain explicit for the one-shot execution decision.

## Next Gate

Make a separate validator-backed decision for the exact pinned runner or stop. Only after that decision passes may the required authorization record be created and the runner executed once. No automatic retry is permitted.
