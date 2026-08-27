# Phase 6 llmster Acquisition Implementation

## Outcome

The dependency-free acquisition module is implemented and fixture-proven without contacting the archive host. It accepts only the pinned `0.0.21-2` Windows x64 full archive URL, rejects redirects and non-200 responses, enforces the 1 GiB transfer ceiling and 32 GiB post-transfer reserve, streams SHA-256 and SHA-512, flushes the partial file, and atomically places it only after the published SHA-512 matches.

The module has no command-line entry point. It cannot extract, install, or execute the archive. The network opener and free-space probe are injectable so fixtures remain in memory and deterministic.

## Failure and Ownership Rules

An existing destination blocks acquisition without mutation. An unexpected existing `.partial` file is also preserved and blocks the run because its ownership is unknown. On request, stream, checksum, storage, or placement failure, the module removes only the partial file created by that invocation.

Thirteen fixtures cover successful placement, URL/status rejection, declared and streamed size bounds, checksum cleanup, both storage gates, destination and partial preservation, request normalization, invalid response chunks, and timeout rejection.

## Evidence and Validation

The pinned result is [phase6_llmster_acquisition_implementation_result.json](../pilot_data/review_evidence/phase6_llmster_acquisition_implementation_result.json). Ten result-validator tests reject preflight or source drift, redirects, retries, reduced storage reserve, weakened partial ownership, fixture network activity, download authorization, and dependency growth.

```powershell
python Thesis\pilot_data\validate_llmster_acquisition_implementation_result.py Thesis\pilot_data\review_evidence\phase6_llmster_acquisition_implementation_result.json
py -3.12 -m unittest discover -s Thesis\pilot_data -p 'test_*.py'
py -3.14 -m unittest discover -s Thesis\pilot_data -p 'test_*.py'
```

The complete pilot suite passes 296/296 on Python 3.12 and 3.14. Fixture execution made zero network requests and downloaded zero archive bytes.

## Next Gate

Make a separate validator-backed decision before one archive request. Download, extraction, installation, runtime execution, retry, HTTP serving, prompts, CyxCode invocation, and benchmark input remain unauthorized.
