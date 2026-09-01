# Phase-6 Windows Authenticode Adapter Implementation

## Outcome

The dependency-free Windows Authenticode adapter and its fixed PowerShell script are implemented and source-bound. Twenty adapter fixtures and ten implementation-record mutations pass; the complete pilot suite passes 567/567 sequentially on Python 3.12 and 3.14.

Only generated candidates, a generated fake `powershell.exe` file, and fake transport callbacks were used. The fixed script was read for identity and semantic assertions but was not executed. No real PowerShell path was discovered or hashed, no process or signature tool ran, and the retained staging child was not enumerated, read, modified, or removed.

## Implemented Boundary

The adapter requires an absolute regular non-link executable named `powershell.exe`, its expected SHA-256, the fixed script digest, and an absolute regular candidate with an allowlisted suffix. It checks executable, script, and candidate identities around the single transport call.

The exact request uses `-NoLogo -NoProfile -NonInteractive -File`, followed by the fixed script and one `-CandidatePath` value. The candidate remains a single literal argument and is never interpolated into PowerShell source. The script calls `Get-AuthenticodeSignature -LiteralPath` once and emits only schema version and status as compressed JSON. It does not use `Invoke-Expression`, `Start-Process`, or an execution-policy override.

The unchanged CLI transport owns direct `shell=False` execution, a ten-second timeout, and a 4-KiB combined retention ceiling. The adapter additionally limits stdout JSON to 512 bytes, rejects duplicate or extra keys, and accepts only bounded ASCII status text. Timeout is distinct from tool error; unexpected programming exceptions are not concealed.

The repository attributes now force LF checkout for `.ps1` files, matching the existing Python, JSON, Markdown, and patch policy. This prevents platform line-ending conversion from invalidating the fixed script's source-bound digest.

## Lean Ownership

- The review policy still owns tree admission, candidate order, outcome normalization, and aggregate evidence.
- The Windows adapter owns executable/script identity, exact argv, transport failure mapping, and strict JSON parsing.
- The fixed script owns the single `-LiteralPath` cmdlet operation.
- A later execution preflight must own real executable selection, batch deadline, and external zero-egress evidence.

## Next Gate

Design and fixture-test a real-execution preflight without touching the retained child or real PowerShell. It must freeze one exact executable identity, an overall 91-candidate deadline, external zero-egress containment evidence, one-shot authorization consumption, aggregate-only output, and no retry. Only a later committed execution decision may inspect real candidates.
