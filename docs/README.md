# Development Documentation

This folder records development-facing decisions and conceptual boundaries that contributors need while CyxSheath evolves. It explains why the system is designed a certain way and links to the authoritative research or operational evidence.

## Documentation Roles

| Location | Purpose |
|---|---|
| `docs/` | Living architecture decisions, research-to-production boundaries, and contributor-facing explanations |
| `Thesis/` | Formal research argument, frozen protocol, roadmap, schemas, progress records, and curated evidence |
| `usage/` | Commands, setup, validation, troubleshooting, and current operating restrictions |
| `AGENTS.md` | Repository contribution and agent-editing rules |

Do not copy raw logs, model responses, benchmark task bodies, hidden tests, credentials, or temporary artifacts into `docs/`. Link to privacy-minimized evidence records instead.

## Current Documents

- [Model Use and Evidence Boundary](Model_Use_and_Evidence_Boundary.md): why a model may be usable through CyxCode but blocked from a thesis benchmark, what kind of generator the experiment needs, and how frontier models can later be used in production.
- [Publication Boundary](Publication_Boundary.md): files and evidence permitted in the public repository versus material that remains local.

## Update Rule

Add or update a document when a decision changes system architecture, experimental validity, data exposure, model admission, or production deployment. Keep the explanation short and link the corresponding roadmap, protocol, usage instruction, or validator-backed record. Label proposed, accepted, observed, failed, and blocked states explicitly; do not turn a plan or infrastructure check into a finding.

When implementation changes operating commands, update `usage/`. When evidence changes the research status, update the relevant `Thesis/` record and master roadmap. A `docs/` explanation supports those sources but does not supersede them.
