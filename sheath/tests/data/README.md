# Stage-0 Control-Plane Fixtures

`stage0_scenarios.json` contains exactly 20 synthetic tasks for validating contract, evidence, and decision behavior. Each scenario applies small task overrides, ordered ledger operations, and optional findings to the shared task record, then declares the exact expected verdict and reason codes.

These fixtures are harness tests, not repository-level benchmarks or empirical thesis results. They execute no generated code and make no claim about model quality. Their purpose is to expose control-plane regressions before a command runner or generator is connected.
