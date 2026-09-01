# Phase-6 Authenticode Execution-Preflight Design

## Outcome

The fixture-only execution-preflight boundary is frozen. It authorizes one dependency-free pure policy module and generated observations; it does not authorize retained-child access, real PowerShell discovery or hashing, firewall inspection or mutation, event-log access, or Authenticode invocation.

The policy will accept typed executable, Windows Defender Firewall/WFP, batch, and one-shot observations and emit an immutable plan. It will perform no filesystem, process, network, firewall, event-log, or clock I/O. This keeps the 284-line owned-tree review policy and 199-line single-candidate Windows adapter unchanged.

## Containment Decision

The later provider must establish an enabled outbound block rule for the exact observed `powershell.exe` across Domain, Private, and Public profiles, with any protocol, address, and port. The rule must be effective before the one-shot claim and remain effective through the last adapter call. Later evidence may retain only aggregate WFP blocked-connection counts and digests, not raw events or local paths.

This is a precise program-scoped claim: the project may claim externally enforced outbound denial for the exact PowerShell executable, not machine-wide absence of network activity. Rule creation, verification, audit reading, and removal require a separate provider design and authorization.

## Batch and One-Shot Boundary

The plan binds the retained staging result's 91 candidates and digests, permits at most 91 adapter calls, preserves the adapter's ten-second per-call timeout, and adds a 300-second overall deadline. A new call may start only with at least ten seconds remaining. Deadline expiry produces an incomplete normalized result and cannot claim successful full classification.

A later runner must create an atomic claim after preflight and before retained-child access. Existing claim or result state blocks execution. Success, failure, or interruption consumes the authorization, and automatic retry remains zero.

## Validation

Twelve mutations protect the accepted evidence links, candidate count, firewall scope, deadline, call bound, one-shot behavior, privacy, and execution gates. The next step is to implement and source-bind the pure module with generated observations only.
