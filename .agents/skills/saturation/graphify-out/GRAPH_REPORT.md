# Graph Report - saturation  (2026-09-16)

## Corpus Check
- 23 files · ~29,499 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 437 nodes · 545 edges · 20 communities
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 3 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `81f1d33d`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- _comparison
- Google C# Style Guide — Agent Instructions
- grader.py
- TypeScript Style Guide — Agent Instructions
- quality_comparison.py
- General Code Style — Structural Design Rules
- Google C++ Style Guide — Agent Summary
- Java Code Style and Engineering Guide — Agent Instructions
- 3. Usage
- GraderTests
- 4. API Design
- Internal Prompt Construction Guide
- 5. Java Constructs and Practices — `JAVA-PRACTICES`
- Saturation
- Effective Go Style Guide Summary
- Google JavaScript Style Guide Summary
- reasoning_scaffold.py
- Ruby Style & Philosophy Guide Summary 💎
- Google HTML/CSS Style Guide Summary
- Google Python Style Guide Summary

## God Nodes (most connected - your core abstractions)
1. `_comparison()` - 21 edges
2. `_load_module()` - 16 edges
3. `Google C# Style Guide — Agent Instructions` - 14 edges
4. `GraderTests` - 13 edges
5. `TypeScript Style Guide — Agent Instructions` - 13 edges
6. `_events()` - 12 edges
7. `Google C++ Style Guide — Agent Summary` - 12 edges
8. `General Code Style — Structural Design Rules` - 12 edges
9. `QualityComparisonTests` - 11 edges
10. `3. Usage` - 11 edges

## Surprising Connections (you probably didn't know these)
- `4. Main` --references--> `main()`  [INFERRED]
  code_styleguides/python.md → evals/grader.py
- `4.1. Names` --references--> `add()`  [INFERRED]
  code_styleguides/dart.md → evals/test_quality_comparison_edges.py
- `Observation hook` --references--> `RunObserver`  [INFERRED]
  evals/README.md → evals/grader.py
- `add()` --calls--> `_comparison()`  [EXTRACTED]
  evals/test_quality_comparison_edges.py → evals/test_quality_comparison.py

## Import Cycles
- None detected.

## Communities (20 total, 0 thin omitted)

### Community 0 - "_comparison"
Cohesion: 0.08
Nodes (25): _comparison(), Adversarial edge coverage for the future comparison contracts., Exercise malformed inputs and every scaffold routing boundary., ScaffoldEdgeTests, _load_module(), MissingBranchTests, Focused regression checks for previously unvisited rejection branches., Keep non-mapping and non-string input boundaries executable. (+17 more)

### Community 1 - "Google C# Style Guide — Agent Instructions"
Cohesion: 0.04
Nodes (46): 10. Comments, documentation, and tests, 11. Decision examples, 12. Verification checklist, 1. Agent contract, 2. Execution procedure, 3. Source files, namespaces, and imports — `CS-SOURCE`, 4. Formatting — `CS-FORMATTING`, 5. Naming — `CS-NAMING` (+38 more)

### Community 2 - "grader.py"
Cohesion: 0.07
Nodes (38): ArgumentParser, _contains(), evaluate_events(), evaluate_observation(), format_result(), _internal_artifact(), load_observation(), main() (+30 more)

### Community 3 - "TypeScript Style Guide — Agent Instructions"
Cohesion: 0.05
Nodes (41): 10. Few-Shot Decision Examples, 11. Verification and Output Contract, 1. Agent Contract, 2. Execution Procedure, 3. Source Files, Modules, Imports, and Exports, 4. Declarations, Formatting, and Control Flow, 5. Classes, Visibility, and Errors, 6. Type System and Runtime Boundaries (+33 more)

### Community 4 - "quality_comparison.py"
Cohesion: 0.13
Nodes (30): _bootstrap_interval(), evaluate_comparison(), _nonempty(), _observations(), _percentile(), Any, Versioned, dependency-free comparison of delegated task outcomes., Validate the exact quality-comparison-v1 contract. Args: value: A candidate… (+22 more)

### Community 5 - "General Code Style — Structural Design Rules"
Cohesion: 0.07
Nodes (27): 1. Size limits, 2. Coupling, 3. Cohesion and encapsulation, 4. First-Class Collections, 5. Duplication, 6. Readability and simplicity, 7. Documentation, Agent application protocol (+19 more)

### Community 6 - "Google C++ Style Guide — Agent Summary"
Cohesion: 0.08
Nodes (24): 10. Verification checklist, 1. Language version and file names, 2. Naming, 3. Headers and dependencies, 4. Formatting, 5. Classes, structs, and operators, 6. Functions and APIs, 7. Scope, lifetime, and ownership (+16 more)

### Community 7 - "Java Code Style and Engineering Guide — Agent Instructions"
Cohesion: 0.08
Nodes (25): 1. Agent Contract, 2. Execution Procedure, 3. Source Files and Imports — `JAVA-SOURCE`, 4. Formatting Rules — `JAVA-FORMATTING`, 6. Naming Rules — `JAVA-NAMING`, 7. Javadoc Rules — `JAVA-JAVADOC`, 8. Few-shot Examples, 9. Verification and Output Contract (+17 more)

