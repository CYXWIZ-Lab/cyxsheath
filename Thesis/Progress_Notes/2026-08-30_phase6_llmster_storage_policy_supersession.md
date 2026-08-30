# Phase 6 llmster Storage-Policy Supersession

## Decision

Supersede the unused 32-GiB final-reserve authorization with one versioned acquisition-policy module that requires 9 GiB free before the request and 8 GiB afterward. The archive remains capped at 1 GiB. The original content-addressed implementation remains unchanged; the revised module reuses its URL, redirect, streaming, checksum, cleanup, and atomic-placement machinery.

The earlier authorization was never invoked and is now non-executable. Across the old and new decisions, only one archive request remains authorized and no retry is permitted.

## Rationale

This operation writes at most one 1-GiB partial file and renames it on the same volume after SHA-512 verification. It cannot inventory, extract, install, or execute the archive. Atomic rename does not create a second archive copy. An 8-GiB final reserve is eight times the maximum write while avoiding deletion of required thesis replay images.

The fresh baseline observed 21,203,013,632 free bytes against a 9,663,676,416-byte pre-request requirement. The destination and partial paths were absent.

## Validation and Boundary

Five policy fixtures cover exact and failing pre/post storage boundaries, retained destination protection, and unchanged acquisition identity. Ten decision mutations reject evidence or module drift, reserve weakening, request widening, retry, extraction, and benchmark use. The complete pilot suite passes 331/331 on Python 3.12 and 3.14 without network access.

The next action is exactly one call through the revised module after validation. Archive inventory, extraction, installation, LM Studio execution, inference, HTTP serving, CyxCode execution, and benchmark input remain blocked.
