# General Code Style — Structural Design Rules

Cross-language design rules: size, coupling, cohesion, encapsulation,
duplication, and documentation. A language guide owns formatting, naming, APIs,
and language idioms, and decides inside that domain.

## Rule priority — `GEN-PRECEDENCE`

Resolve a conflict at the highest level that names it:

1. Explicit user requirements and acceptance criteria.
2. Developer and system instructions, and the frozen cycle context.
3. Environment, compatibility, and generated-code boundaries.
4. The convention of the code being modified. It governs the lines you touch and
   becomes a project-wide rule only when the task says so.
5. These guides: this module for design structure, the language guide for
   formatting, naming, APIs, and idioms.
6. Personal preference, which never decides a review.

## Normative language

- **MUST** is a requirement. A violation is a defect.
- **SHOULD** is the default choice. Deviate with a stated reason.
- **MAY** is a permitted choice.

Every MUST and SHOULD carries a rule ID of the form `<MODULE>-<TOPIC>`; cite it
when you apply, deviate from, or report the rule. MAY carries no ID.

A numeric limit is a diagnostic signal, not a refactoring command. Cohesion,
coupling, behavior, and the cost of the change decide the action. **MUST** record
a deviation from a MUST with its rule ID, location, reason, and impact
(`GEN-DEVIATION`).

## 1. Size

### Class or module size — `GEN-SIZE-CLASS`

- **SHOULD** keep a class or cohesive module under approximately 200 lines.
- Treat size as a stronger signal when the unit also has high coupling, several
  reasons to change, or weak cohesion.
- **MUST NOT** split a unit only to satisfy a line count. An extracted unit needs
  a name, a responsibility, a boundary, and its own reason to change.

### Method or function size — `GEN-SIZE-METHOD`

- **SHOULD** keep a method or function under approximately 30 lines. A longer
  unit is a signal to look for several responsibilities, deep nesting, or an
  unnamed concept.
- Prefer extracting a well-named operation over a comment that narrates a block.
- **MAY** stay above the limit for a cohesive algorithm whose invariants or error
  handling would become less visible if split.

## 2. Coupling — `GEN-COUPLING`

- **SHOULD** keep constructor and field dependencies under approximately 7
  distinct runtime collaborators per class or module.
- Count the collaborators needed to construct or operate the unit: injected
  services, gateways, repositories, policies, clients, and similar domain
  dependencies.
- When the signal is present, map each dependency to the responsibility that uses
  it, and extract a collaborator only when the cluster changes together and can be
  understood and tested on its own.
- **MUST NOT** hide coupling behind a pass-through `Facade`, `Manager`, or
  `Helper` that moves fields without creating a boundary.

## 3. Encapsulation

### Behavior ownership — `GEN-ENCAPSULATION`

- **SHOULD** keep behavior with the data it operates on. An operation that
  primarily reads another object's state belongs to that object's concept.
- **MUST NOT** make a domain decision by traversing another object's internals
  through several accessors. That is the Feature Envy signal.
- **MAY** traverse accessors to project a DTO, serialize, map persistence, serve
  a read model, or cross an adapter boundary: those translate data instead of
  deciding domain behavior.

## 4. Collections — `GEN-COLLECTION`

- **SHOULD** give a named abstraction to a collection that carries domain
  invariants, semantic queries, or repeated filtering, mapping, and reducing
  across call sites.
- **MAY** keep a raw collection for one local iteration with no domain behavior.
- **MUST NOT** wrap a raw collection only to rename `map`, `filter`, or `len`. The
  abstraction encapsulates the iteration, exposes semantic operations, and keeps
  mutation and representation rules at the boundary.

## 5. Duplication — `GEN-DUPLICATION`

- **MUST NOT** duplicate materially identical domain behavior across call sites.
  Two blocks are duplicates when they express the same intent, even when names or
  parameters differ.
- Compare semantics, validation, error handling, side effects, and expected
  change reasons before extracting. Similar-looking code with different contracts
  stays separate.
- Choose the strategy from the relationship: a shared method for local
  duplication, a domain class or value object across units, and `GEN-COLLECTION`
  when the duplication is collection behavior.
- **MAY** keep a small explicit duplication when the shared version would need
  flags, conditionals, or a misleading name.

## 6. Documentation — `GEN-DOCUMENTATION`

- **SHOULD** document why a non-obvious decision is necessary, with its
  constraint, trade-off, or invariant.
- **MUST NOT** restate in a comment what the code already says. Prefer a better
  name or a smaller operation.
