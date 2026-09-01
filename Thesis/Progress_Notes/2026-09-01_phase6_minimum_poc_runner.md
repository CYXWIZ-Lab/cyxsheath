# Phase-6 Minimum POC Runner

## Outcome

The three-task A-versus-D0 runner is implemented by composing the existing CyxCode adapter, Stage-0 coordinators, artifact store, snapshot stager, and Docker backend. No Sheath core module or external dependency changed.

Condition A makes one model call and receives no verification feedback. D0 permits at most two calls; after a failed first attempt, only canonical Stage-0 reason codes enter the second prompt. Both conditions are scored by the same verifier against allowed changed paths, visible tests, and hidden tests.

Hidden test files stay outside each staged source tree. At verification time their source is passed directly as a `python -c` argument to the pinned, network-disabled Docker sandbox. Raw prompts, responses, patches, commands, and tool output remain under `.replay_cache`; the public record contains only task-level outcomes, counts, timing, failure codes, and digests.

Six focused fixtures cover task/order freezing, source mutation, prompt blinding, visible-before-hidden execution, scope rejection, and public-record privacy. Complete suites pass 585/585 pilot tests and 138/138 Sheath core tests on Python 3.12 and 3.14.

## Result

The frozen schedule was committed and executed once. One direct-condition proposal failed independent verification; the remaining five cells stopped before a proposal on provider HTTP 429 responses. See [the v1 result note](2026-09-01_phase6_minimum_poc_v1_result.md). The consumed schedule will not be rerun.
