# Java Style Guide

Target: Java 17 or the version the build declares, whichever is higher. Apply with
`general.md`, which defines the normative markers and the cross-language rules.

### Source files — `JAVA-SOURCE`

- **MUST** encode source files as UTF-8 and use ASCII spaces, never tabs, as whitespace.
- **MUST** name a file after its single case-sensitive top-level type plus `.java`.
- **MUST** keep the section order license, package, imports, one top-level type.
- **MUST** declare a package in every ordinary source file.
- **MUST NOT** use wildcard imports, module imports, or wrapped import declarations.
- **MUST** put static imports in one group before non-static imports and sort each group
  in ASCII order, separating the groups with one blank line.
- **MUST** import a static nested class with a normal import.
- **MUST** keep overloads contiguous, with no unrelated member between them.
- **MUST** order module directive blocks as `requires`, `exports`, `opens`, `uses`, `provides`.
- **SHOULD** order class members by a logical, explainable rule.

### Formatting — `JAVA-FORMATTING`

- **MUST** use braces for every control-structure body, including empty and
  single-statement bodies.
- **MUST** write one statement per line.
- **SHOULD** keep grouping parentheses that make precedence or intent clearer.
- **MUST NOT** reformat unrelated code; run the repository formatter scoped to the files
  you changed.

### Control flow — `JAVA-CONTROL-FLOW`

- **SHOULD** keep control flow shallow and extract a named predicate when nested branches
  obscure the business rule.
- **MUST** make every switch exhaustive, adding `default` when the cases do not cover
  every value.
- **MUST** use `->` syntax for switch expressions.
- **MUST** comment intentional or possible fall-through in a colon-style switch.

### Declarations — `JAVA-DECLARATIONS`

- **MUST** declare one variable per declaration, except in a `for` header.
- **SHOULD** declare locals close to their first use and initialize them at declaration.
- **SHOULD** prefer `final` fields and immutable locals without adding `final`
  mechanically.
- **SHOULD** use `var` only when the initializer makes the type clear, and an explicit type
  when it documents an ambiguous numeric, generic, or nullable inference.
- **MUST** put array brackets with the type: `String[] args`, not `String args[]`.
- **MUST** order modifiers as `public protected private abstract default static final sealed
  non-sealed transient volatile synchronized native strictfp`.

### Types and API boundaries — `JAVA-API`

- **MUST** keep implementation fields private and avoid exposing mutable internal state
  through public fields or accessors.
- **SHOULD** prefer immutable value objects, `final` fields, and records for transparent
  value carriers, and defensively copy mutable components.
- **SHOULD** return interface types and unmodifiable views or copies when callers must not
  mutate internal state.
- **MUST** preserve ordering, duplicate, and null-element semantics when changing a
  collection representation.
- **MUST** follow the repository's nullability contract and make accepted and rejected
  `null` values explicit at public boundaries.
- **MUST** preserve the names, visibility, annotations, constructors, and schema that
  serialization or reflection depends on, absent an explicit migration.
- **SHOULD** use `Optional` for an absent return value where the repository does, never
  returning `null` where an `Optional` is promised and never as a field, parameter, or
  element type.

### Collections and streams — `JAVA-COLLECTIONS`

- **SHOULD** use a stream for a short, side-effect-free transformation whose stages read
  naturally, and a loop for stateful, multi-step, exceptionful, or debugged logic.
- **MUST NOT** mutate external or shared state from a stream pipeline.
- **MUST** preserve encounter order and short-circuit behavior.
- **MUST NOT** introduce `parallelStream()` without a requirement and evidence that it
  helps.
- **SHOULD** give a repeated domain query a semantic name or a domain type.

### Exceptions and resources — `JAVA-ERRORS`

- **MUST** catch the most specific exception that can be handled; catch `Exception`,
  `Throwable`, or `Error` only at a deliberate boundary with a documented reason.
- **MUST** log, rethrow, translate, or otherwise handle every caught exception, preserving
  the original cause when translating and explaining in a comment when no action is
  correct.
- **SHOULD** log where the failure can be acted on, not at every layer, and never include
  secrets in messages.
- **MUST** use try-with-resources for `AutoCloseable` resources the method owns and not
  close resources whose ownership was transferred or is framework-managed.
