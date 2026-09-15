# Google C# Style Guide — Agent Instructions

Use this module whenever you create, modify, review, or refactor C# code. It
is an operational summary of the [Google C# Style
Guide](https://google.github.io/styleguide/csharp-style.html), supplemented by
practical engineering guidance for modern .NET code. It is not a reason to
reformat an unrelated file or to introduce a language feature unsupported by
the project.

Use [`general.md`](general.md) for cross-language structural rules and
[`prompting.md`](prompting.md) for prompt construction. Explicit user
requirements, project constraints, generated-code boundaries, and the
effective compiler configuration take precedence over this module.

## 1. Agent contract

### Role

Act as a careful C# engineer and reviewer. Produce code that is readable,
safe to change, compatible with the declared target, and consistent with the
surrounding repository.

### Objective

For every C# change:

1. Preserve requested behavior, public contracts, and compatibility unless the
   task explicitly changes them.
2. Apply only the relevant rules in this module to new or modified code.
3. Keep the diff focused; do not turn a feature or bug fix into a legacy-code
   cleanup or repository-wide formatting pass.
4. Use the repository's formatter, analyzers, compiler, build, and test tools
   when they exist.
5. Report actual changes, checks, assumptions, accepted deviations, and
   unresolved risks accurately.

### Context to inspect

Before editing, inspect the context needed for the assigned paths:

-   The C# language version, target framework(s), runtime, nullable setting,
    implicit/global using configuration, and relevant conditional compilation
    symbols.
-   The solution/project files, `.editorconfig`, analyzers, formatter, source
    generators, and build/test commands that govern the change.
-   Nearby C# files, tests, public APIs, serialization or reflection
    boundaries, dependency-injection registration, and threading or resource
    ownership conventions.
-   The requested behavior, compatibility requirements, and established local
    style. Do not infer a project-wide convention from one exceptional file.

### Applicability and boundaries

-   **MUST** identify generated, vendored, migrated, designer-owned, and
    formatter-owned files before editing. Change the source or template that
    owns generated output; hand-edit generated or third-party code only when
    the task explicitly requires it.
-   **MUST** apply this module to new and modified lines. Preserve unrelated
    legacy deviations unless the task is an intentional migration.
-   **SHOULD** select only the rule IDs relevant to the assigned paths and
    objective. A threshold or recommendation is a design signal, not an
    automatic refactoring command.
-   **MUST NOT** request or store hidden chain-of-thought. Ask for concise
    decisions, assumptions, checks, and observable evidence instead.

### Rule priority

Resolve conflicts in this order:

1. Explicit user requirements and acceptance criteria.
2. System and project safety constraints, compatibility targets, and generated
   boundaries.
3. The mandatory Google C# rules and engineering rules in this module.
4. Established local conventions that do not conflict with the levels above.
5. Personal preference.

When a higher-priority constraint prevents a rule, make the smallest safe
deviation and report its reason and impact. Do not silently reformat unrelated
code.

### Normative language

-   **MUST:** Required unless a documented higher-priority constraint applies.
-   **SHOULD:** The default choice. Deviate only when the context provides a
    clear reason and the result remains readable and consistent.
-   **MAY:** Permitted choice. Prefer the option that is easiest to understand,
    test, and maintain.
-   **BLOCK:** Stop the current phase when a required prerequisite, scope
    boundary, or compatibility fact is missing. Escalate rather than guess.

## 2. Execution procedure

### Before editing

1. Identify the affected projects, C# files, tests, public contracts, and
   generated-code boundaries.
2. Confirm the effective language version, target framework, nullable context,
   formatter, analyzers, compiler, build, and test commands.
3. Separate required behavior from optional cleanup. Record source, binary,
   serialization, reflection, threading, and resource-lifetime constraints
   when they apply.
4. Select the relevant rule IDs and identify existing deviations that must be
   preserved.
5. Choose the smallest implementation that satisfies the request.

### While editing

1. Preserve evaluation order, exception behavior, disposal, cancellation,
   allocation characteristics, and public API shape unless the task changes
   them.
2. Apply this module together with the relevant rules in `general.md`.
3. Use only syntax and APIs supported by the declared language/runtime target.
   Do not introduce preview features, new collection expressions, `required`,
   or newer BCL APIs without project support.
4. Keep overloads, related members, XML documentation, attributes, and
   interface implementations coherent.
5. Prefer an explicit local, named method, or domain type over clever syntax or
   a generic `Helper`, `Manager`, or `Utils` abstraction.
6. Keep comments focused on intent, invariants, constraints, and non-obvious
   behavior.

### After editing

1. Run the configured formatter on the affected files. If it rewrites
   unrelated code, use a scoped invocation or record why it was skipped.
2. Run focused compilation, analyzers, and tests; expand regression checks when
   shared or public behavior is affected.
3. When applicable, check API compatibility, serialization/reflection shape,
   nullability warnings, asynchronous behavior, disposal, cancellation, and
   concurrency.
4. Inspect the final diff for accidental reformatting, missing imports,
   changed evaluation order, swallowed exceptions, resource leaks, and
   undocumented public API changes.
5. Report every command that was run and distinguish passed, failed, and
   skipped checks. Never claim a check passed when it was not run.

## 3. Source files, namespaces, and imports — `CS-SOURCE`

-   **MUST** use `.cs` for C# source files and PascalCase for file and directory
    names, following the local repository convention where one exists.
-   **SHOULD** keep one core class, interface, enum, record, or struct per file.
    Additional small, tightly coupled types, partial declarations, generated
    output, and test fixtures are reasonable exceptions.
-   **SHOULD** name a file after its primary type, such as `OrderProcessor.cs`
    for `OrderProcessor`.
-   **MUST** put ordinary `using` directives before namespace declarations and
    outside the namespace. Put `System` imports first, then order the remaining
    imports alphabetically within the repository's established static, global,
    or alias groups.
-   **MUST NOT** add unused imports. Do not depend on a transitive import when
    a direct import or a fully qualified name makes the dependency clearer.
-   **SHOULD NOT** alias a long type name merely to shorten it. A long alias is
    often a signal that a named domain type should replace a complex tuple or
    generic expression.
-   **MAY** use global usings, file-scoped namespaces, and `using` aliases when
    the project already uses them or the target explicitly supports them. Do
    not migrate namespace or import style in unrelated files.
-   **MUST** use PascalCase for namespaces and, in general, keep them to no
    more than two levels of project-specific nesting.
-   **SHOULD** use namespaces for shared libraries and modules. Leaf
    application code may omit a namespace when that is the established style.
-   **MUST NOT** force folder layout to match namespaces. Keep the existing
    project organization consistent and prefer a flat structure where it
    remains understandable.
-   **MUST** keep new top-level namespace names globally unique and
    recognizable within the product or organization.

### Declaration order

Within a type, **MUST** use this order unless a framework or generated-code
contract requires another order:

1. Nested classes, enums, delegates, and events.
2. Static, `const`, and `readonly` fields.
3. Fields and properties.
4. Constructors and finalizers.
5. Methods.

Within each group, order members by accessibility:

1. `public`
2. `internal`
3. `protected internal`
4. `protected`
5. `private`

Where possible, group interface implementations together. Keep overloads and
closely related members contiguous; do not let the ordering rule separate a
small, coherent API.

### Modifier order — `CS-MODIFIERS`

Use the Google order for modifiers:

```text
public protected internal private new abstract virtual override sealed static
readonly extern unsafe volatile async
```

Place only modifiers valid for the declaration. For newer modifiers not in the
Google list, such as `file`, `required`, `ref`, or `scoped`, follow the
compiler/formatter and the existing project convention.

## 4. Formatting — `CS-FORMATTING`

-   **MUST** use two spaces for indentation and never tabs for indentation.
-   **MUST** keep code within a 100-column limit unless a split would make an
    URL, unsplittable literal, generated fragment, or similar boundary less
    clear.
-   **MUST** write at most one statement and at most one ordinary assignment
    per line. **SHOULD** write one declaration per line.
-   **MUST** use K&R braces: keep the opening brace on the declaration or
    control-flow line, keep `} else` together, and use braces even when the
    language makes them optional.
-   **MUST** put a space after `if`, `for`, `while`, `switch`, `catch`, and
    similar keywords, and after commas.
-   **MUST NOT** put padding immediately inside parentheses. Use no space after
    `(` or before `)`.
-   **MUST NOT** put a space between a unary operator and its operand. Put one
    space around ordinary binary and ternary operators unless the expression's
    syntax requires otherwise.
-   **SHOULD** separate consecutive members or logical sections with one blank
    line. Do not use horizontal alignment that makes later edits fragile.
-   **MUST** indent general continuation lines by four spaces. For calls and
    declarations that wrap, align continuation arguments with the first
    argument when practical; otherwise use a four-space continuation indent.
-   **MUST** indent multi-line object, collection, and lambda initializer bodies
    by one block level. Closing braces align with the first character of the
    line containing the opening brace.
-   **MUST** place attributes on the line above the member they annotate.
    Separate multiple attributes onto separate lines.
-   **MUST NOT** add trailing whitespace or unrelated formatting churn.

Preferred wrapping:

```csharp
public void ProcessOrder(
    Order order,
    CancellationToken cancellationToken) {
  // ...
}

ProcessOrder(
    order,
    cancellationToken);
```

When alignment is readable and fits the column limit, it is also acceptable:

```csharp
private void ProcessOrder(Order order,
                          CancellationToken cancellationToken) {
  // ...
}
```

## 5. Naming — `CS-NAMING`

-   **MUST** use PascalCase for classes, records, structs, interfaces, enums,
    enum members, methods, public fields, public properties, events, and
    namespaces.
-   **MUST** use camelCase for local variables, parameters, and ordinary local
    function variables.
-   **MUST** use `_camelCase` for private, protected, internal, and protected
    internal fields and properties. The modifier does not change the casing
    rule.
-   **MUST** prefix interfaces with `I`, such as `IOrderStore`.
-   **MUST** use descriptive type-parameter names prefixed with `T`, such as
    `TValue` and `TKey`; `T` is appropriate for a simple, single-purpose
    parameter.
-   **MUST** treat acronyms as words: use `HttpClient`, `CustomerId`, and
    `ParseRpc`, not `HTTPClient`, `CustomerID`, or `ParseRPC`, unless an
    external contract requires the original spelling.
-   **MUST** keep casing independent of `const`, `static`, `readonly`, and
    other modifiers. Constants are still PascalCase; do not convert them to
    `UPPER_SNAKE_CASE` solely because they are constants.
-   **SHOULD** choose names that describe domain meaning rather than type,
    storage, or implementation details. Avoid unexplained abbreviations and
    Hungarian prefixes.
-   **SHOULD** use semantic boolean names such as `IsReady`, `HasItems`, or
    `CanRetry` when the value represents a predicate.
-   **MAY** preserve test, serialization, generated-code, interop, and framework
    naming conventions when changing those contracts is not in scope.

## 6. Declarations, state, and API boundaries

### Visibility and modifiers — `CS-DECLARATIONS`

-   **MUST** declare visibility explicitly for new top-level types and public,
    protected, internal, and private members. For legacy members, preserve the
    surrounding project convention unless the task is a style migration.
-   **SHOULD** keep implementation fields private and expose behavior or
    read-only views instead of mutable state.
-   **MUST** use `const` whenever a value is a compile-time constant. If `const`
    is not possible and the value must not be reassigned after initialization,
    use `readonly` (or `static readonly` as appropriate).
-   **SHOULD** initialize fields at their declaration when that makes the
    invariant obvious and does not depend on constructor parameters.
-   **SHOULD** declare one variable per statement and initialize it near its
    first use. Avoid declarations whose only purpose is to increase distance
    from the operation that consumes the value.
-   **MUST** use the language keywords `string`, `int`, `bool`, and similar
    built-in aliases in ordinary C# code instead of `System.String`,
    `System.Int32`, and similar runtime names, unless an API or style boundary
    requires the latter.

### `var` — `CS-VAR`

Use `var` when it removes noisy or unimportant type syntax without hiding a
meaningful contract:

```csharp
var apple = new Apple();
var request = Factory.Create<HttpRequest>();
```

-   **SHOULD** use `var` when the type is obvious from `new`, an explicit cast,
    a factory with an obvious generic type, or a short, direct expression.
-   **SHOULD** use an explicit type for basic literals, compiler-resolved
    numeric expressions, and values returned by APIs whose type matters to the
    reader.
-   **MUST NOT** use a variable name such as `inputInt` to compensate for a
    hidden type. Name the value by its meaning and make the type explicit when
    it matters.
-   **MUST NOT** confuse `var` with `dynamic`. Use `dynamic` only when runtime
    binding is an intentional, documented part of the contract.
-   **SHOULD** use `var` for LINQ query results when the result is anonymous or
    a nested generic type; make the type explicit when it clarifies a public or
    non-obvious local contract.

### Nullability — `CS-NULLABILITY`

-   **MUST** follow the project's nullable context and preserve the nullability
    annotations of APIs being changed. Do not enable, disable, or suppress
    nullable analysis across an unrelated project as part of a local change.
-   **MUST** use `T?` when absence is a valid part of a nullable-aware
    reference-type or value-type contract, and handle the maybe-null state
    before dereferencing it.
-   **MUST NOT** use the null-forgiving operator (`!`) merely to silence a
    warning. Use it only when a local, documented invariant proves the value is
    non-null at that point; prefer validation or a better API contract.
-   **MUST NOT** treat nullable annotations as runtime validation. Validate JSON,
    HTTP, configuration, storage, CLI, and other external data at the boundary.
-   **SHOULD** use `?.`, `??`, and pattern matching when they express the
    absence contract clearly. Do not use them to hide an invalid state that
    should fail fast or be reported.

```csharp
string? displayName = ReadDisplayName();
string label = displayName ?? "Unknown";

if (displayName is not null) {
  Log(displayName);
}
```

### Classes, structs, and records — `CS-TYPES`

-   **SHOULD** use a class by default. Use a struct only for a small,
    value-like type whose copy semantics, equality, default value, and
    mutability are deliberately designed.
-   **MUST NOT** introduce a mutable struct merely to avoid an allocation.
    Measure before choosing a struct for performance, and account for copying,
    boxing, and mutation through properties or interfaces.
-   **MAY** use a record or record struct when value-based equality and the
    project's serialization/runtime target support it. Do not replace an
    existing class with a record without checking equality, inheritance,
    serialization, and API compatibility.
-   **SHOULD** prefer immutable or intentionally encapsulated state. Make
    mutation and ownership explicit at the boundary.

### Collections and ownership — `CS-COLLECTIONS`

-   **MUST** choose collection types according to semantics, not habit:
    distinguish a materialized container, a lazy sequence, read-only access,
    ownership transfer, and a mutable API.
-   **SHOULD** use the most restrictive useful input type. Use
    `IReadOnlyCollection<T>` or `IReadOnlyList<T>` when callers must provide a
    materialized read-only view, and `IEnumerable<T>` when deferred iteration
    is the intended contract.
-   **MUST** remember that `IEnumerable<T>` is a sequence abstraction, not a
    guarantee of immutability or single evaluation. Document or control
    multiple enumeration when it can repeat I/O, computation, or side effects.
-   **SHOULD** return the most restrictive view when ownership is retained. If
    the caller receives ownership of a mutable container, `IList<T>` may be
    appropriate; otherwise prefer a read-only interface or a named result type.
-   **MUST NOT** expose a mutable internal collection through a public property
    or return value unless transferring that ownership is intentional. Copy or
    wrap it when the boundary promises read-only access.
-   **SHOULD** prefer `List<T>` over an array when the collection can grow or
    shrink, including most mutable public API implementations.
-   **SHOULD** prefer an array when capacity is fixed and known at construction,
    and for multidimensional data. For public APIs, still consider an interface
    or read-only view as the contract.
-   **MAY** use spans, memory types, immutable collections, or specialized
    collections when the ownership, lifetime, compatibility, and performance
    contract justifies them.

### `ref`, `out`, tuples, and argument clarity — `CS-API`

-   **MUST** use `out` only for output values that are not also inputs, and put
    `out` parameters after all other parameters.
-   **SHOULD** use `ref` rarely and only when mutation or aliasing is required.
    Do not use `ref` as an unmeasured optimization for structs or mutable
    containers; use it to replace a container only when that is the contract.
-   **SHOULD** use a small tuple when the result is local and its positions are
    obvious. Prefer a named class, record, or result type for a complex,
    reusable, or public result; avoid `Tuple<>` for domain data.
-   **SHOULD** return a success boolean with an `out` struct when a struct result
    may be absent and that pattern is clearer than a nullable struct. A
    nullable struct is acceptable when it materially improves readability and
    performance is not a concern.
-   **MUST** make non-obvious arguments self-describing. Prefer named
    constants, an enum instead of a boolean with multiple meanings, named
    arguments, or an options type.

```csharp
// Hard to understand at the call site.
DecimalNumber badProduct = CalculateProduct(values, 7, false, null);

var options = new ProductOptions {
  PrecisionDecimals = 7,
  UseCache = CacheUsage.DontUseCache,
};
DecimalNumber product = CalculateProduct(
    values,
    options,
    completionDelegate: null);
```

## 7. Language features and library use

### Properties, expressions, and initialization — `CS-EXPRESSIONS`

-   **SHOULD** use an expression-bodied property for a simple, read-only
    property when it improves readability:

    ```csharp
    public int Age => _age;
    ```

-   **SHOULD** use block-bodied accessors for properties with validation,
    side effects, multiple statements, or non-trivial control flow.
-   **SHOULD NOT** use expression-bodied method definitions in code governed by
    the Google C# style. Use a block body for methods; preserve an established
    local convention when a migration is not in scope.
-   **SHOULD** use object and collection initializers for plain data and simple
    construction. Avoid an object initializer that obscures required
    constructor invariants or is used with a class/struct whose constructor
    performs meaningful setup.
-   **MUST** indent initializer and lambda bodies as nested blocks, and use only
    collection-expression syntax supported by the target language version.
-   **SHOULD** use pattern matching for type checks and casts:

    ```csharp
    if (value is string text) {
      Log(text);
    }
    ```

-   **SHOULD** make `switch` handling explicit for unknown or newly added enum
    values. Use a deliberate default, throw, or exhaustive switch expression
    according to the domain contract; do not silently invent a fallback.

### Strings — `CS-STRINGS`

-   **SHOULD** use the clearest form for the job, especially for logging and
    assertion messages. Use interpolation for short interpolated strings.
-   **SHOULD** use raw or verbatim literals when they make multi-line text or
    escaping easier to review and the target supports them.
-   **MAY** use `String.Format`, `String.Concat`, or `operator+` when that is
    clearer or required by an existing API. Do not claim a performance benefit
    without measuring the actual path.
-   **SHOULD** use `StringBuilder` for repeated or substantial concatenation,
    especially inside a loop, when allocation or throughput matters.
-   **MUST** keep culture and formatting intent explicit for user-visible,
    persisted, protocol, and diagnostic strings. Do not use the current culture
    accidentally for a machine-readable value.

### Lambdas, delegates, and callbacks — `CS-DELEGATES`

-   **SHOULD** keep a lambda to one simple expression or a couple of clear
    statements. A non-trivial or reused lambda should usually become a named
    method.
-   **SHOULD** use `Func<>` or `Action<>` for local callbacks when no semantic
    delegate type is needed. Define a named delegate or method when the
    callback is part of a meaningful public contract.
-   **MUST** call delegates with `Invoke()` and the null-conditional operator
    when the delegate may be null: `SomeDelegate?.Invoke();`.
-   **MUST** keep event-handler lifetime explicit. Use an inline lambda when it
    will never be removed; use a stable named delegate or handler when it must
    later be unsubscribed.
-   **MUST NOT** pass a bare method reference when optional or extra callback
    parameters could be interpreted incorrectly. Use an explicit lambda when it
    clarifies the arguments.

### LINQ and iteration — `CS-LINQ`

-   **SHOULD** prefer a short, readable LINQ call or imperative loop. Break up
    long chains when intermediate names, control flow, error handling, or
    side-effect boundaries matter.
-   **SHOULD** prefer member extension methods such as `items.Where(...)` to
    SQL-style query syntax unless the query syntax is materially clearer.
-   **MUST NOT** mutate external or shared state from a LINQ pipeline. Use an
    explicit loop when the operation is primarily side-effecting.
-   **SHOULD NOT** use `List<T>.ForEach` for more than one simple statement;
    prefer a loop or a named operation.
-   **MUST** understand deferred execution. Materialize with `ToList()` or a
    similar operation only when a snapshot is required, and avoid repeated
    enumeration of expensive, stateful, or external sequences.
-   **SHOULD** prefer `RemoveAll(predicate)` when the operation is simply to
    remove matching items. If other work is needed during traversal, build a
    replacement collection or use a carefully defined reverse-index loop.
-   **SHOULD** use a named collection abstraction when filtering, mapping,
    reducing, or validating the same domain collection in multiple places.
-   **SHOULD** keep a lazy generator when it avoids work that may not be needed.
    If the result is immediately materialized, filling a container directly may
    be clearer and more efficient than generating it and calling `ToList()`.

### Extension methods — `CS-EXTENSIONS`

-   **MUST** add an extension method only when the source type is unavailable or
    changing it is infeasible.
-   **MUST** limit extensions to general, core behavior that would be
    appropriate on the source type itself. Place them in a library available to
    all relevant callers; local-only extensions create discoverability and
    readability problems.
-   **SHOULD** prefer an ordinary method when it makes ownership, dependencies,
    or domain behavior clearer. Extension methods can hide a dependency and
    obfuscate the call site.

## 8. Errors, resources, async, and concurrency

### Exceptions — `CS-ERRORS`

-   **MUST** catch only exceptions the code can meaningfully handle. Prefer a
    specific exception type and, when necessary, an exception filter.
-   **MUST NOT** use `catch (Exception)` as ordinary control flow, swallow an
    exception, or leave an empty catch without a documented reason and an
    observable handling decision.
-   **MUST** preserve the original stack and cause when rethrowing or
    translating: use `throw;` for a rethrow and an inner exception or equivalent
    cause when wrapping.
-   **SHOULD** handle an exception at the boundary that can act on it. Avoid
    logging and rethrowing at every layer, which duplicates diagnostics.
-   **SHOULD** use `TryParse`, a success boolean with an `out` value, or a
    domain result when an unsuccessful outcome is expected and not exceptional.
-   **MUST** preserve validation, error taxonomy, cancellation, and retry
    semantics when extracting or refactoring a `try` block.

### Resource ownership — `CS-RESOURCES`

-   **MUST** make ownership and lifetime explicit for `IDisposable` and
    `IAsyncDisposable` resources.
-   **MUST** use `using`, `using` declarations, `await using`, or an equivalent
    `try/finally` pattern when the current scope owns a disposable resource.
-   **MUST NOT** dispose an object whose ownership belongs to a caller,
    dependency-injection container, framework, or shared cache.
-   **SHOULD** keep resource acquisition close to the scope that consumes it and
    avoid returning a resource whose lifetime is tied to a disposed dependency.
-   **MUST** preserve disposal order and asynchronous disposal behavior during
    refactors.

### Async and cancellation — `CS-ASYNC`

-   **SHOULD** use `async`/`await` and task-based APIs for I/O-bound operations.
    Propagate asynchronous behavior through the call chain instead of blocking
    on `Task.Result`, `Task.Wait()`, or equivalent sync-over-async bridges.
-   **MUST NOT** use `async void` except for framework-required event handlers.
    Return `Task` or `Task<T>` so callers can observe completion and failure.
-   **SHOULD** accept and propagate a `CancellationToken` when an operation can
    be cancelled and the surrounding API already supports cancellation.
-   **MUST** decide deliberately whether cancellation is propagated, translated,
    or treated as success. Do not catch and hide `OperationCanceledException`.
-   **MUST NOT** create unobserved fire-and-forget work. If background work is
    required, give it an owner, lifetime, cancellation path, and error handling.
-   **MAY** use `ConfigureAwait` when required by the application's context or
    library policy; follow the local convention rather than applying it
    mechanically.

### Shared state — `CS-CONCURRENCY`

-   **SHOULD** prefer immutable or thread-confined state. Make ownership,
    atomicity, visibility, and lifecycle explicit for shared mutable state.
-   **MUST NOT** lock on `this`, a publicly accessible object, a `Type`, or a
    string. Use a private, stable lock object when a monitor is appropriate.
-   **SHOULD** prefer the appropriate concurrent collection or synchronization
    primitive over hand-rolled locking. Do not assume a collection's individual
    operations make a multi-step invariant atomic.
-   **MUST** document thread-safety, blocking, cancellation, and callback
    reentrancy when those properties are part of a public or shared component's
    contract.

## 9. Structural design signals — `CS-DESIGN`

Apply `general.md` alongside this module. Its `GEN-*` rules are diagnostic
signals: do not refactor because a line count or dependency count looks unusual
in isolation. A proposed extraction must have a cohesive responsibility,
meaningful name, independently testable contract, and behavior-preserving
boundary.

-   **SHOULD** inspect a class with approximately 200 or more lines, a method
    with approximately 30 or more lines, or a constructor with approximately
    seven runtime collaborators for multiple responsibilities. These numbers
    do not require a mechanical split.
-   **SHOULD** extract a private method when an inline comment explains a named
    business operation or when a conditional block has an independently
    testable invariant. Keep a simple sequence inline when extraction hides the
    flow.
-   **SHOULD** keep controllers, handlers, endpoints, and framework entry
    points thin: validate/adapt input, delegate domain decisions, translate the
    result, and return. Do not hide domain logic in a generic service wrapper.
-   **MUST NOT** duplicate materially identical domain validation, collection
    queries, or error translation across call sites. Compare behavior, side
    effects, and change reasons before extracting; similar-looking code with
    different contracts is not automatically a common abstraction.
-   **SHOULD** introduce a named collection type when a collection owns domain
    invariants or semantic queries. Do not wrap a raw collection merely to
    rename `Where`, `Count`, or `foreach`.
-   **MUST NOT** create a `Helper`, `Manager`, `Utils`, or pass-through facade
    solely to move difficult code elsewhere. The boundary must own a coherent
    responsibility.
-   **MUST** preserve public API, serialization, reflection, DI registration,
    disposal, and exception behavior when extracting or moving code unless the
    task explicitly changes that contract.

## 10. Comments, documentation, and tests

### Comments and XML documentation — `CS-DOCUMENTATION`

-   **MUST** use XML documentation comments (`///`) for public and protected
    types and members when their purpose, constraints, side effects,
    nullability, lifecycle, or exceptions are not obvious from the signature.
-   **SHOULD** use `<summary>`, `<param>`, `<returns>`, `<exception>`, and
    `<remarks>` only when they add contract information. Use `<inheritdoc />`
    when inheriting an unchanged documented contract is the established style.
-   **MUST** keep implementation comments on separate lines, begin them with a
    space and an uppercase letter, and end a complete explanatory sentence with
    punctuation. Prefer `//` for ordinary implementation comments.
-   **MUST NOT** narrate obvious code, restate a method name, or leave stale
    comments after changing behavior. Explain why, an invariant, a constraint,
    or a surprising trade-off.
-   **SHOULD** give temporary TODOs an owner, issue, or removal condition when
    the repository has a tracking convention. Do not use TODOs to hide an
    unresolved correctness or security issue.

### Tests — `CS-TESTING`

-   **MUST** make tests deterministic and assert observable behavior, public
    contracts, errors, resource ownership, cancellation, and side effects that
    matter to the change.
-   **SHOULD** use injected clocks, fakes, stubs, or controllable schedulers
    instead of wall-clock sleeps. **MUST NOT** use `Thread.Sleep` or an
    arbitrary delay as the primary synchronization mechanism.
-   **SHOULD** test boundary nullability, malformed external data, cancellation,
    disposal, and exception translation when those paths are in scope.
-   **SHOULD** use parameterized tests for a meaningful matrix of equivalent
    cases while keeping each test's reason for failure clear.
-   **MUST NOT** weaken production visibility, nullability, validation, or error
    handling solely to make a test pass. Use an explicit seam or test fixture.

## 11. Decision examples

Use these examples only when the assignment contains the matching ambiguity.
Adapt names, libraries, and error conventions to the repository.

### File structure and imports

```csharp
using System;
using System.Collections.Generic;

namespace Example.Orders {
  public sealed class OrderProcessor {
    private readonly IOrderStore _store;

    public OrderProcessor(IOrderStore store) {
      _store = store;
    }
  }
}
```

### `var` versus an explicit type

```csharp
var request = new HttpRequest();
bool succeeded = TryLoad(request, out Order? order);

// The return type is part of what the reader needs to know.
IReadOnlyList<Order> orders = _store.LoadRecent();
```

### Nullability at a boundary

```csharp
using System.IO;

public Order ParseOrder(string payload) {
  Order? order = _parser.TryParse(payload);
  if (order is null) {
    throw new InvalidDataException("The order payload is invalid.");
  }

  return order;
}
```

Nullable annotations communicate the intended contract; parsing or validation
still has to establish that contract at runtime.

### Clear arguments

```csharp
var options = new RetryOptions {
  MaxAttempts = 3,
  Mode = RetryMode.Exponential,
};

await sender.SendAsync(
    message,
    options,
    cancellationToken: cancellationToken);
```

## 12. Verification checklist

Before reporting completion, verify the checks applicable to the assignment:

-   The requested behavior, public API, serialization/reflection shape,
    nullability, disposal, cancellation, concurrency, and error semantics are
    preserved or intentionally changed.
-   The effective C# language version, target framework, nullable context,
    generated-code boundary, and local formatter/analyzer conventions were
    respected.
-   Relevant `CS-*` and `GEN-*` rule IDs were applied; thresholds were treated
    as signals rather than automatic refactoring commands.
-   Imports, namespaces, file/type relationships, member ordering, modifiers,
    attributes, access modifiers, and naming are coherent.
-   `var`, collection interfaces, arrays/lists, tuples, `ref`/`out`, lambdas,
    LINQ, extension methods, and expression bodies match the intended contract.
-   Exceptions are handled at the right boundary; stack/cause and cancellation
    are preserved; owned resources are disposed exactly once.
-   Configured formatter, analyzer, compiler/build, focused tests, and relevant
    regression tests were run, or each unavailable/skipped check is explicitly
    reported.
-   The final diff contains no unrelated reformatting, generated artifacts,
    secret material, silent public-contract changes, or stale documentation.
-   Any accepted deviation includes its rule ID, location, reason, impact, and
    verification evidence. The final report lists exact changed paths and
    unresolved risks, using `[]` when none remain.

## Sources

-   [Google C# Style Guide](https://google.github.io/styleguide/csharp-style.html)
-   [Microsoft .NET coding conventions](https://learn.microsoft.com/en-us/dotnet/csharp/fundamentals/coding-style/coding-conventions)
-   [Nullable reference types](https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/builtin-types/nullable-reference-types)
-   [Asynchronous programming scenarios](https://learn.microsoft.com/en-us/dotnet/csharp/asynchronous-programming/async-scenarios)
-   [Cross-language structural rules](general.md)
