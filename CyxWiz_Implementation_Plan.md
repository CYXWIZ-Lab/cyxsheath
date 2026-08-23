# CyxWiz Implementation Plan

## Purpose

This document describes how to use CyxWiz Engine to build the software-engineering LLM agent research pipeline.

CyxWiz is not only the application being used. It is the research system that should ingest data, clean it, build datasets, run training graphs, run evaluation graphs, export artifacts, and visualize results.

## High-Level Architecture

The research workflow is divided into six pipelines:

1. raw data ingestion
2. data cleaning and normalization
3. supervised training dataset construction
4. reasoning-process dataset construction
5. model training and checkpointing
6. benchmark evaluation and reporting

Each pipeline should be represented as a saved CyxWiz graph where possible.

## Data Sources

The first version should use data that directly teaches software engineering behavior.

### Repository Data

- C projects
- C++ projects
- Python projects
- build scripts
- tests
- documentation
- CI configuration

### Change Data

- commits
- pull requests
- issue descriptions
- review comments
- failing tests before fix
- passing tests after fix
- compiler errors before fix
- patches that resolve the error

### Security Data

- vulnerable code snippets
- fixed versions
- CVE summaries
- static analyzer findings
- secure coding rules
- unsafe API usage examples

### Tool-Use Data

- command run
- command output
- failure reason
- next action
- final verification

## Dataset Schema

Use structured records instead of untyped text blobs.

### Engineering Task Record

```json
{
  "task_id": "unique id",
  "language": "c | cpp | python",
  "task_type": "bug_fix | feature | test | refactor | security | docs",
  "repository": "source repo or benchmark name",
  "prompt": "user or issue request",
  "context_files": [
    {"path": "src/file.cpp", "content": "..."}
  ],
  "evidence": [
    {"kind": "test_output", "content": "..."},
    {"kind": "compiler_error", "content": "..."}
  ],
  "patch": "unified diff or file edit representation",
  "verification": [
    {"command": "ctest -R example", "result": "pass | fail", "output": "..."}
  ],
  "risk_labels": ["memory", "security", "api_contract"],
  "quality_labels": ["scoped", "tested", "documented"]
}
```

### Reasoning Trace Record

```json
{
  "trace_id": "unique id",
  "task_id": "linked task id",
  "steps": [
    {"phase": "understand", "text": "..."},
    {"phase": "inspect", "text": "..."},
    {"phase": "hypothesis", "text": "..."},
    {"phase": "edit", "text": "..."},
    {"phase": "test", "text": "..."},
    {"phase": "repair", "text": "..."},
    {"phase": "verify", "text": "..."}
  ],
  "final_status": "solved | failed | blocked",
  "failure_reason": "optional"
}
```

## CyxWiz Pipeline 1: Raw Ingestion

Goal: load raw repository, issue, commit, and log data into a normalized tabular or document dataset.

Recommended graph shape:

```text
DataInput -> DataPreview -> DataValidator -> ExportParquet
```

Expected outputs:

- raw repository metadata
- raw source file table
- raw issue table
- raw commit table
- raw build log table

Export format:

- Parquet for large structured datasets
- JSONL for trace-style examples

## CyxWiz Pipeline 2: Cleaning and Deduplication

Goal: remove low-quality, duplicate, generated, or irrelevant data.

Recommended operations:

- remove vendored/generated files
- remove minified files
- remove binary files
- normalize line endings
- classify language
- detect test files
- deduplicate near-identical files
- filter repositories without tests or build metadata

Recommended graph shape:

```text
DataInput -> FilterRows -> SelectColumns -> RemoveDuplicates -> DataValidator -> ExportParquet
```

Quality gates:

- every record has language
- every code file has path and content
- generated files are flagged
- train/test contamination is checked

## CyxWiz Pipeline 3: Supervised Dataset Construction

Goal: build instruction-response records for code understanding, patch generation, debugging, testing, and documentation.

Task families:

