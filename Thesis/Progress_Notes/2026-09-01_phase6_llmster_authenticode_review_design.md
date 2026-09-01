# Phase-6 LLMster Authenticode Review Design

## Decision

The accepted retained staging tree is bound to 91 Authenticode candidates by count and canonical-path digest. This checkpoint authorizes only a dependency-free, platform-independent review policy and generated-fixture tests. It does not authorize enumerating or reading the retained child, discovering or invoking a signature tool, implementing a Windows process adapter, installing files, executing targets, networking, or removing the retained child.

The staging module continues to own extraction and marker lifecycle. A separate `llmster_authenticode_review` module will own marker/manifest admission, deterministic candidate discovery, result normalization, and aggregate evidence. An injected fake inspector is the only inspector allowed in this checkpoint.

## Frozen Semantics

Candidates remain limited to case-insensitive `.dll`, `.exe`, `.node`, and `.ps1` suffixes. The policy must reconstruct the full content manifest before inspection, reproduce the exact 91-candidate path digest, and reject drift before the first inspector call. Curated evidence may retain counts and digests, but not paths, raw status messages, or certificate details.

Microsoft documents seven `SignatureStatus` values. The design keeps `Valid`, `NotSigned`, `HashMismatch`, `UnknownError`, `NotTrusted`, `NotSupportedFileFormat`, and `Incompatible` distinguishable through explicit normalized outcomes; unrecognized values, timeout, and tool failure also remain distinct. Importantly, Microsoft defines `Valid` as syntactic validity only, not publisher trust. See [Get-AuthenticodeSignature](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.security/get-authenticodesignature) and [SignatureStatus](https://learn.microsoft.com/en-us/dotnet/api/system.management.automation.signaturestatus).

## Boundary Decision

The future Windows adapter is deferred because platform process, timeout, and egress controls change independently from review policy. Its planned cmdlet parameter is `-LiteralPath`, which avoids wildcard interpretation. The cmdlet may select a catalog signature over an embedded signature when both exist. Official cmdlet documentation does not establish a zero-network guarantee, so a later real-execution decision must establish external zero-egress containment before any tool invocation.

## Next Gate

Implement and fixture-test only the platform-independent policy, then record its source identities and full sequential test results. A later committed decision is still required before the retained child is enumerated or any Windows signature tool is discovered or invoked.
