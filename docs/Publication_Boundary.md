# Publication Boundary

Decision `publication-boundary-001`, accepted 2026-08-23, defines the smallest reproducible public CyxSheath checkpoint. It protects restricted research inputs while keeping implemented claims independently inspectable.

## Published

- `sheath/src/`, `sheath/tests/`, and `sheath/scripts/`: dependency-free Stage-0 implementation, fixtures, and smoke entry points.
- `usage/`: operator instructions and runnable examples.
- `docs/`: living development decisions and conceptual boundaries linked to authoritative research and operating records.
- `Thesis/`: the manuscript, protocol, roadmap, schemas, validators, and curated evidence records.
- Root research plans referenced by the thesis, contributor guidance, and repository configuration.
- `integrations/README.md`: the public integration boundary.

Curated evidence may contain identifiers, hashes, bounded failure descriptions, and reproducibility metadata. It must not contain restricted task bodies, hidden tests, raw provider responses, credentials, or unreviewed source archives.

## Kept Local

- Raw conversation exports, global source context, review inputs, presentation drafts, and temporary notes.
- `.replay_cache/`, `logs/`, `.tools/`, smoke object stores, temporary workspaces, bytecode, dependencies, and build output.
- `integrations/cyxcode/`, which is an independent Git checkout with experimental adapter work and generated dependencies.

Ignored files are preserved locally; this decision does not authorize deletion.

## CyxCode Release Boundary

CyxCode remains a separate project. The public CyxSheath checkpoint includes the Python adapter, deterministic fixture tests, contracts, and integration evidence, but does not vendor the full CyxCode fork or claim that its experimental bridge sources can be rebuilt from this repository alone.

The bridge should later be published from a reviewed CyxCode commit or release and referenced by immutable identity. Until then, core tests and evidence validators are public reproduction paths; the live CyxCode smoke is a maintainer-only path requiring the separate experimental checkout.

## Admission Rule

Before staging a new file, confirm that it is necessary for code, operation, review, or reproducibility; contains no secret or restricted raw material; has a clear owner and documentation role; and passes the relevant tests or validators. Generated output stays ignored unless a curated record is explicitly required to support a claim.
