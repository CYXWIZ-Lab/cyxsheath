# Repository Guidelines

## Project Structure & Document Roles

This repository combines a thesis package, executable Stage-0 research core, and isolated integrations. `Thesis/` contains the manuscript, master roadmap, schemas, experiment protocol, and curated evidence records. `sheath/src/sheath/` contains the dependency-free Python core; `sheath/tests/` contains unit, scenario, and Docker-adapter tests. `usage/` contains public operator instructions. `integrations/` documents external boundaries; the optional `integrations/cyxcode/` worktree is deliberately ignored and maintained separately. Local raw context files are not part of the public repository.

## Development and Validation Commands

Run the Sheath tests from `sheath/`:

- `$env:PYTHONPATH='src'; py -3.12 -m unittest discover -s tests -v`
- `$env:PYTHONPATH='src'; py -3.14 -m unittest discover -s tests -v`

Use lightweight Markdown checks from PowerShell:

- `rg -n '^#{1,3} ' -g '*.md' .` lists document headings and line numbers.
- `python -m unittest discover -s Thesis\pilot_data -p 'test_*.py' -v` validates curated Phase-6 records.
- `git diff --check` detects trailing whitespace when the folder is placed under Git.

CyxCode uses Bun. If the separate checkout is present, follow its nested `AGENTS.md`; run tests or `bun typecheck` from package directories such as `integrations/cyxcode/packages/opencode`, never from the CyxCode repository root.

## Writing Style & Naming Conventions

Use UTF-8 Markdown, ATX headings (`#`, `##`), short paragraphs, and blank lines around lists. Give each standalone document one descriptive H1. Prefer precise, testable language; distinguish hypotheses from findings and avoid unsupported claims such as “bug-free” or “AGI achieved.” Follow the established `Title_Case_With_Underscores.md` pattern for new research documents. Preserve established technical terms, including CyxWiz, knowledge base, and thinking base.

## Research Validation Guidelines

Treat reproducibility as the equivalent of testing. Benchmark changes should state the task, dataset or fixture, train/validation/test split, metric, baseline, and pass criterion. Record assumptions and cite primary sources for factual claims. Keep proposed methods clearly separated from completed experiments and reported results.

## Commit & Pull Request Guidelines

Use concise, imperative commits with a scope, for example `docs: clarify benchmark scoring` or `core: bind evidence to revision`. Pull requests should summarize the research purpose, list affected documents, identify changed claims or metrics, and describe validation performed. Link relevant issues or sources; include screenshots only when rendered layout materially changes.

## Agent-Specific Guidance

Make narrow, reviewable edits. Do not commit raw context, caches, logs, model responses, generated artifact stores, or independent integration worktrees. Follow [docs/Publication_Boundary.md](docs/Publication_Boundary.md) before staging research evidence.

Treat any separate upstream CyxCode source as read-only material. Make experimental CyxCode changes only in an independent `integrations/cyxcode/` checkout on its integration branch. Preserve that checkout's remotes so successful work can later become an upstream merge, plugin, or direct integration; never add the checkout as an embedded repository.
