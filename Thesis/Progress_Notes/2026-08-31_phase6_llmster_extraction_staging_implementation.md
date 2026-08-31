# Phase 6 LLMster Extraction-Staging Implementation

## Outcome

The frozen dependency-free staging boundary is implemented and source-bound. Nineteen generated-ZIP fixtures pass on Python 3.12 and 3.14. The real LLMster archive was not opened for member content and was not extracted.

The inventory module remains the single owner of canonical path and member-kind policy. The new staging module owns only exclusive child creation, the ownership marker, bounded streamed writes, content evidence, and marker-verified cleanup. It adds no process, network, installer, runtime, Sheath-core, or CyxCode surface.

## Verified Behavior

- An absolute existing non-symlink parent and a new `llmster-<32 hex>` child are mandatory.
- The archive identity, stable source file identity, canonical inventory digest, declared expansion, 4-GiB final reserve, and 8-MiB read ceiling are enforced.
- Canonical destinations remain inside the owned child; traversal, links, special members, collisions, and existing file destinations fail closed.
- Per-file SHA-256, exact written sizes, a canonical content-manifest digest, and signature-candidate path digest are computed without retaining member names in the curated result.
- Stream, size, reserve, or policy failure removes only the matching marker-owned child. Wrong or missing markers block the public cleanup function.
- Successful staging is retained for a later, separate signature review; no binary is launched.

The implementation record and ten negative mutations bind the exact decision and four source files. The complete pilot-data suite passes 467/467 on Python 3.12 and 3.14.

## Validation

```powershell
python Thesis\pilot_data\validate_llmster_extraction_staging_implementation_result.py Thesis\pilot_data\review_evidence\phase6_llmster_extraction_staging_implementation_result.json
python -m unittest Thesis.pilot_data.test_llmster_archive_inventory Thesis.pilot_data.test_llmster_archive_staging Thesis.pilot_data.test_validate_llmster_extraction_staging_implementation_result -v
python -m unittest discover -s Thesis\pilot_data -p 'test_*.py' -v
```

## Next Gate

Create and commit a separate validator-backed real-staging decision before any member-content read or extraction from the pinned archive. That decision must recheck implementation identities, archive identity, parent cleanliness, and current storage, authorize at most one attempt, and keep Authenticode tooling, installation, execution, networking, benchmark input, and retry blocked.
