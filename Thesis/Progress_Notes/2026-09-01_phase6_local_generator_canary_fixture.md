# Phase-6 Local Generator Canary Fixture

## Outcome

The pre-call local-canary task and CyxCode configuration are implemented without starting LM Studio or invoking a model. The original Python task asks the model to repair one feature-flag normalizer. Its defective baseline fails both visible and hidden checks, while `hidden_tests.py` remains outside the staged `source/` directory.

The task manifest binds the v2 decision, model identifier, request, allowed path, and all source/hidden-test digests. The CyxCode configuration uses only `http://127.0.0.1:1234/v1`, disables sharing, snapshots, plugins, external skills, and MCP, and applies a deny-by-default permission policy. Only task-local read, list, search, and edit capabilities are allowed; shell, web, external-directory, skill, and subagent access remain denied.

Five focused tests pass on Python 3.12 and 3.14. They verify task identities, intended baseline failure, hidden-source prompt exclusion, exact loopback/permission policy, and source-mutation rejection. The complete Phase-6 suite passes 597/597 on both versions.

## Next Step

Implement the one-shot host lifecycle and CyxCode runner with injected fake transports first. Commit and revalidate it before the sole live local-model call. Do not manually start LM Studio, run this task through another model, or expose the server beyond loopback.
