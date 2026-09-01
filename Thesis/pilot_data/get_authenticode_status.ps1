[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string] $CandidatePath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$signature = Get-AuthenticodeSignature -LiteralPath $CandidatePath -ErrorAction Stop
[ordered]@{
    schema_version = '1.0.0'
    status = [string] $signature.Status
} | ConvertTo-Json -Compress
