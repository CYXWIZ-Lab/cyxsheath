# Phase 6 llmster Acquisition Preflight

## Outcome

The acquisition contract is frozen without downloading the `llmster` archive. The mutable `install.ps1` path is rejected. A future dependency-free module may acquire only the exact Windows x64 full archive over HTTPS, stream it to an ignored partial file, enforce size and disk-reserve bounds, require the pinned published SHA-512, compute SHA-256 and exact bytes, and atomically rename only after verification.

The selected release is `0.0.21-2`; the exact archive is `0.0.21-2-win32-x64.full.zip`. Its official checksum document reports SHA-512 `ec13183ddc2f56d68b48fc13428e0cdca84c29bfc2b87a7aa2b9befeb7b79a8cdd3ea5a7c50d6e941fcf43545c8730f8b2bf2665b030b98e5ccfab6a3d43efff`. Only the small checksum document was retrieved. The archive endpoint rejected a HEAD request, so no byte-size claim is made before acquisition.

## Preserved State

Acquisition must not modify LM Studio home, `PATH`, engine preferences, the pinned desktop CLI, the 2.29.1 engine inventory, or the symbolically imported Qwen weight. It permits no ZIP extraction or executable launch. Any partial transfer is the only file removable on failure; an unexpected destination blocks without mutation.

## Lean Boundary

The future module will own exact archive acquisition only. The lifecycle parser, Windows process adapter, load-health runner, Sheath core, model contract, and CyxCode seam remain unchanged. No dependency or thread is added.

## Evidence and Validation

The decision is [phase6_llmster_acquisition_preflight_decision.json](../pilot_data/review_evidence/phase6_llmster_acquisition_preflight_decision.json). Ten negative mutations reject evidence or checksum drift, mutable-installer use, redirects, retries, reduced storage reserve, LM Studio-home mutation, extraction, download, and runtime permission.

```powershell
python Thesis\pilot_data\validate_llmster_acquisition_preflight_decision.py Thesis\pilot_data\review_evidence\phase6_llmster_acquisition_preflight_decision.json
py -3.12 -m unittest discover -s Thesis\pilot_data -p 'test_*.py' -v
py -3.14 -m unittest discover -s Thesis\pilot_data -p 'test_*.py' -v
```

The complete pilot suite passes 273/273 on both Python versions. Next, implement and fixture-test the acquisition module without network access, then make a separate archive-download execution decision.
