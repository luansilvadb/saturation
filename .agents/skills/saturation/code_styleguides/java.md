# Java Code Style Guide — Agent Instructions

Use this file as the Java-specific instruction block whenever you create,
edit, review, or refactor Java code. It is an operational prompt, not only a
reference list: understand the task, apply the rules, verify the result, and
report what was actually verified.

## 1. Agent Contract

### Role

Act as a careful Java engineer and code reviewer. Produce code that is easy to
read, safe to change, consistent with the repository, and conformant with the
[Google Java Style Guide](https://google.github.io/styleguide/javaguide.html).

### Objective

For every Java change:

1. Preserve the requested behavior and public contracts.
2. Apply the mandatory rules in this document to all new or modified code.
3. Keep the diff focused; do not reformat unrelated code.
4. Run the most relevant available formatting, static-analysis, build, and test
   checks.
5. Report changes, checks, assumptions, and unresolved risks accurately.

### Context to inspect

Before editing, inspect only the context relevant to the task:

-   The Java version declared by the build (`pom.xml`, `build.gradle`, or
    equivalent).
-   Existing Java files near the change, including tests and public APIs.
-   Repository formatter, linter, compiler, and test configuration.
-   The requested behavior, compatibility requirements, and local conventions.

Use repository context to resolve harmless stylistic choices. Do not infer a
new project convention from a single exceptional file.

### Rule priority

Resolve conflicts in this order:

1. Explicit user requirements and acceptance criteria.
2. Required project constraints, compatibility targets, and generated-code
   boundaries.
3. The mandatory Google Java rules in this document.
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

## 2. Execution Procedure

Follow this sequence for each task. If a step cannot be completed, record why
and continue only when doing so is safe.

### Before editing

1. Identify the Java files, public APIs, tests, and build configuration in
   scope.
2. Confirm the Java language level and the repository's formatter or linter.
3. Separate required behavior from optional cleanup.
4. Choose the smallest implementation that satisfies the request.

### While editing

1. Preserve behavior unless the task explicitly requests a behavior change.
2. Apply this guide and the structural design rules in `general.md` to all
   new and modified code.
3. Keep overloads, related members, and public documentation coherent.
4. Prefer a clear local variable or extracted method over clever wrapping.
   See Section 5 "Structural design" for concrete extraction signals.
5. Keep comments focused on intent, constraints, or non-obvious behavior.
6. Check structural health: class size, method size, coupling count, and
   encapsulation against the thresholds in `general.md`.

### After editing

1. Run the repository formatter when one is configured.
2. Run focused compilation, static analysis, and tests; expand coverage when
   the change affects shared or public behavior.
3. Inspect the final diff for accidental reformatting, missing imports,
   unhandled exceptions, and undocumented public API changes.
4. Recheck the quality gates in Section 8.
5. Report every command that was run and distinguish skipped checks from passed
   checks.

## 3. Source Files and Imports

-   **MUST** encode source files as UTF-8.
-   **MUST** name a file containing a class after its one case-sensitive
    top-level class, followed by `.java`. `package-info.java` and
    `module-info.java` use their special forms.
-   **MUST** use the ASCII horizontal space (`0x20`) as source-file whitespace
    and never use tabs for indentation. Escape special characters with Java's
    standard escape sequences when available.
-   **MUST** order ordinary source-file sections as follows, with one blank line
    between present sections:
    1. License or copyright information, if present.
    2. Package declaration.
    3. Imports.
    4. Exactly one top-level class declaration.
-   **MUST** declare a package in every ordinary source file. Use lowercase
    letters and digits for package and module names; do not use underscores or
    camel case.
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

## 4. Formatting Rules

-   **MUST** use braces with `if`, `else`, `for`, `do`, and `while`, including
    empty and single-statement bodies.
-   **MUST** use K&R braces: the opening brace stays on the same line, and a
    non-empty block starts and ends on its own lines.
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
-   **MUST NOT** break immediately before or after a lambda arrow or switch
    arrow.
-   **MUST** use one blank line between consecutive class members or
    initializers. Add a blank line elsewhere only when it improves a logical
    separation.
-   **SHOULD** use one ASCII space around binary and ternary operators, after
    commas, colons, and semicolons, between keywords and parentheses, and before
    opening braces. Do not add spaces around `.` or `::`.
-   **MAY** use horizontal alignment, but never add or preserve alignment at
    the cost of a noisy or fragile diff.
-   **SHOULD** retain grouping parentheses when they make precedence or intent
    clearer.

## 5. Java Constructs and Practices

### Control flow

-   **MUST** indent switch labels by two spaces relative to the switch block
    and their statements by another two spaces.
-   **MUST** make every switch exhaustive. Add `default` when the cases do not
    otherwise cover every possible value.
-   **MUST** document intentional or possible fall-through in an old-style
    switch with a comment such as `// fall through`.
-   **MUST** use new-style (`->`) syntax for switch expressions.

### Declarations and initialization

-   **MUST** declare one variable per declaration, except for multiple variables
    in a `for` header.
-   **SHOULD** declare local variables close to their first use and initialize
    them at declaration or immediately afterward.
-   **MUST** put array brackets with the type: `String[] args`, not
    `String args[]`.
-   **MUST** order class and member modifiers as:
    `public protected private abstract default static final sealed non-sealed
    transient volatile synchronized native strictfp`.
-   **MUST** order `requires` module modifiers as `transitive static`.
-   **MUST** use an uppercase `L` for `long` integer literals, such as
    `3000000000L`.
-   **MUST** place text-block delimiters on their own lines with matching
    indentation. Text-block contents may exceed the column limit.

### Annotations, comments, and errors

-   **MUST** put type-use annotations immediately before the annotated type.
-   **MUST** put class, package, module, method, and constructor annotations
    immediately after their Javadoc, one annotation per line. A single
    parameterless method or constructor annotation may share the first
    signature line.
-   **MUST** indent block comments with surrounding code, align continuation
    `*` characters in `/* ... */` comments, and avoid decorative comment boxes.
-   **MUST** use `TODO: <resource> - <explanation>` for temporary work. Link to
    context, ideally a bug reference; do not use a person or team as the
    context.
-   **MUST** use `@Override` whenever legal, including interface
    implementations and explicitly declared record accessors. It may be
    omitted when the parent method is deprecated.
-   **MUST** handle caught exceptions by logging, rethrowing, or otherwise
    explaining them. If intentionally taking no action, add a comment that
    justifies the decision.
-   **MUST** qualify static members with their declaring class, for example
    `Foo.aStaticMethod()`, not `aFoo.aStaticMethod()`.
-   **MUST NOT** override `Object.finalize`.

### Structural design (Java)

These rules complement the cross-language structural rules in `general.md`
with Java-specific extraction signals and patterns.

#### Method extraction signals

-   **SHOULD** extract a private method when a code block requires an inline
    comment to explain *what* it does. The method name replaces the comment.
-   **SHOULD** extract when a method contains a stream pipeline or loop that
    encodes a business rule. Name the extracted method after the business
    concept, not the mechanical operation.
-   **SHOULD** treat a private method longer than approximately 15 lines as a
    signal that it may be doing more than one thing. Consider whether part of
    the logic belongs in a domain class.

Preferred — extract named business logic:

```java
// Before: business rule hidden inside a stream pipeline in a controller
boolean hasValidated = steps.stream()
    .anyMatch(s -> s.getValidationStatus() == VALIDATED);

// After: extracted to a domain method with a semantic name
boolean hasValidated = funnelSteps.hasAnyValidated();
```

#### Controller responsibility

-   **SHOULD** keep controllers and entry-point classes thin. A controller
    orchestrates — it receives input, delegates to domain or service objects,
    and returns output. It should not contain domain logic, complex
    conditionals, or collection operations.
-   **SHOULD** move decision logic that reads multiple properties of a domain
    object into that domain object. See `general.md` Section 3 (Feature
    Envy).

Preferred — thin controller:

```java
@PostMapping("/orders/{id}/ship")
ResponseEntity<Void> ship(@PathVariable Long id) {
  Order order = orders.findOrFail(id);
  shipmentService.shipIfReady(order);     // domain decides readiness
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

#### Complex private methods

-   **SHOULD** treat an accumulation of private methods with Maps, nested
    conditionals, or multi-step transformations as a design signal, not just
    a size signal. It often means a missing domain abstraction.
-   When multiple private methods in the same class operate on the same data
    structure (e.g. building a `Map`, filtering it, reducing it), **SHOULD**
    extract a First-Class Collection or domain class that encapsulates those
    operations. See `general.md` Section 4.

## 6. Naming Rules

-   **MUST** use ASCII letters and digits in identifiers, plus underscores only
    where explicitly allowed. Do not add prefixes or suffixes such as `mName`,
    `name_`, `s_name`, or `kName`.
-   **MUST** use lowercase letters and digits for package and module names,
    concatenating words without separators (`com.example.deepspace`).
-   **MUST** use `UpperCamelCase` for classes, interfaces, enums, records, and
    annotation types. A test class ends with `Test`.
-   **MUST** use `lowerCamelCase` for methods, fields, parameters, and local
    variables. Method names should normally be verbs or verb phrases.
-   **MAY** use underscores between logical parts of JUnit test method names;
    each part remains `lowerCamelCase`.
-   **MUST** use `UPPER_SNAKE_CASE` only for `static final` fields whose values
    are deeply immutable and whose methods have no detectable side effects.
    `final` alone does not make an instance field or mutable value a constant.
-   **MUST** name type variables with one capital letter and an optional numeral
    (`T`, `E`, `T2`) or a class-style name ending in `T` (`RequestT`).
-   **MAY** use `_` for unnamed variables and parameters where the Java language
    permits it.
-   **SHOULD** normalize acronyms as words: use `XmlHttpRequest`,
    `newCustomerId`, and `supportsIpv6OnIos`, not their all-caps variants.

## 7. Javadoc Rules

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
-   **MUST** order block tags as `@param`, `@return`, `@throws`, and
    `@deprecated`; give each used tag a non-empty description.
-   **MUST** indent wrapped traditional-Javadoc tag text at least four spaces
    from `@` and Markdown continuations exactly two spaces.
-   **MUST** document every visible class, member, and record component unless
    it is genuinely simple and obvious or is an override needing no extra
    explanation.
-   **SHOULD** express overall purpose or behavior in Javadoc rather than an
    implementation comment.

## 8. Few-shot Examples

Use these examples as formatting and decision patterns. Adapt names and types
to the repository instead of copying them mechanically.

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

### Constants and fields

Preferred:

```java
private static final Duration DEFAULT_TIMEOUT = Duration.ofSeconds(5);

private final String customerId;
```

`DEFAULT_TIMEOUT` is a deeply immutable static final value. `customerId` is an
instance field, so it remains `lowerCamelCase` even though it is final.

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
-   Visible APIs have useful Javadoc.
-   Structural design checks from `general.md` pass: class size, method size,
    coupling count, Feature Envy, First-Class Collections, and duplication.
-   Controllers are thin and do not contain domain logic (Section 5,
    "Controller responsibility").
-   The configured formatter, linter, compiler, and relevant tests were run, or
    each unavailable/skipped check is explicitly reported.
-   The final diff contains no unrelated reformatting or generated artifacts.

Use this report format:

```text
Summary:
- <what changed and why>

Changed files:
- <path>

Validation:
- <command>: passed | failed | skipped (<reason>)

Assumptions and deviations:
- none
```

Never claim a check passed when it was not run. If a rule cannot be applied,
state the exact rule, the reason, the affected path, and the smallest safe
alternative.

## Sources

-   [Google Java Style Guide](https://google.github.io/styleguide/javaguide.html)
-   [Prompt Engineering Guide](https://www.promptingguide.ai/)

The prompt structure follows the guide's practical principles: state the
instruction and context, define the expected output, be specific without
adding irrelevant detail, provide examples, make quality gates explicit, handle
errors visibly, and iterate based on observed behavior.
