# Research Thesis: A Software-Engineering LLM Agent Built With CyxWiz

## Abstract

This research proposes a specialized LLM agent for software engineering, focused first on C, C++, and Python. The agent is designed to move beyond isolated code generation and toward complete engineering behavior: repository understanding, planning, implementation, testing, debugging, review, documentation, and security-aware decision making.

CyxWiz Engine is used as the experiment platform. It provides visual data pipelines, preprocessing graphs, model training workflows, evaluation graphs, artifact export, checkpointing, and experiment visualization. The research goal is to produce measurable evidence that an LLM agent can perform increasingly complex software engineering tasks with reliability, safety, and reproducibility.

## Motivation

Software engineering is a strong testbed for machine intelligence because it requires several cognitive skills at the same time:

- symbolic reasoning
- language understanding
- tool use
- mathematics
- systems thinking
- debugging
- design tradeoffs
- security awareness
- long-term planning
- empirical validation

A model that can build and maintain nontrivial software must reason across requirements, source code, tests, runtime behavior, user intent, and failure evidence. This makes software engineering a disciplined and measurable domain for studying advanced agentic intelligence.

## Thesis Statement

A specialized LLM agent trained and evaluated on software-engineering workflows can become substantially more useful than a general code-generation model when it is trained not only on code, but also on engineering process: task decomposition, evidence gathering, test-driven correction, security review, and reproducible verification.

## Mission

Build a software-engineering LLM agent that can receive a task and execute a complete engineering loop:

1. understand the repository and user goal
2. inspect relevant files and tests
3. propose or infer a small plan
4. implement the change
5. run targeted verification
6. debug failures
7. document the final result
8. preserve safety and security constraints

## Initial Scope

The first research scope is deliberately narrow:

- Languages: C, C++, Python
- Build systems: CMake, Make, Python packaging, common compiler flows
- Task types: bug fixes, feature additions, tests, refactors, documentation updates, security reviews
- Runtime behavior: compile errors, test failures, logs, crashes, memory issues
- Repositories: high-quality open-source projects with clean history, issues, tests, and review artifacts

Out of scope for the first phase:

- full autonomous operating system creation
- unrestricted internet action
- malware generation
- unsandboxed destructive actions
- unverifiable AGI claims
- large multi-month autonomous tasks without intermediate measurable milestones

## Research Questions

1. Can a model trained on engineering process outperform a model trained mainly on source code completion?
2. Which data types most improve software-engineering behavior: commits, issues, tests, compiler logs, reviews, security fixes, or documentation?
3. Can a reasoning loop improve reliability compared with direct answer generation?
4. Can CyxWiz graphs provide reproducible training and evaluation pipelines for software-agent research?
5. What benchmarks best measure practical engineering capability rather than superficial code fluency?
6. How can safety policies be made concrete enough to guide an autonomous software agent?

## Hypotheses

H1: A model trained on task, evidence, patch, test, and review traces will outperform a code-only baseline on repository-level tasks.

H2: Explicit reasoning-process data will improve debugging and correction behavior, especially after failed tests.

H3: Security-fix datasets and negative examples will improve the agent's ability to detect and avoid vulnerable code patterns.

H4: A graph-based experiment platform such as CyxWiz can make the research more reproducible by preserving dataset versions, preprocessing steps, training configuration, metrics, and exported artifacts.

## Capability Model

The agent should be evaluated as a system of capabilities, not as one vague intelligence score.

### 1. Code Understanding

The agent reads source files, tests, build scripts, and documentation to understand behavior and project structure.

### 2. Planning

The agent decomposes a task into small engineering steps and identifies the files and tests most likely to matter.

### 3. Implementation

The agent writes scoped changes that follow local style and existing architecture.

### 4. Debugging

The agent interprets compile errors, runtime logs, test failures, stack traces, and incorrect outputs, then makes targeted corrections.

### 5. Testing

The agent selects or creates tests that prove the intended behavior without overfitting to implementation details.

### 6. Refactoring

The agent improves structure only when it reduces real complexity, duplication, risk, or maintenance cost.

### 7. Security Review

The agent detects unsafe patterns, insecure defaults, injection risks, memory hazards, unsafe file handling, and dangerous tool behavior.

### 8. Documentation

The agent explains changes, constraints, APIs, and usage in a way that helps future engineers.

### 9. Long-Running Autonomy

The agent can continue through multiple inspect, edit, build, test, and repair cycles while preserving context and avoiding unrelated damage.

## Thinking Base

The project distinguishes knowledge from thinking.

Knowledge base is the data: source code, docs, tests, commits, issues, build logs, bug reports, security advisories, and engineering books or notes.

Thinking base is the method for using the data. The first thinking principle is a binary engineering loop: yes/no, true/false, works/fails, supported/unsupported. The model should learn to move between proof and application:

1. state the expected behavior
2. inspect evidence
3. decide whether the current code satisfies the expectation
4. make the smallest correction
5. verify with tests or runtime evidence
6. repeat until the claim is supported

This converts broad reasoning into observable engineering behavior.

## Moral and Safety Foundation

The project should include a moral foundation, but the enforceable system must be written as concrete policies.

A religious or philosophical source can inform values, but the agent's operating rules must be explicit and testable:

- do not create malware or tools for unauthorized access
- do not hide vulnerabilities or bypass user consent
- prefer defensive security work
- preserve user data and privacy
- avoid destructive actions unless explicitly authorized
- log important actions and decisions
- refuse requests that enable harm
- sandbox risky execution
- report uncertainty honestly
- keep humans in control of high-impact actions

## Role of CyxWiz Engine

CyxWiz is the research execution layer. It should provide:

- dataset ingestion from repositories, issues, commits, logs, and benchmark files
- preprocessing nodes for cleaning, deduplication, labeling, chunking, tokenization, and splitting
- training graphs for baseline and fine-tuned models
- evaluation graphs for task benchmarks
- export nodes for clean datasets, metrics, and artifacts
- visual experiment tracking
- checkpoint management
- reproducibility through saved graph configuration

## Expected Contributions

The research should produce:

1. a structured software-engineering dataset schema
2. CyxWiz graph templates for training and evaluation
3. a capability-based benchmark suite
4. a baseline model and improved agent model
5. safety and refusal policy for software agents
6. reproducible experiment artifacts
7. thesis-quality analysis of what improves engineering behavior

## Success Criteria

The project is successful when the agent can repeatedly complete held-out software-engineering tasks with evidence:

- code compiles
- tests pass
- hidden tests pass
- changes are scoped
- no severe security regression is introduced
- output is documented
- failures are analyzed instead of ignored

Late-stage stress tests may include designing a small programming language, building a compiler prototype, creating a small runtime, or implementing a compact game engine. These should be evaluated as engineering benchmarks, not used as unsupported AGI claims.

## Limitations

The project should avoid claiming full autonomy, bug-free output, or AGI without reproducible evidence. Software can be tested deeply, but not proven universally safe in every environment. The research must distinguish measured capability from aspiration.
