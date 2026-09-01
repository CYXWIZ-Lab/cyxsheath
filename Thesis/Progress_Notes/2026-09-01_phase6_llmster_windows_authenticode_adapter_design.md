# Phase-6 Windows Authenticode Adapter Design

## Decision

This checkpoint authorizes only source and generated-fixture work for a Windows PowerShell Authenticode adapter. It does not authorize enumerating or reading the retained child, discovering or hashing the real PowerShell executable, invoking PowerShell or `Get-AuthenticodeSignature`, networking, installing files, executing target binaries, or removing the retained child.

The platform-independent policy remains responsible for owned-tree admission, candidate ordering, normalization, and aggregate evidence. A new Windows adapter will own executable/script identity validation, exact argument construction, one transport call, and strict response parsing. The existing source-bound CLI transport remains unchanged and supplies absolute-executable validation, `shell=False`, timeout, and bounded retained output.

## Frozen Command

The future command is one direct `powershell.exe` child per candidate:

```text
powershell.exe -NoLogo -NoProfile -NonInteractive -File <fixed-script> -CandidatePath <absolute-candidate>
```

The fixed script accepts a string parameter and calls `Get-AuthenticodeSignature -LiteralPath`. No candidate path is interpolated into PowerShell source, no profile is loaded, and no execution-policy override is added. Microsoft documents that values following `-File` are script parameters and that `-NonInteractive` converts attempts to prompt into terminating errors. Microsoft also documents that `-LiteralPath` does not interpret wildcard characters. See [about_PowerShell_exe](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_powershell_exe?view=powershell-5.1) and [Get-AuthenticodeSignature](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.security/get-authenticodesignature).

Each transport call is limited to ten seconds and 4,096 retained output bytes. Only exit zero, empty stderr, and a strict UTF-8 JSON object containing exactly `schema_version` and `status` may produce a status observation. Timeout remains distinct; start, output, exit, identity, and parse failures become tool errors. There is no retry.

## Network Boundary

The adapter cannot prove whether Windows trust evaluation performs network access. It therefore makes no network claim. A later real-execution decision must identify and evidence an external zero-egress containment mechanism and a batch deadline before any signature-tool invocation.

## Next Gate

Implement the adapter and fixed script, then test them only with generated candidate files, a fake `powershell.exe` file, and a fake transport. Source-bind the result before any real tool or retained-child access.
