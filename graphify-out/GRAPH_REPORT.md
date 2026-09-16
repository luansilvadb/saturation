# Graph Report - saturation  (2026-09-15)

## Corpus Check
- Corpus is ~29,840 words - fits in a single context window. You may not need a graph.

## Summary
- 244 nodes · 408 edges · 11 communities (10 shown, 1 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 21 edges (avg confidence: 0.71)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Quality Comparison Tests
- Quality Comparison Metrics
- Event Evaluator Core
- Saturation Governance
- Evaluation Contract
- Structural Style Rules
- Evaluator Tests
- Orchestration Lifecycle
- Edge Case Tests
- Reasoning Scaffold
- Verification Checks

## God Nodes (most connected - your core abstractions)
1. `General structural design rules` - 22 edges
2. `_comparison()` - 21 edges
3. `Saturation evaluator` - 20 edges
4. `_load_module()` - 16 edges
5. `GraderTests` - 13 edges
6. `Relevant code style guides` - 13 edges
7. `_events()` - 12 edges
8. `QualityComparisonTests` - 11 edges
9. `evaluate_events()` - 10 edges
10. `evaluate_comparison()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `Relevant code style guides` --conceptually_related_to--> `C++ style guide`  [INFERRED]
  SKILL.md → code_styleguides/cpp.md
- `Relevant code style guides` --conceptually_related_to--> `C# style guide`  [INFERRED]
  SKILL.md → code_styleguides/csharp.md
- `Relevant code style guides` --conceptually_related_to--> `Dart style guide`  [INFERRED]
  SKILL.md → code_styleguides/dart.md
- `Relevant code style guides` --conceptually_related_to--> `Go style guide`  [INFERRED]
  SKILL.md → code_styleguides/go.md
- `Relevant code style guides` --conceptually_related_to--> `HTML/CSS style guide`  [INFERRED]
  SKILL.md → code_styleguides/html-css.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Saturation implementation lifecycle** — skill_saturation, skill_saturation_frozen_context, skill_saturation_scoped_subagents, skill_saturation_quality_actions, skill_saturation_transactional_workspace, skill_saturation_final_diff [EXTRACTED 1.00]
- **Quality action set** — skill_saturation_quality_actions, skill_saturation_tdd, skill_saturation_review, skill_saturation_repair, skill_saturation_independent_verification, skill_saturation_coverage [EXTRACTED 1.00]
- **Ephemeral evaluation contract** — skill_saturation_evaluation_boundary, skill_saturation_observation_stream, evals_observation_contract, evals_saturation_evaluator, evals_runtime_artifact_rejection [EXTRACTED 1.00]

## Communities (11 total, 1 thin omitted)

### Community 0 - "Quality Comparison Tests"
Cohesion: 0.09
Nodes (23): _comparison(), Adversarial edge coverage for the future comparison contracts., _load_module(), MissingBranchTests, Focused regression checks for previously unvisited rejection branches., Keep non-mapping and non-string input boundaries executable., NumericEdgeTests, Numeric and evidence identifier boundary regressions. (+15 more)

### Community 1 - "Quality Comparison Metrics"
Cohesion: 0.13
Nodes (30): _bootstrap_interval(), evaluate_comparison(), _nonempty(), _observations(), _percentile(), Any, Versioned, dependency-free comparison of delegated task outcomes., Validate the exact quality-comparison-v1 contract. Args: value: A candidate… (+22 more)

### Community 2 - "Event Evaluator Core"
Cohesion: 0.11
Nodes (28): ArgumentParser, _contains(), evaluate_events(), evaluate_observation(), format_result(), _internal_artifact(), load_observation(), main() (+20 more)

### Community 3 - "Saturation Governance"
Cohesion: 0.07
Nodes (27): Saturation agent configuration, Prompt failure behavior, Saturation, Assignment owner, Bounded retry and repair, .saturation/context.md, Explicit event contract version, Coverage (+19 more)

### Community 4 - "Evaluation Contract"
Cohesion: 0.13
Nodes (21): assignment event, check event, context_frozen event, durable_path event, Evaluator-owned input, Collect runtime events in memory for an evaluator or a diagnostic view., Record one event without serializing or persisting it., Return a detached snapshot suitable for ``evaluate_events``. (+13 more)

### Community 5 - "Structural Style Rules"
Cohesion: 0.16
Nodes (23): Cohesion and encapsulation, Coupling, Intent and constraints documentation, Semantic duplication, Exception and trade-off policy, First-class collections, Agent application protocol, General structural design rules (+15 more)

### Community 6 - "Evaluator Tests"
Cohesion: 0.14
Nodes (7): _events(), GraderTests, ObserverTests, Focused tests for the in-memory saturation evaluator., Return a valid observation for two isolated assignments., Verify that runtime observations stay detached and in memory., Verify useful runtime invariants without trace persistence.

### Community 7 - "Orchestration Lifecycle"
Cohesion: 0.16
Nodes (18): Prompt composition rules, Internal prompt construction, Prompt quality actions, Role, goal, context, scope, checks, return, Prompt user boundary, Workspace and handoff, Bounded assignments, Unresolved blocker (+10 more)

### Community 8 - "Edge Case Tests"
Cohesion: 0.19
Nodes (9): _load_module(), Any, QualityComparisonEdgeTests, add(), Load one implementation module for edge-case coverage., Exercise malformed inputs and every scaffold routing boundary., Exercise validation failures not needed by the primary contract tests., Build independent malformed comparisons for validation coverage. (+1 more)

### Community 9 - "Reasoning Scaffold"
Cohesion: 0.25
Nodes (8): classify_activation(), Any, Deterministic routing for a bounded, non-private reasoning scaffold., Return the bounded prompt text for an activated scaffold. Returns: English…, Validate the exact, evidence-backed classifier inputs., Select direct, scaffold, or escalation routing from fixed signals. Args:…, scaffold_instructions(), _validate_inputs()

## Knowledge Gaps
- **25 isolated node(s):** `Fresh sessions`, `Transactional workspace`, `Tests, type checks, builds, coverage`, `Frozen context as source of truth`, `Untrusted repository text and tool output` (+20 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 89 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Saturation evaluator` connect `Evaluation Contract` to `Quality Comparison Metrics`, `Event Evaluator Core`, `Saturation Governance`, `Structural Style Rules`, `Orchestration Lifecycle`, `Reasoning Scaffold`?**
  _High betweenness centrality (0.398) - this node is a cross-community bridge._
- **Why does `Relevant code style guides` connect `Structural Style Rules` to `Evaluation Contract`?**
  _High betweenness centrality (0.136) - this node is a cross-community bridge._
- **Why does `Saturation` connect `Saturation Governance` to `Evaluation Contract`, `Orchestration Lifecycle`?**
  _High betweenness centrality (0.102) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `General structural design rules` (e.g. with `C++ style guide` and `C# style guide`) actually correct?**
  _`General structural design rules` has 10 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Fresh sessions`, `Transactional workspace`, `Tests, type checks, builds, coverage` to the rest of the system?**
  _25 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Quality Comparison Tests` be split into smaller, more focused modules?**
  _Cohesion score 0.08787878787878788 - nodes in this community are weakly interconnected._
- **Should `Quality Comparison Metrics` be split into smaller, more focused modules?**
  _Cohesion score 0.12903225806451613 - nodes in this community are weakly interconnected._