- explain code
- write function
- fix compile error
- fix failing test
- add regression test
- refactor safely
- review code
- detect vulnerability
- document API

Recommended output columns:

- instruction
- repository context
- input files
- expected patch
- expected explanation
- verification command
- labels

## CyxWiz Pipeline 4: Reasoning Dataset Construction

Goal: teach the agent the engineering loop, not only final answers.

Trace phases:

1. task interpretation
2. repository inspection
3. hypothesis
4. planned edit
5. actual edit
6. test result
7. failure analysis
8. correction
9. final verification
10. final summary

This dataset should be curated carefully. Bad reasoning traces will teach bad engineering behavior.

## CyxWiz Pipeline 5: Training

Goal: train or fine-tune models and compare them against baselines.

Model stages:

1. baseline code model evaluation
2. supervised fine-tuning on engineering task records
3. reasoning-process fine-tuning on trace records
4. tool-use fine-tuning on command/evidence/action records
5. safety fine-tuning on refusal and secure coding records

CyxWiz should track:

- dataset version
- graph version
- model architecture
- training parameters
- loss curves
- validation metrics
- checkpoint path
- evaluation score

Recommended artifacts:

- model checkpoint
- tokenizer or vocabulary package
- dataset manifest
- graph manifest
- evaluation report

## CyxWiz Pipeline 6: Evaluation

Goal: run repeatable benchmarks that measure engineering ability.

Recommended graph shape:

```text
DataInput -> ModelInference -> TaskRunner -> Metrics -> ExportJSON
```

If CyxWiz does not yet have every needed node, start with external runner integration and keep the outputs in CyxWiz-compatible tables.

Evaluation should include:

- pass rate
- hidden test pass rate
- compile success
- patch size
- number of attempts
- security regression count
- review score
- time to solution
- failure category

## Minimal Viable Research Build

The first version should be small and provable.

### MVP Dataset

- 1,000 C examples
- 1,000 C++ examples
- 1,000 Python examples
- each example includes task, context, patch, and verification

### MVP Tasks

- fix compile error
- fix failing unit test
- write missing test
- explain function
- detect unsafe code pattern

### MVP Evaluation

- 100 held-out tasks
- no overlap with training repositories
- automatic pass/fail scoring
- manual review for patch quality

## Roadmap

### Phase 1: Research Foundation

- finalize thesis document
- finalize dataset schema
- define safety policy
- define benchmark scoring
- create CyxWiz graph templates

### Phase 2: Dataset Engine

- ingest repositories
- ingest commits and issues
- build cleaning pipeline
- export clean Parquet and JSONL datasets
- create dataset manifests

### Phase 3: Baseline Evaluation

- select baseline model
- run held-out benchmark
- record failure categories
- establish baseline metrics

### Phase 4: Fine-Tuning

- train on supervised task records
- train on reasoning traces
- compare against baseline
- analyze regressions

### Phase 5: Tool-Using Agent

- add command execution traces
- evaluate build/test/debug loops
- measure repair after failure
- add sandbox and audit policy

### Phase 6: Security and Reliability

- train on vulnerability repair data
- evaluate secure coding benchmarks
- add static analysis feedback
- measure introduced vulnerability rate

### Phase 7: Long-Running Engineering

- multi-file bug fixes
- small feature implementation
- library migration
- small compiler or interpreter project
- compact game engine or runtime prototype

## Engineering Guardrails

Keep the first implementation small:

- do not build every model feature at once
- do not start with unrestricted autonomy
- do not mix low-quality data into the first dataset
- do not evaluate using only easy code-completion tasks
- do not claim AGI from demos
- do preserve every experiment artifact
- do make every result reproducible

## Immediate Next Actions

1. Create the first CyxWiz graph for raw dataset ingestion.
2. Define the exact dataset table schema in a machine-readable file.
3. Build a small manually curated dataset of 100 examples.
4. Run a baseline model against those examples.
5. Use the failure analysis to decide the next dataset expansion.
