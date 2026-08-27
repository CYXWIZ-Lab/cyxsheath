# CyxSheath

CyxSheath is a research system for evidence-grounded supervision of AI coding agents. It freezes the task contract, constrains execution, preserves revision-bound evidence, independently verifies proposed changes, and issues fail-closed verdicts.

The long-term research goal is a dedicated residual critic built and evaluated with CyxWiz Engine. That model is not implemented yet: the current release is the deterministic **Sheath Stage 0** supervisor, with CyxCode as the first coding-agent generator integration.

## System Boundary

```text
Task -> Sheath contract -> CyxCode + coding model -> proposed patch
     -> isolated execution -> independent checks -> accept/reject/abstain
```

CyxCode proposes changes. Sheath owns isolation, trusted patch extraction, evidence, verification, and the final decision. A future CyxSheath-D1 critic will be considered only if the deterministic experiment reveals a stable residual problem that rules and tests cannot resolve.

## Quick Start

Python 3.11 or newer is required. The current suite is verified on Python 3.12 and 3.14 and has no third-party runtime dependencies.

From PowerShell:

```powershell
$env:PYTHONPATH='sheath\src'
py -3.12 usage\examples\stage0_decision_example.py

Set-Location sheath
$env:PYTHONPATH='src'
py -3.12 -m unittest discover -s tests -v
```

From a POSIX shell:

```sh
PYTHONPATH=sheath/src python usage/examples/stage0_decision_example.py
cd sheath
PYTHONPATH=src python -m unittest discover -s tests -v
```

The example creates an immutable contract, records current evidence, and returns a deterministic verdict. It does not call a model or modify a repository. Docker and Bun are optional unless running container or CyxCode integration smokes.

## Current Status

| Area | Status |
|---|---|
| Sheath Stage 0 | Implemented; 138 tests pass on Python 3.12 and 3.14 |
| CyxCode adapter | Python boundary and deterministic fixture verified; experimental bridge remains a separate checkout |
| Phase-6 pilot | Active; acquisition module fixture-proven, 20 candidates quarantined, no benchmark result claimed |
| CyxWiz integration | Phase-7 capability audit pending |
| CyxSheath-D1 critic | Conditional design and training in Phases 9–10 |

## Documentation

- [Development documentation](docs/README.md): living architecture decisions, model/evidence boundaries, and research-to-production explanations.
- [Usage guide](usage/README.md): setup, examples, tests, evidence validation, and operational restrictions.
- [Thesis package](Thesis/README.md): manuscript, architecture, protocol, dataset/model plan, paper plan, and evidence records.
- [Master roadmap](Thesis/Research_and_Implementation_Roadmap.md): authoritative completed, active, and pending work.
- [Stage-0 package](sheath/README.md): implemented modules, test coverage, and Docker smokes.
- [Research framing](Research_Thesis.md), [CyxWiz plan](CyxWiz_Implementation_Plan.md), and [benchmark plan](Evaluation_Benchmarks.md): source design documents retained for traceability.
- [Publication boundary](docs/Publication_Boundary.md): what is public, what remains local, and why.
- [Contributor guide](AGENTS.md): repository conventions and validation commands.

## Research Integrity

Infrastructure checks are not model-quality results. Public benchmark membership excludes a case from the confirmatory test set, and quarantined cases must not be sent to a provider or used for training. Claims become findings only when supported by versioned artifacts and the frozen experiment protocol.

CyxWiz Engine is the intended dataset, training, evaluation, and artifact platform for a future dedicated critic, subject to the Phase-7 capability audit. The repository does not currently claim a trained critic, completed CyxWiz graph, admitted training corpus, or improved coding-agent performance.

## License Status

No repository-wide license has been selected for this research checkpoint. Third-party projects, benchmark identifiers, and referenced evidence retain their own terms, and unresolved dataset rights must not be inferred from public visibility. A code-and-document licensing decision should be recorded separately before presenting CyxSheath as an open-source release.
