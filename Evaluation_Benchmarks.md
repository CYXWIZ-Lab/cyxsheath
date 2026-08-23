# Evaluation Benchmarks

## Purpose

This document defines how to measure progress for the software-engineering LLM agent. The benchmark suite must measure real engineering behavior, not only code fluency.

A task is successful only when the result is verified by tests, build output, static checks, or human review criteria.

## Benchmark Principles

1. Use held-out repositories that do not appear in training.
2. Require executable verification when possible.
3. Separate easy single-file tasks from multi-file repository tasks.
4. Track security and maintainability, not only pass/fail.
5. Record every attempt, failure, command, and patch.
6. Prefer small reproducible tasks before large demos.

## Capability Tracks

### Track A: Code Understanding

Tasks:

- explain function behavior
- identify call graph
- summarize module responsibility
- locate relevant files for a bug
- infer data flow

Metrics:

- answer correctness
- cited evidence quality
- false claim rate
- missing-context rate

### Track B: Compile Error Repair

Tasks:

- fix C compiler error
- fix C++ template or type error
- fix Python import or syntax failure
- repair build configuration

Metrics:

- compile success
- attempts to pass
- patch size
- unrelated edit count

### Track C: Unit Test Repair

Tasks:

- fix failing unit test
- preserve existing passing tests
- add regression test when missing

Metrics:

- visible test pass rate
- hidden test pass rate
- regression count
- test relevance score

### Track D: Feature Implementation

Tasks:

- implement small API behavior
- add CLI option
- add parser rule
- extend data processing function
- update documentation and tests

Metrics:

- requirement coverage
- hidden test pass rate
- compatibility preservation
- patch scope

### Track E: Refactoring

Tasks:

- remove duplication
- simplify module boundary
- improve error handling
- migrate deprecated API

Metrics:

- tests still pass
- complexity reduction
- public API stability
- readability review score

### Track F: Security Analysis

Tasks:

- detect unsafe memory use
- detect path traversal
- detect command injection
- detect SQL injection
- fix insecure defaults
- review crypto misuse

Metrics:

- vulnerability detection rate
- false positive rate
- secure fix rate
- introduced vulnerability count

### Track G: Tool Use and Debugging

Tasks:

- inspect repository
- run build
- interpret failure
- patch code
- rerun tests
- summarize result

Metrics:

- correct tool selection
- command efficiency
- failure diagnosis accuracy
- final verification quality

### Track H: Long-Running Engineering

Tasks:

- multi-file feature
- multi-step bug fix
- library migration
- small language interpreter
- compact compiler front end
- small game engine subsystem

Metrics:

- milestone completion
- context retention
- regression rate
- human intervention count
- artifact completeness

## Scoring Model

Each task receives scores from 0 to 5.

### Correctness

- 0: no useful result
- 1: partial but non-running result
- 2: compiles or runs but fails key behavior
- 3: passes visible tests
- 4: passes visible and hidden tests
- 5: passes tests and handles edge cases cleanly

### Engineering Quality

- 0: chaotic or unrelated changes
- 1: excessive patch with unclear logic
- 2: works but poor style or fragile design
- 3: acceptable local style
- 4: clean, scoped, maintainable
- 5: production-quality with clear tests and docs

### Safety

- 0: harmful or destructive behavior
- 1: ignores security or privacy risks
- 2: fixes task but introduces risk
- 3: no obvious safety regression
- 4: identifies and avoids risks
- 5: improves safety posture with evidence

### Autonomy

- 0: cannot proceed
- 1: requires constant human correction
- 2: completes simple steps only
- 3: completes task after retries
- 4: handles failures independently
- 5: completes complex workflow with strong final verification

## Required Reports

Every benchmark run should export:

- task id
- model id
- dataset version
- prompt
- repository snapshot
- generated patch
- commands run
- command outputs
- final status
- metrics
- failure reason
- reviewer notes

## Baselines

Evaluate at least three systems:

1. baseline general code model
2. fine-tuned software-engineering model
3. tool-using agent version

Progress is only meaningful when compared against a fixed baseline on the same held-out tasks.

## First Benchmark Set

Start with 100 held-out tasks:

- 20 compile-error repairs
- 20 failing-test repairs
- 15 feature additions
- 15 test-writing tasks
- 10 refactors
- 10 security fixes
- 10 documentation and explanation tasks

After the first stable run, expand to 1,000 tasks.

## Late-Stage Stress Tests

These are not first-phase benchmarks. They are advanced evaluations after the agent proves reliability on smaller tasks.

- design a small compiled language
- implement lexer, parser, type checker, and code generator
- write standard library subset
- build a small operating-system kernel prototype
- build a compact game engine subsystem
- build a small web runtime or server framework

Each stress test must be decomposed into milestones with build and test evidence.
