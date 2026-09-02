# Phase-6 Local Generator Canary Fixture

## Outcome

The pre-call local-canary task and CyxCode configuration are implemented without starting LM Studio or invoking a model. The original Python task asks the model to repair one feature-flag normalizer. Its defective baseline fails both visible and hidden checks, while `hidden_tests.py` remains outside the staged `source/` directory.

The task manifest binds the v2 decision, model identifier, request, allowed path, and all source/hidden-test digests. A pre-implementation audit found that the read-only CyxCode development checkout is not Git-clean, so the decision now retains the pinned Docker executable and selects an authenticated transient proxy to loopback LM Studio. The CyxCode configuration targets only that proxy, disables sharing, snapshots, plugins, external skills, and MCP, and applies a deny-by-default permission policy. Only task-local read, list, search, and edit capabilities are allowed; shell, web, external-directory, skill, and subagent access remain denied.

Six task/configuration tests, seven proxy tests, and six lifecycle tests pass on Python 3.12 and 3.14. They verify task identities, intended baseline failure, hidden-source prompt exclusion, authenticated proxy/permission policy, token shape, source-mutation rejection, authentication before forwarding, the two-path allowlist, authorization stripping, request/response limits, aggregate-only metrics, exact production endpoints, reverse-order cleanup, partial-start handling, and fail-closed outcomes. The complete Phase-6 suite passes 611/611 on both versions.

The proxy uses only the Python standard library. It does not log request or response bodies and is not a general network gateway. Its sole purpose is to let the pinned CyxCode container reach loopback-only LM Studio during the bounded canary.

## Next Step

Implement the concrete LM Studio/CyxCode adapter behind the tested one-shot lifecycle. Commit and revalidate it before the sole live local-model call. Do not manually start LM Studio, run this task through another model, or start the proxy independently.
