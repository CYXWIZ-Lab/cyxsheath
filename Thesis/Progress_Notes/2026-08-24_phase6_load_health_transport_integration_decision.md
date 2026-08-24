# Phase 6 Load-Health Transport Integration Decision

## Outcome

The numeric CLI transport and activation monitor now have a frozen integration design. This checkpoint authorizes only implementation of `run_local_model_load_health.py` and fixture tests using temporary Python child processes. It does not authorize an LM Studio daemon, model load, inference request, HTTP server, CyxCode invocation, Docker container, synthetic prompt, or benchmark input.

## Lean Boundary

Short, low-output commands—daemon up/down, `ps --json`, and unload—reuse the verified dependency-free `cli_transport.py` module. Its 1 MiB limit remains a post-completion acceptance bound. The long-running load command will use one standard-library `subprocess.Popen` child and one same-thread monitoring loop; no threads, framework, dependency, or Sheath-core change is introduced.

The loop must sample the exact owned service tree, host memory, GPU memory, port 1234, timeout, and temporary stdout/stderr file sizes. Its 1 MiB per-file threshold is sampled and may briefly overshoot between samples; it is not described as a strict disk quota. A measurement gap, threshold breach, timeout, or nonzero numeric exit fails closed.

## Ownership and Cleanup

The runner must start from zero LM Studio/lms processes and no port-1234 listener. After daemon startup it must capture exactly one `LM Studio.exe --run-as-service` root by PID and creation timestamp. Only that root's descendants and the direct load child belong to the attempt. Graceful unload and daemon down precede any forced cleanup, and forced termination is limited to the captured tree. Forced cleanup fails protocol acceptance even if final safety state is clean.

## Next Gate

Implement and fixture-test the exact runner without invoking LM Studio. After its code identity and fixture evidence are recorded, a separate decision may authorize at most one bounded load-health execution. Runtime remains blocked until then.

## Validation

The direct decision validator passes. Eleven focused tests reject dependency, concurrency, command, output, service-ownership, retry, cleanup, identity, and runtime-authority drift. The full pilot-data suite passes 146/146 on Python 3.12 and 3.14. The unchanged Sheath suite passes 138/138 on both versions outside the managed Windows filesystem sandbox; the sandbox-only attempt reproduced the documented temporary-directory ACL error and its 95 scratch directories were removed. No LM Studio/lms process or port-1234 listener remained.