### Community 8 - "3. Usage"
Cohesion: 0.09
Nodes (21): 1.1. Identifiers, 1.2. Ordering, 1.3. Formatting, 1. Style, 2.1. Comments, 2.2. Doc Comments, 2.3. Markdown, 2.4. Writing (+13 more)

### Community 9 - "GraderTests"
Cohesion: 0.14
Nodes (7): _events(), GraderTests, ObserverTests, Focused tests for the in-memory saturation evaluator., Return a valid observation for two isolated assignments., Verify that runtime observations stay detached and in memory., Verify useful runtime invariants without trace persistence.

### Community 10 - "4. API Design"
Cohesion: 0.13
Nodes (16): 4.1. Names, 4.2. Libraries, 4.3. Classes and Mixins, 4.4. Constructors, 4.5. Members, 4.6. Types, 4.7. Parameters, 4.8. Equality (+8 more)

### Community 11 - "Internal Prompt Construction Guide"
Cohesion: 0.17
Nodes (8): Composition rules, Failure behavior, Internal Prompt Construction Guide, Prompt shape, Purpose, Quality actions, User boundary, Workspace and handoff

### Community 12 - "5. Java Constructs and Practices — `JAVA-PRACTICES`"
Cohesion: 0.15
Nodes (13): 5. Java Constructs and Practices — `JAVA-PRACTICES`, Annotations and comments — `JAVA-ANNOTATIONS`, Collections and streams — `JAVA-COLLECTIONS`, Complex private methods and collections — `JAVA-DESIGN-COLLECTION`, Concurrency — `JAVA-CONCURRENCY`, Control flow — `JAVA-CONTROL-FLOW`, Controller responsibility — `JAVA-DESIGN-BOUNDARY`, Declarations and initialization — `JAVA-DECLARATIONS` (+5 more)

### Community 13 - "Saturation"
Cohesion: 0.18
Nodes (10): Context and trust, Core promise, Evaluation boundary, Final delivery, Lifecycle, Persistence boundary, Quality actions, Safety and escalation (+2 more)

### Community 14 - "Effective Go Style Guide Summary"
Cohesion: 0.20
Nodes (9): 1. Formatting, 2. Naming, 3. Control Structures, 4. Functions, 5. Data, 6. Interfaces, 7. Concurrency, 8. Errors (+1 more)

### Community 15 - "Google JavaScript Style Guide Summary"
Cohesion: 0.22
Nodes (8): 1. Source File Basics, 2. Source File Structure, 3. Formatting, 4. Language Features, 5. Disallowed Features, 6. Naming, 7. JSDoc, Google JavaScript Style Guide Summary

### Community 16 - "reasoning_scaffold.py"
Cohesion: 0.25
Nodes (8): classify_activation(), Any, Deterministic routing for a bounded, non-private reasoning scaffold., Return the bounded prompt text for an activated scaffold. Returns: English…, Validate the exact, evidence-backed classifier inputs., Select direct, scaffold, or escalation routing from fixed signals. Args:…, scaffold_instructions(), _validate_inputs()

### Community 17 - "Ruby Style & Philosophy Guide Summary 💎"
Cohesion: 0.25
Nodes (7): 1. Philosophy & The Ruby Way ✨, 2. Language Rules & Idioms 🛠️, 3. Style & Formatting 📐, 4. Naming Conventions 📛, 5. Ecosystem & Developer Workflow ⚙️, Ruby Style & Philosophy Guide Summary 💎, Sources

### Community 18 - "Google HTML/CSS Style Guide Summary"
Cohesion: 0.29
Nodes (6): 1. General Rules, 2. HTML Style Rules, 3. HTML Formatting Rules, 4. CSS Style Rules, 5. CSS Formatting Rules, Google HTML/CSS Style Guide Summary

### Community 19 - "Google Python Style Guide Summary"
Cohesion: 0.33
Nodes (5): 1. Python Language Rules, 2. Python Style Rules, 3. Naming, 4. Main, Google Python Style Guide Summary

## Knowledge Gaps
- **210 isolated node(s):** `Core promise`, `Lifecycle`, `Persistence boundary`, `Context and trust`, `Scoped subagents` (+205 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 283 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Google C# Style Guide — Agent Instructions` connect `Google C# Style Guide — Agent Instructions` to `Internal Prompt Construction Guide`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Why does `TypeScript Style Guide — Agent Instructions` connect `TypeScript Style Guide — Agent Instructions` to `Internal Prompt Construction Guide`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **Why does `Java Code Style and Engineering Guide — Agent Instructions` connect `Java Code Style and Engineering Guide — Agent Instructions` to `Internal Prompt Construction Guide`, `5. Java Constructs and Practices — `JAVA-PRACTICES``?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **What connects `Core promise`, `Lifecycle`, `Persistence boundary` to the rest of the system?**
  _210 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `_comparison` be split into smaller, more focused modules?**
  _Cohesion score 0.07908163265306123 - nodes in this community are weakly interconnected._
- **Should `Google C# Style Guide — Agent Instructions` be split into smaller, more focused modules?**
  _Cohesion score 0.043478260869565216 - nodes in this community are weakly interconnected._
- **Should `grader.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06871035940803383 - nodes in this community are weakly interconnected._