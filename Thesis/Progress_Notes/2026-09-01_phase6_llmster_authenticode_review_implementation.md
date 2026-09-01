# Phase-6 LLMster Authenticode Review Policy Implementation

## Outcome

The dependency-free, platform-independent review policy is implemented and source-bound. It operates only on generated owned-tree fixtures through an injected typed inspector. Fourteen policy fixtures and ten implementation-record mutations pass; the complete pilot suite passes 525/525 sequentially on Python 3.12 and 3.14.

No retained-child path was enumerated or read. No Windows signature tool was discovered or invoked. No platform adapter, process, network request, installer, target execution, benchmark input, cleanup, or retained-child change occurred.

## Implemented Boundary

`llmster_authenticode_review.py` reuses the unchanged staging ownership verifier instead of duplicating marker semantics. It reconstructs the payload count, byte total, and canonical content manifest before calling an inspector. It then reproduces the candidate suffix set, raw-UTF-8 ordering, exact candidate count, and newline-joined path digest.

After admission, every candidate is checked for identity stability immediately before and after its injected inspection. The policy normalizes all seven documented PowerShell signature statuses plus unrecognized, timeout, and tool-error observations. Unexpected inspector exceptions remain visible instead of being silently converted into tool errors. The result contains outcome counts and a classification-manifest digest, but no candidate paths, raw tool messages, or certificate details.

The policy result deliberately does not claim network, launch, installation, or internal retry counts for an injected inspector. Those facts are outside policy visibility and must be supplied by the future adapter and execution evidence. This refines where the design's zero-operation ceilings are enforced without weakening them.

## Lean Ownership

- Staging retains ownership of extraction, markers, and cleanup invariants.
- The new policy owns tree admission, candidate discovery, normalization, and aggregate evidence.
- A future Windows adapter will own process invocation, `-LiteralPath`, timeout, output bounds, and egress containment.

This avoids changing the already source-bound staging module and keeps platform mechanics outside the policy.

## Validation Note

The managed filesystem sandbox denied access to Python-created temporary fixture directories. The complete suites were therefore rerun outside that restrictive sandbox and passed. This was an execution-environment deviation only; the retained staging child was not used by any test.

## Next Gate

Create a separate design and generated-fixture checkpoint for the Windows adapter. It must define an absolute pinned PowerShell executable, literal non-shell arguments, bounded output and timeout behavior, one typed observation per input, no retry, and externally established zero-egress containment. Retained-child access and real `Get-AuthenticodeSignature` invocation remain blocked until a still-later committed execution decision.
