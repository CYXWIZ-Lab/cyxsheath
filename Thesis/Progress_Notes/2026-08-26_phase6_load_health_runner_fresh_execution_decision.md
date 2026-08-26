# Phase 6 Load-Health Runner Fresh Execution Decision

## Outcome

The fresh execution review is complete, but execution remains blocked. No runtime authorization was created and no LM Studio command, daemon, model load, inference request, HTTP server, CyxCode invocation, or Docker operation ran.

## Blocking Finding

The installed 2.29.1 engine still contains 20 files totaling 558,082,098 bytes. The manifest, server executable, CLI, preference file, and model weight retain their pinned identities. However, the recorded full-inventory digest `389f3fc...` was serialized after PowerShell's culture-aware `Sort-Object FullName` ordering, while `lm_studio_windows.py` recomputes the same file entries with Python's Windows-path ordering and obtains `c016b534...`. The ordering differs at the `ggml_llamacpp.dll`/`ggml-base.dll` boundary.

This is a canonicalization mismatch, not proof that engine content changed. The current runner would create and retain its one-shot claim, fail the engine check before starting the daemon, and consume the authorization. A runtime decision would therefore be knowingly invalid.

## Validation and Boundary

The append-only decision record is validated by ten mutation tests on Python 3.12 and 3.14. The tests reject dependency drift, mismatch concealment, ordering-witness drift, claim-order concealment, execution overclaims, runtime operations, and synthetic-canary permission. The complete pilot suite passes 203/203 on both Python versions. Initial sandboxed runs could not write inside `TemporaryDirectory` ACLs; unchanged suites passed outside that filesystem restriction, and the temporary workspace test directory was removed.

The next slice must select one explicit locale-independent inventory order, repin the runner and fixtures, and repeat the execution decision. It must not reinterpret either digest as model-quality evidence or authorize an automatic retry.