- **MUST NOT** return or throw from a `finally` block.
- **MUST** preserve interruption when catching `InterruptedException`, by rethrowing it,
  delegating cancellation, or restoring the interrupt status.

### Concurrency — `JAVA-CONCURRENCY`

- **SHOULD** prefer immutable or thread-confined state and `java.util.concurrent`
  abstractions over ad hoc coordination.
- **MUST** make visibility and atomicity explicit for shared mutable state and use a
  primitive designed for compound updates.
- **SHOULD** synchronize on a private, stable lock rather than `this`, a public object, or
  a string literal.
- **MUST** define ownership and lifecycle for executors, schedulers, and threads; no
  unbounded or per-call executor without a documented bound and shutdown strategy.
- **SHOULD** document thread-safety, blocking, interruption, and cancellation behavior of
  concurrent public APIs.

### Tests — `JAVA-TESTING`

- **MUST** make tests deterministic and assert observable behavior, including boundary,
  failure, and compatibility cases.
- **SHOULD** inject a fake, stub, or clock instead of sleeps, wall-clock timing, network
  calls, or uncontrolled randomness.
- **SHOULD** use a reproducible seed and report it on failure when randomness is
  unavoidable.
- **MUST NOT** use sleeps as the primary synchronization mechanism; use awaitility,
  latches, or virtual time with bounded timeouts.
- **SHOULD** use parameterized tests for a matrix of equivalent cases and keep each test
  focused on one behavior.
- **SHOULD** keep fixtures readable and local and never weaken production code for a test.

### Annotations and comments — `JAVA-ANNOTATIONS`

- **MUST** place type-use annotations immediately before the annotated type.
- **MUST** place class, package, module, method, and constructor annotations immediately
  after their Javadoc, one per line.
- **MUST** place field annotations immediately after the field's Javadoc.
- **MUST** use `@Override` whenever it is legal, including interface implementations and
  declared record accessors.
- **MUST** keep `@SuppressWarnings` at the narrowest useful scope and explain the invariant
  that makes it safe.
- **MUST** write temporary work as `TODO: <resource> - <explanation>`, linking a bug
  reference rather than a person or team.
- **MUST** qualify static members with their declaring class, as in `Foo.aStaticMethod()`.
- **MUST NOT** override `Object.finalize`.

### Naming — `JAVA-NAMING`

- **MUST** use lowercase letters and digits for package and module names.
- **MUST** use `UpperCamelCase` for classes, interfaces, enums, and records.
- **MUST** use `lowerCamelCase` for methods, fields, parameters, and local variables.
- **MUST** end a test class name with `Test`.
- **MUST** use `UPPER_SNAKE_CASE` only for `static final` fields that are deeply immutable
  and whose methods have no detectable side effects; keep every other field, including
  a `static final` reference to mutable state, in `lowerCamelCase`.

  ```java
  private static final Duration DEFAULT_TIMEOUT = Duration.ofSeconds(5);
  private final String customerId;
  ```

- **SHOULD** use `UPPER_SNAKE_CASE` for enum constants unless a test or serialization
  contract overrides it.
- **MAY** use underscores between logical parts of a JUnit test method name.
- **MUST** use ASCII letters and digits in identifiers, with no prefixes or suffixes such as
  `mName`, `name_`, or `s_name`.
- **MUST** name a type variable with one capital letter and an optional numeral (`T`, `E`,
  `T2`) or a class-style name ending in `T`.
- **SHOULD** treat acronyms as words: `XmlHttpRequest`, `customerId`, `supportsIpv6OnIos`.

### Javadoc — `JAVA-JAVADOC`

- **MUST** use the Javadoc form supported by the repository's compiler and tooling.
- **MUST** start with a brief, capitalized, punctuated summary fragment.
- **MUST** order core block tags as `@param`, `@return`, `@throws`, `@deprecated`, with a
  non-empty description for every tag used.
- **SHOULD** document public and protected types, members, and record components whose
  contract is not obvious from the signature; an override may inherit documentation.
- **SHOULD** add `@param`, `@return`, and `@throws` only where they add contract
  information.
- **MUST** pair `@Deprecated` with a `@deprecated` description naming the replacement or
  removal reason.
- **SHOULD** use `{@link ...}` for navigable references and `{@code ...}` for code and
  literals.
- **SHOULD** state purpose or behavior in Javadoc rather than in an implementation comment.
