# Phase 6 LLMster Extraction-Staging Design

## Outcome

A validator-backed design now authorizes implementation and generated-archive fixtures for a new dependency-free `llmster_archive_staging` module. It does not authorize reading member contents from or extracting the real LLMster archive.

The new module owns only the staging lifecycle. The existing inventory module remains the metadata and canonical-path policy owner; installation and runtime responsibilities are not added.

## Frozen Boundary

- Use an existing absolute, non-symlink parent and exclusively create one `llmster-<32 hex>` child.
- Create a matching ownership marker before member writes.
- Require 6,086,645,562 free bytes before the real 1,791,678,266-byte declared expansion, preserving 4 GiB afterward.
- Stream at no more than 8 MiB per read; verify each declared size, SHA-256, total bytes, and a canonical content-manifest digest.
- Reject links, special members, traversal, collisions, existing destinations, and any canonical destination outside the owned child.
- Retain successful staging only for a separate signature review; on failure, remove only the marker-verified owned child and report cleanup failure.
- Never execute a binary, invoke an installer, access the network, or retry automatically.

Authenticode candidates are limited to `.dll`, `.exe`, `.node`, and `.ps1`. Actual signature tooling remains blocked until a later real-staging decision.

Ten decision mutations pass on Python 3.12 and 3.14; the complete Phase 6 suite passes 438/438 on both versions. The next step is module implementation and generated fixtures only.
