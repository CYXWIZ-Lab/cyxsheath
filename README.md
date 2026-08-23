# CyxSheath

This folder documents the research program for building a software-engineering LLM agent using CyxWiz Engine as the experiment, dataset, training, evaluation, and artifact platform.

The goal is not only to build a model that writes code. The goal is to build an agent that can perform disciplined software engineering: understand codebases, plan changes, implement features, debug failures, write tests, review risks, reason about security, and improve software over long-running tasks.

## Core Thesis

A strong software-engineering agent is a credible path toward broader machine intelligence because software engineering combines reasoning, mathematics, systems thinking, design, security, language understanding, tool use, and applied problem solving.

The first research target is narrow and measurable:

- C
- C++
- Python
- build systems
- tests
- debugging
- code review
- security analysis
- documentation
- long-running tool-using workflows

Large goals such as designing a programming language, building an operating system, or producing a full game engine should be treated as late-stage stress tests, not the starting benchmark.

## Documents

- [Thesis/README.md](Thesis/README.md): structured thesis package, implementation blueprint, dataset/model plan, experiment protocol, schemas, and paper plan.
- [sheath/README.md](sheath/README.md): dependency-free Stage-0 implementation of contracts, state transitions, host/container executable authorization, content-addressed artifacts, a fail-closed runner, a digest-pinned Docker adapter, mandatory checks, and canonical run records.
- [Research_Thesis.md](Research_Thesis.md): academic framing, mission, hypotheses, research questions, capability model, and safety position.
- [CyxWiz_Implementation_Plan.md](CyxWiz_Implementation_Plan.md): how CyxWiz Engine should be used to build datasets, training graphs, evaluation graphs, checkpoints, and experiment artifacts.
- [Evaluation_Benchmarks.md](Evaluation_Benchmarks.md): measurable tasks and scoring methods for proving progress.

## Working Principle

The project separates two things:

1. Knowledge base: the code, documentation, bugs, tests, security reports, compiler diagnostics, and engineering examples the model learns from.
2. Thinking base: the process the model uses to turn knowledge into correct engineering action.

The thinking base follows a practical engineering loop:

1. Understand the task.
2. Form a hypothesis.
3. Inspect evidence.
4. Plan a small change.
5. Implement.
6. Run tests.
7. Analyze failure.
8. Correct.
9. Verify.
10. Document the result.

## Role of CyxWiz

CyxWiz is the research engine for this work. It should support:

- dataset ingestion and cleaning
- code/document/test preprocessing
- train, validation, and test splitting
- graph-based training workflows
- evaluation workflows
- experiment tracking
- export of clean datasets and artifacts
- training curves and benchmark visualization
- checkpoint and model package management

## Research Discipline

The project must avoid vague claims such as "bug-free" or "AGI achieved" unless those claims are tied to concrete tests. Progress should be measured with reproducible datasets, fixed benchmarks, hidden tests, security checks, and logged experiment artifacts.
