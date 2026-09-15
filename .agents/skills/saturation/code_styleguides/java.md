# Java Code Style and Engineering Guide — Agent Instructions

Use this module whenever you create, edit, review, or refactor Java code. It is
an operational instruction block, not only a reference list: understand the
task, select the relevant rules, apply them to the smallest useful scope,
verify the result, and report what was actually verified.

This module governs Java syntax, APIs, idioms, and Java-specific design signals.
Use `general.md` for cross-language structural rules and
`prompting.md` for prompt construction. Neither module overrides
explicit user requirements, repository constraints, or the supported Java
version.

## 1. Agent Contract

### Role

Act as a careful Java engineer and code reviewer. Produce code that is easy to
read, safe to change, consistent with the repository, and conformant with the
[Google Java Style Guide](https://google.github.io/styleguide/javaguide.html).

### Objective

For every Java change:

1. Preserve the requested behavior and public contracts.
2. Apply the relevant mandatory rules in this document to all new or modified
   code.
3. Keep the diff focused; do not reformat unrelated code.
4. Run the most relevant available formatting, static-analysis, build, and test
   checks.
5. Report changes, checks, assumptions, deviations, and unresolved risks
   accurately.

### Context to inspect

Before editing, inspect only the context relevant to the task:

-   The Java version declared by the build (`pom.xml`, `build.gradle`, or
   equivalent).
-   The effective compiler settings, including `--release`, source/target
    compatibility, preview flags, toolchain, and annotation processors.
-   Existing Java files near the change, including tests, public APIs, and
    serialization or reflection boundaries.
-   Repository formatter, linter, compiler, test, and API-compatibility
    configuration.
-   The requested behavior, compatibility requirements, and local conventions.

Use repository context to resolve harmless stylistic choices. Do not infer a
new project convention from a single exceptional file.

### Applicability and boundaries

-   **MUST** identify generated, vendored, migrated, or formatter-owned files
    before editing. Change the source or template that owns generated output;
    do not hand-edit generated or third-party code unless the task explicitly
    requires it.
-   **MUST** apply this guide to new code and modified lines. Do not turn a
    focused change into a legacy-code cleanup or a repository-wide formatting
    pass.
-   **SHOULD** select only the rule IDs relevant to the assigned paths and
    objective when this module is injected into an operational prompt. A
    threshold or recommendation is a decision signal, not an automatic
    refactoring command.
-   **MUST** ask for concise decisions, checks, assumptions, and observable
    evidence in an operational prompt; never request or store hidden
    chain-of-thought or a private scratchpad.

### Rule priority

Resolve conflicts in this order:

1. Explicit user requirements and acceptance criteria.
2. Required project constraints, compatibility targets, and generated-code
   boundaries.
3. The mandatory Google Java rules and applicable engineering practices in this
   document.
4. Established local conventions that do not conflict with the levels above.
5. Personal preference.

When a higher-priority constraint prevents a Google Java rule, preserve the
required behavior, limit the deviation to the smallest useful scope, and
report the deviation. Never hide a conflict by silently reformatting unrelated
files.

### Normative language

-   **MUST:** Required. Treat a violation as a defect unless a documented
    higher-priority constraint applies.
-   **SHOULD:** The default choice. Use another choice only when the context
    provides a clear reason and the choice remains readable and consistent.
-   **MAY:** Permitted choice. Prefer the option that keeps the surrounding code
    easiest to understand.
-   **BLOCK:** Stop the current phase when a required prerequisite, scope
    boundary, or compatibility fact is missing. Record the reason and
    escalate rather than guessing.

## 2. Execution Procedure

Follow this sequence for each task. If a step cannot be completed, record why
and continue only when doing so is safe.

### Before editing

1. Identify the Java files, public APIs, tests, generated boundaries, and build
   configuration in scope.
2. Confirm the effective Java language level, formatter, linter, compiler, and
   test commands for the affected module.
3. Separate required behavior from optional cleanup. Record compatibility
   constraints for source, binary, serialization, reflection, and threading
   contracts when they apply.
4. Select the rule IDs that matter to the change and identify any existing
   deviations that must be preserved.
5. Choose the smallest implementation that satisfies the request.

### While editing

1. Preserve behavior unless the task explicitly requests a behavior change.
2. Apply this guide and the structural design rules in `general.md` to all
   new and modified code.
3. Use only language features, APIs, and compiler flags supported by the
   declared compatibility target. Do not introduce preview or incubator
   features without explicit project support.
4. Keep overloads, related members, and public documentation coherent.
5. Prefer a clear local variable or extracted method over clever wrapping.
   See Section 5, "Structural design (Java)," for concrete extraction signals.
6. Keep comments focused on intent, constraints, or non-obvious behavior.
7. Check relevant structural signals from `general.md`; do not refactor
   solely to satisfy an approximate threshold.

### After editing

1. Run the configured formatter on the affected files. If it would rewrite
   unrelated code, use a scoped invocation or record the reason it was skipped.
2. Run focused compilation, static analysis, and tests; expand regression
   coverage when the change affects shared or public behavior.
3. When applicable, check source/binary API compatibility, serialization,
   reflection, concurrency, and resource-lifecycle behavior.
4. Inspect the final diff for accidental reformatting, missing imports,
   unhandled exceptions, changed evaluation order, and undocumented public API
   changes.
5. Recheck the quality gates in Section 9.
6. Report every command that was run and distinguish passed, failed, and
   skipped checks. Never claim a check passed when it was not run.

## 3. Source Files and Imports — `JAVA-SOURCE`

-   **MUST** encode source files as UTF-8.
-   **MUST** name a file containing a class after its one case-sensitive
    top-level class, followed by `.java`. `package-info.java` and
    `module-info.java` use their special forms.
-   **MUST** use the ASCII horizontal space (`0x20`) as source-file whitespace
    apart from line terminators. Do not use tabs or other whitespace
    characters, including in indentation. Escape non-ASCII whitespace in
    character, string, and text-block literals.
-   **MAY** use a readable non-ASCII character in source or use its Unicode
    escape. Prefer the actual character when it is clear; add a comment when an
    escape would otherwise be difficult to understand. Use Java's standard
    escape sequences for characters that have them.
-   **MUST** order ordinary source-file sections as follows, with one blank line
    between present sections:
    1. License or copyright information, if present.
    2. Package declaration.
    3. Imports.
    4. Exactly one top-level class declaration, including an interface, enum,
       record, or annotation type.
-   **MUST** declare a package in every ordinary source file. `package-info.java`
    contains the package declaration without a class, and `module-info.java`
    contains a module declaration without a package declaration.
-   **MUST NOT** use compact source files unless the repository explicitly
    supports and requires them.
-   **MUST** use lowercase letters and digits for package and module names; do
    not use underscores or camel case.
-   **MUST NOT** use wildcard imports or module imports.
-   **MUST NOT** wrap import declarations. Package declarations and imports are
    exempt from the column limit.
-   **MUST** place static imports in one group before non-static imports. If
    both groups exist, separate them with one blank line; sort each group in
    ASCII order and add no other blank lines.
-   **MUST** use a normal import for a static nested class rather than a static
    import.
-   **SHOULD** keep one logical top-level class per source file and choose a
    logical, explainable order for class members and initializers.
-   **MUST** keep overloads contiguous, with no unrelated member between
    methods or constructors that share a name.
-   **MUST** order module directives in blocks: `requires`, `exports`,
    `opens`, `uses`, then `provides`. Separate present
    blocks with one blank line.

## 4. Formatting Rules — `JAVA-FORMATTING`

-   **MUST** use braces with `if`, `else`, `for`, `do`, and `while`, including
    empty and single-statement bodies.
-   **MUST** use K&R braces for non-empty blocks: keep the opening brace on the
    same line, break after it and before the closing brace, and break after the
    closing brace only when it terminates a statement or declaration. Keep the
    closing brace on the same line as a following `else`, `catch`,
    `finally`, or comma.
-   **MAY** format an empty block as `{}`, except that an empty block in a
    multi-block statement such as `try/catch/finally` is written with its
    braces on separate lines.
-   **MUST** indent each new block or block-like construct by two spaces.
-   **MUST** place one statement on each line.
-   **MUST** keep Java code to 100 characters per line, except for package
    declarations, imports, text-block contents, copyable shell commands in
    comments, unavoidable lines, and rare long identifiers.
-   **MUST** indent a wrapped continuation line at least four spaces from the
    original line.
-   **SHOULD** wrap at the highest useful syntactic level. Break before
    non-assignment operators and usually after assignment operators. Keep a
    method or constructor name attached to its opening parenthesis and keep a
    comma attached to the preceding token.
-   **MUST NOT** break immediately before a lambda or switch arrow. **MAY**
    break immediately after the arrow only when the remainder is a single
    unbraced expression and the break improves readability.
-   **MUST** use one blank line between consecutive members or initializers,
    except that blank lines between consecutive fields are optional and may
    group related fields. Add a blank line elsewhere only when it improves a
    logical separation. Multiple blank lines are never required.
-   **SHOULD** use one ASCII space around binary and ternary operators, after
    commas, colons, and semicolons, between keywords and parentheses, and before
    opening braces. Do not add spaces around `.` or `::`.
-   **MAY** use horizontal alignment, but never add or preserve alignment at
    the cost of a noisy or fragile diff.
-   **SHOULD** retain grouping parentheses when they make precedence or intent
    clearer.

## 5. Java Constructs and Practices — `JAVA-PRACTICES`

### Control flow — `JAVA-CONTROL-FLOW`

-   **SHOULD** keep control flow shallow. Extract a named predicate or
    operation when nested branches obscure the business rule; do not extract a
    trivial sequence merely to reduce indentation.
-   **MUST** indent switch labels by two spaces relative to the switch block and
    their statements by another two spaces.
-   **MUST** make every switch exhaustive. Add `default` when the cases do not
    otherwise cover every possible value.
-   **MUST** document intentional or possible fall-through in an old-style
    switch with a comment such as `// fall through`. There is no fall-through
    in a new-style switch.
-   **MUST** use new-style (`->`) syntax for switch expressions.

### Declarations and initialization — `JAVA-DECLARATIONS`

-   **MUST** declare one variable per declaration, except for multiple variables
    in a `for` header.
-   **SHOULD** declare local variables close to their first use and initialize
    them at declaration or immediately afterward. Prefer `final` fields and
    immutable locals when that improves safety; do not add `final` mechanically.
-   **SHOULD** use `var` only for local variables when the initializer makes the
    type immediately clear and the repository supports the required language
    level. Use an explicit type when it improves the API, documents a
    non-obvious type, or avoids confusing numeric, generic, or nullable
    inference.
-   **MUST** put array brackets with the type: `String[] args`, not
    `String args[]`.
-   **MUST** order class and member modifiers as:
    `public protected private abstract default static final sealed non-sealed
    transient volatile synchronized native strictfp`.
-   **MUST** order `requires` module modifiers as `transitive static`.
-   **MUST** use an uppercase `L` for `long` integer literals, such as
    `3000000000L`.
-   **MUST** place the opening and closing `"""` delimiters of a text block on
    their own lines. Keep both delimiters at the same indentation, and indent
    text at least as far as the delimiters. Text-block contents may exceed the
    column limit.

### Types, state, and API boundaries — `JAVA-API`

-   **MUST** keep implementation fields private unless a framework or public
    contract requires otherwise. Do not expose mutable internal state through
    public fields or accessors.
-   **SHOULD** prefer immutable value objects and final fields. Use a record for
    a transparent data carrier with value semantics when the supported Java
    version and repository conventions allow it; defensively copy mutable
    components.
-   **SHOULD** return interface types such as `List` or `Map` and expose
    unmodifiable views or copies when callers must not mutate internal state.
    Preserve ordering, duplicate, and null-element semantics when changing a
    collection representation.
-   **MUST** preserve the `equals`/`hashCode` contract. Override both when a
    type defines value equality, and do not base hash identity on mutable state
    used in hash-based collections.
-   **MUST** follow the repository's nullability annotations and API contract.
    Make accepted and rejected `null` values explicit at public boundaries;
    do not silently change null behavior while refactoring.
-   **MUST** preserve names, visibility, annotations, constructors, and schema
    details relied on by serialization or reflection unless the task includes
    an explicit migration.
-   **SHOULD** use `Optional` for an absent return value when the repository
    uses that convention. Do not use an `Optional` field, parameter, or
    collection element as a substitute for a clear domain model, and never
    return `null` where an `Optional` is promised.
-   **MUST NOT** introduce raw types or broad unchecked operations. If an
    unchecked operation is unavoidable, isolate it, suppress the warning at the
    narrowest scope, and document the safety invariant.

### Collections and streams — `JAVA-COLLECTIONS`

-   **SHOULD** use a stream for a short, side-effect-free transformation whose
    stages read naturally. Prefer a loop for stateful, multi-step, exceptionful,
    or heavily debugged logic; do not force either form.
-   **MUST NOT** mutate external or shared state from a stream pipeline. Preserve
    encounter order and short-circuit behavior, and do not introduce
    `parallelStream()` without an explicit requirement and evidence that it
    helps.
-   **SHOULD** give a repeated domain query a semantic name or a first-class
    collection rather than duplicating a mechanical pipeline. See the
    structural signals below and `general.md` Section 4.

### Exceptions and resources — `JAVA-ERRORS`

-   **MUST** catch the most specific exception that can be handled. Do not catch
    `Exception`, `Throwable`, or `Error` broadly except at a deliberate
    application boundary with a documented reason.
-   **MUST** log, rethrow, translate, or otherwise handle every caught
    exception. If taking no action is genuinely correct, explain why in a
    comment. When translating, preserve the original cause.
-   **SHOULD** log an exception at the boundary that can act on it; do not log
    and rethrow the same failure at every layer or include secrets in messages.
-   **MUST** use try-with-resources for `AutoCloseable` resources whose lifetime
    the method owns. Do not close a resource whose ownership was transferred or
    is managed by a framework; make that ownership explicit. Do not return or
    throw from a `finally` block; preserve the original failure.
-   **MUST** preserve interruption when catching `InterruptedException` unless
    the method rethrows it or delegates cancellation explicitly:
    `Thread.currentThread().interrupt()`.

### Concurrency — `JAVA-CONCURRENCY`

-   **SHOULD** prefer immutable or thread-confined state and the
    `java.util.concurrent` abstractions over ad hoc coordination.
-   **MUST** make visibility and atomicity explicit for shared mutable state.
    `volatile` provides visibility, not atomicity for compound operations.
-   **SHOULD** synchronize on a private, stable lock rather than `this`, a
    public object, or a string literal. Keep lock ordering and ownership
    understandable.
-   **MUST** define ownership and lifecycle for executors, schedulers, and
    threads. Do not create an unbounded or per-call executor without a
    documented bound and shutdown strategy.
-   **SHOULD** document thread-safety, blocking, interruption, and cancellation
    behavior for public APIs that coordinate concurrent work.

### Tests and test doubles — `JAVA-TESTING`

-   **MUST** make tests deterministic and assert observable behavior, including
    relevant boundary, failure, and compatibility cases.
-   **SHOULD** prefer a fake, stub, or injected clock over sleeps, wall-clock
    timing, network calls, or uncontrolled randomness. If randomness is
    necessary, use a reproducible seed and report it on failure.
-   **MUST NOT** use sleeps as the primary synchronization mechanism. Use the
    repository's awaitility, latch, future, virtual-time, or equivalent
    facility with bounded timeouts.
-   **SHOULD** use parameterized tests for a meaningful matrix of equivalent
    cases and keep each test focused on one behavior or contract.
-   **SHOULD** keep test fixtures readable and local. Do not weaken production
    visibility or error handling solely to make a test convenient.

### Annotations and comments — `JAVA-ANNOTATIONS`

-   **MUST** put type-use annotations immediately before the annotated type.
-   **MUST** put class, package, module, method, and constructor annotations
    immediately after their Javadoc, one annotation per line. A single
    parameterless method or constructor annotation may share the first
    signature line.
-   **MUST** put field annotations immediately after the field's Javadoc.
    Multiple field annotations may share one line. Parameters and local
    variables have no additional placement rule beyond type-use placement.
-   **SHOULD** keep `@SuppressWarnings` at the narrowest useful scope and
    explain the invariant that makes the suppression safe.
-   **MUST** indent block comments with surrounding code, align continuation
    `*` characters in `/* ... */` comments, and avoid decorative comment
    boxes.
-   **MUST** use `TODO: <resource> - <explanation>` for temporary work. Link to
    context, ideally a bug reference; do not use a person or team as the
    context. Include a specific date or event when the TODO is time-bound.
-   **MUST** use `@Override` whenever legal, including interface
    implementations and explicitly declared record accessors. It may be
    omitted when the parent method is deprecated.
-   **MUST** qualify static members with their declaring class, for example
    `Foo.aStaticMethod()`, not `aFoo.aStaticMethod()`.
-   **MUST NOT** override `Object.finalize`.

### Structural design (Java)

These rules complement the cross-language structural rules in `general.md`
with Java-specific extraction signals and patterns.
Apply the `GEN-*` rules as diagnostic signals: a refactor is justified by
cohesion, coupling, behavior, and change risk, not by a line count alone. Record
a relevant accepted deviation with its rule ID, location, reason, impact, and
verification.

#### Method extraction signals — `JAVA-DESIGN-EXTRACTION`

-   **SHOULD** extract a private method when a code block requires an inline
    comment to explain *what* it does. The method name replaces the comment.
-   **SHOULD** extract a non-trivial stream pipeline or loop when it encodes a
    business rule that would be clearer with a domain name. Keep a simple,
    one-use transformation inline when extraction would hide the flow.
-   **SHOULD** treat a private method longer than approximately 15 lines as an
    early signal to inspect for multiple responsibilities. Also apply
    `GEN-SIZE-METHOD`'s approximately 30-line diagnostic threshold; neither
    threshold requires a mechanical split.
-   **SHOULD** name an extracted method after the business concept, not the
    mechanical operation. Preserve evaluation order, short-circuiting, and
    exception behavior during extraction.

Preferred — extract named business logic:

```java
// Before: business rule hidden inside a stream pipeline in a controller
boolean hasValidated = steps.stream()
    .anyMatch(s -> s.getValidationStatus() == VALIDATED);

// After: extracted to a domain method with a semantic name
boolean hasValidated = funnelSteps.hasAnyValidated();
```

#### Controller responsibility — `JAVA-DESIGN-BOUNDARY`

-   **SHOULD** keep controllers and entry-point classes thin. A controller
    orchestrates — it receives input, delegates to domain or service objects,
    maps boundary data, and returns output. It should not contain domain
    decisions, complex conditionals, or non-trivial collection processing.
    Simple DTO projection and boundary validation are acceptable when they are
    local and do not duplicate domain rules.
-   **SHOULD** move decision logic that reads multiple properties of a domain
    object into that domain object. See `general.md` Section 3 (Feature
    Envy).

Preferred — thin controller:

```java
@PostMapping("/orders/{id}/ship")
ResponseEntity<Void> ship(@PathVariable Long id) {
  Order order = orders.findOrFail(id);
  shipmentService.shipIfReady(order);
  return ResponseEntity.accepted().build();
}
```

Avoid — controller containing domain logic:

```java
@PostMapping("/orders/{id}/ship")
ResponseEntity<Void> ship(@PathVariable Long id) {
  Order order = orders.findOrFail(id);
  // Feature Envy: controller reads order internals to decide
  if (order.getStatus() == VALIDATED
      && order.getPayment().isConfirmed()
      && order.getItems().stream().allMatch(Item::isAvailable)) {
    shipmentService.ship(order);
  }
  return ResponseEntity.accepted().build();
}
```

#### Complex private methods and collections — `JAVA-DESIGN-COLLECTION`

-   **SHOULD** treat an accumulation of private methods with maps, nested
    conditionals, or multi-step transformations as a design signal, not just a
    size signal. It may indicate a missing domain abstraction.
-   When multiple private methods in the same class operate on the same data
    structure (for example, building a `Map`, filtering it, and reducing it),
    **SHOULD** extract a First-Class Collection or domain class that
    encapsulates those operations. See `general.md` Section 4.
-   **MUST NOT** extract a generic `Manager`, `Helper`, or `Utils` class
    solely to move difficult code elsewhere. The new boundary needs a cohesive
    responsibility, a meaningful name, and an independently testable contract.

## 6. Naming Rules — `JAVA-NAMING`

-   **MUST** use ASCII letters and digits in identifiers, plus underscores only
    where explicitly allowed. Do not add prefixes or suffixes such as `mName`,
    `name_`, `s_name`, or `kName`.
-   **MUST** use lowercase letters and digits for package and module names,
    concatenating words without separators (`com.example.deepspace`).
-   **MUST** use `UpperCamelCase` for classes, interfaces, enums, and records.
    Class names are normally nouns or noun phrases; interface names may also
    be adjectives. Follow the repository convention for annotation types;
    Google Style defines no additional annotation-type naming rule.
-   **MUST** end a test class name with `Test` (for example, `OrderTest`).
-   **MUST** use `lowerCamelCase` for methods, fields, parameters, and local
    variables. Method names should normally be verbs or verb phrases, while
    fields and parameters are normally nouns or noun phrases.
-   **MAY** use underscores between logical parts of JUnit test method names;
    each part remains `lowerCamelCase`.
-   **SHOULD** use `UPPER_SNAKE_CASE` for enum constants, unless the
    repository's test or serialization contract requires another spelling.
-   **MUST** use `UPPER_SNAKE_CASE` only for `static final` fields whose values
    are deeply immutable and whose methods have no detectable side effects.
    `final` alone does not make an instance field or mutable value a constant.
-   **MUST** keep non-constant fields, including `static final` fields that
    reference mutable state, in `lowerCamelCase`.
-   **SHOULD** avoid one-character parameter names in public methods unless the
    type or established convention makes the meaning obvious.
-   **MUST** name type variables with one capital letter and an optional numeral
    (`T`, `E`, `T2`) or a class-style name ending in `T` (`RequestT`).
-   **MAY** use `_` for unnamed variables and parameters only where the
    declared Java version permits it and the omission improves clarity.
-   **SHOULD** normalize acronyms as words: use `XmlHttpRequest`,
    `newCustomerId`, and `supportsIpv6OnIos`, not their all-caps variants.
-   **MAY** use underscores to separate adjacent number components in the rare
    case where camel case cannot distinguish them, such as `guava33_4_6`.

## 7. Javadoc Rules — `JAVA-JAVADOC`

-   **MUST** use either Markdown Javadoc (`///`) or traditional Javadoc
    (`/** ... */`). A single-line block is appropriate only when the entire
    block fits on one line and has no block tags.
-   **MUST** begin each Javadoc block with a brief, capitalized, punctuated
    summary fragment. Prefer `Returns the canonical identifier.` over
    `This method returns...` or an imperative sentence such as `Save the
    record.`
-   **MUST** separate traditional-Javadoc paragraphs with one blank line and
    place `<p>` immediately before the first word of paragraphs after the
    first. Use normal blank lines for Markdown Javadoc paragraphs.
-   **MUST** order the core block tags, when present, as `@param`,
    `@return`, `@throws`, and `@deprecated`; give every
    used tag a non-empty description. Place other standard tags according to
    the repository's Javadoc convention.
-   **MUST** indent wrapped traditional-Javadoc tag text at least four spaces
    from `@` and Markdown continuations exactly two spaces.
-   **SHOULD** document public and protected types, members, and record
    components when their purpose, constraints, side effects, nullability, or
    exceptions are not obvious from the signature. An override may inherit
    documentation when it adds no contract or behavior.
-   **SHOULD** document each parameter and non-obvious return or failure
    condition for a public API. Use `@param`, `@return`, and `@throws` only
    when they add contract information; do not restate an obvious signature.
-   **MUST** pair `@Deprecated` with a `@deprecated` description that states
    the replacement or removal reason and any migration constraint.
-   **SHOULD** use `{@link ...}` for navigable API references and
    `{@code ...}` for code, identifiers, and literal values. Escape or
    structure HTML deliberately; do not put raw sensitive data in Javadoc.
-   **MUST** use the Javadoc form supported by the repository's compiler,
    documentation tool, and formatter. Do not introduce Markdown Javadoc
    solely because it is shorter.
-   **SHOULD** express overall purpose or behavior in Javadoc rather than an
    implementation comment.

## 8. Few-shot Examples

Use these examples as formatting and decision patterns. They are non-normative:
adapt names and types to the repository instead of copying them mechanically.

### Source structure and imports

Preferred:

```java
package com.example.orders;

import static java.util.Objects.requireNonNull;

import java.time.Instant;
import java.util.List;
```

This demonstrates the package first, static imports in their own group, and
non-static imports without wildcard imports or arbitrary blank lines.

### Braces and wrapping

Preferred:

```java
if (order.isReady()) {
  submit(order);
} else {
  queue(order);
}

private static Result createResult(
    Request request, Clock clock, Metrics metrics) {
  return new Result(request, clock.instant(), metrics);
}
```

This demonstrates required braces, two-space block indentation, and a
continuation indented by at least four spaces.

### Switch wrapping

Preferred:

```java
return switch (status) {
  case READY -> submit();
  default ->
      useFallback();
};
```

The break after the switch arrow is allowed because the remainder is one
unbraced expression. A break before the arrow is not allowed.

### Constants and fields

Preferred:

```java
private static final Duration DEFAULT_TIMEOUT = Duration.ofSeconds(5);

private final String customerId;
```

`DEFAULT_TIMEOUT` is a deeply immutable static final value. `customerId` is an
instance field, so it remains `lowerCamelCase` even though it is final.

### Ownership and resources

Preferred:

```java
final class Order {
  private final List<String> tags;

  Order(List<String> tags) {
    this.tags = List.copyOf(tags);
  }

  List<String> tags() {
    return tags;
  }
}
```

The constructor establishes ownership of an immutable copy, so callers cannot
mutate the object's internal list through the returned value.

Preferred exception boundary:

```java
try (BufferedReader reader = Files.newBufferedReader(path, UTF_8)) {
  return reader.readLine();
} catch (IOException e) {
  throw new ConfigurationException("Cannot read configuration", e);
}
```

The resource is closed automatically and the original cause is preserved when
the lower-level failure is translated.

### Javadoc

Preferred:

```java
/**
 * Returns the canonical identifier for an order.
 *
 * <p>The identifier is stable across retries.
 *
 * @param order order to identify
 * @return canonical order identifier
 * @throws IllegalArgumentException if the order has no identifier
 */
String canonicalId(Order order) {
  return order.requireId();
}
```

The summary is a fragment, the paragraph is separated correctly, and block
tags are ordered and described.

## 9. Verification and Output Contract

Before reporting completion, verify the following:

-   The file structure and imports are valid.
-   Formatting uses braces, two-space indentation, the 100-character limit, and
    correct wrapping.
-   Switches, annotations, comments, modifiers, literals, and exceptions meet
    the applicable rules.
-   Names distinguish constants from ordinary fields and variables.
-   Public and protected APIs have useful Javadoc where the contract is not
    obvious, including relevant nullability, side effects, and failures.
-   Relevant structural signals from `general.md` were assessed:
    class/method size, coupling, behavior ownership, First-Class Collections,
    duplication, and controller boundaries. Approximate thresholds have a
    recorded design reason when exceeded.
-   Resource ownership, exception causes, interruption, and concurrency
    behavior remain correct when the change touches them.
-   The effective Java version, configured formatter, linter, compiler, and
    relevant tests were run, or each unavailable/skipped check is explicitly
    reported.
-   Public API, serialization, and reflection compatibility were checked when
    applicable.
-   The final diff contains no unrelated reformatting or generated artifacts.

For a direct or human-facing task, use this concise report format:

```text
Summary:
- <what changed and why>

Changed files:
- <path>

Rules applied:
- <relevant rule IDs or "none">

Validation:
- <command>: passed | failed | skipped (<reason>)

Assumptions and deviations:
- none

Unresolved risks:
- none
```

When operating under `/saturation`, return the phase's exact handoff
or output contract instead of replacing it with this text template. Keep
machine-readable keys and repository-relative paths unchanged. In every
context, never claim a check passed when it was not run. If a rule cannot be
applied, state the exact rule, the reason, the affected path, and the smallest
safe alternative.

## Sources

-   [Google Java Style Guide](https://google.github.io/styleguide/javaguide.html)
-   Cross-language structural rules in `general.md`.
-   Prompt construction and evaluation are centralized in
    [`prompting.md`](prompting.md). Read that module when this Java guide is
    being used to compose an operational agent prompt.
