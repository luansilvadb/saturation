# C# Style Rules

Target: modern .NET with nullable-aware C#.

Run the repository's configured formatter and analyzers. They own brace placement,
indentation, wrapping, blank lines, modifier order, and member order. The rules below
cover the decisions a formatter cannot express.

## Files, names, and declarations

### Source files and imports — `CS-SOURCE`

- **MUST** use `.cs` files with PascalCase file and directory names and one core type per file.
- **SHOULD** name the file after its primary type; tightly coupled types and partials are fine.
- **MUST** put ordinary `using` directives before the namespace declaration and outside it.
- **MUST** order imports `System` first, then alphabetically within the repository's groups.
- **MUST NOT** add an unused import or rely on a transitive import where a direct one exists.
- **SHOULD NOT** alias a long type name; a long alias signals a missing named domain type.
- **MAY** use global usings, file-scoped namespaces, and aliases where the project already does.
- **MUST** use PascalCase namespaces with at most two levels of nesting and globally unique top-level names.
- **MUST NOT** force folder layout to match namespaces.

### Naming — `CS-NAMING`

- **MUST** use PascalCase for types, enums, methods, events, public fields, and properties.
- **MUST** use camelCase for locals, parameters, and local function variables.
- **MUST** use `_camelCase` for private, protected, and internal fields and properties.
- **MUST** prefix interfaces with `I` and name type parameters with a `T` prefix (`TKey`, `TValue`).
- **MUST** treat acronyms as words (`HttpClient`, `CustomerId`) unless a contract requires otherwise.
- **MUST** keep constants in PascalCase; `const` and `static readonly` never justify `UPPER_SNAKE_CASE`.
- **SHOULD** name by domain meaning, avoid unexplained abbreviations, and use `IsReady` predicates.
- **MAY** preserve test, serialization, generated-code, interop, and framework naming.

### Declarations — `CS-DECLARATIONS`

- **MUST** declare visibility explicitly on new top-level types and on public and private members.
- **MUST** use `const` for compile-time constants and `readonly` for values fixed after initialization.
- **MUST** use `string`, `int`, and `bool` instead of `System.String`, `System.Int32`, and `System.Boolean`.
- **SHOULD** keep implementation fields private and expose behavior or read-only views.
- **SHOULD** initialize a field at its declaration when the invariant does not depend on the constructor.

### Locals and `var` — `CS-VAR`

- **SHOULD** use `var` when the type is obvious from `new`, a cast, or a factory type argument.
- **SHOULD** use an explicit type for literals, numeric expressions, and contract-bearing returns.
- **SHOULD** use `var` for anonymous and deeply nested generic results.
- **MUST NOT** hide a meaningful type behind `var` or compensate with a name like `inputInt`.
- **MUST NOT** confuse `var` with `dynamic`, which is for documented runtime binding only.
- **SHOULD** declare one variable per statement, initialized near first use.

## Contracts and language use

### Nullability — `CS-NULLABILITY`

- **MUST** follow the project's nullable context and preserve the annotations of changed APIs.
- **MUST** use `T?` where absence is part of the contract, and handle the maybe-null state.
- **MUST** validate JSON, HTTP, configuration, storage, and CLI input at the boundary.
- **MUST NOT** use the null-forgiving `!` to silence a warning without a documented invariant.
- **SHOULD** use `?.`, `??`, and pattern matching to express absence, not to hide an invalid state.

### Type choice — `CS-TYPES`

- **SHOULD** use a class by default; a struct needs designed copy, equality, and default semantics.
- **MUST NOT** introduce a mutable struct to avoid an allocation.
- **MAY** use a record or record struct where value equality and the target framework support it.
- **MUST NOT** replace a class with a record without checking equality and serialization compatibility.

### Collections and ownership — `CS-COLLECTIONS`

- **MUST** choose the contract by intent: `IReadOnlyList<T>` for a read-only view, `IEnumerable<T>` for deferred iteration.
- **MUST** use `IList<T>` only when the caller takes ownership, and return the most restrictive view that fits.
- **MUST** treat `IEnumerable<T>` as a sequence, not a promise of immutability or single evaluation.
- **MUST NOT** expose a mutable internal collection publicly unless ownership transfers; copy or wrap it.
- **SHOULD** prefer `List<T>` when the collection can grow and an array when capacity is fixed.

### Parameters and results — `CS-API`

- **MUST** use `out` only for outputs, placed after all other parameters.
- **SHOULD** use `ref` only where mutation or aliasing is the contract, not as an unmeasured optimization.
- **SHOULD** use a small tuple only for a local result with obvious positions.
- **MUST NOT** use `Tuple<>` for domain data; prefer a named class, record, or result type.
- **MUST** make a non-obvious argument self-describing with named constants, an enum, or an options type.

### Properties and expressions — `CS-EXPRESSIONS`

- **MUST** use only syntax and APIs supported by the declared language version and target framework.
- **SHOULD** use an expression body only for a single-expression member; use a block body otherwise.
- **SHOULD** use object and collection initializers for plain data, not where a constructor enforces invariants.
- **SHOULD** make `switch` over an enum explicit with a deliberate default, a throw, or an exhaustive expression.

### Strings and culture — `CS-STRINGS`

- **MUST** keep culture explicit for user-visible, persisted, and protocol strings.
- **SHOULD** keep a structured log message a constant template with named placeholders.

### Delegates and events — `CS-DELEGATES`

- **MUST** invoke a possibly null delegate as `SomeDelegate?.Invoke()`.
- **MUST** keep event-handler lifetime explicit: a stable named handler when it is unsubscribed later.

### LINQ and iteration — `CS-LINQ`

- **MUST NOT** mutate external or shared state from a query pipeline; use an explicit loop for side effects.
- **SHOULD** materialize with `ToList()` only when a snapshot is required, and avoid repeated enumeration
  of expensive or external sequences.
- **SHOULD** break a long chain into named steps where control flow or error handling is involved.
- **SHOULD** use `RemoveAll(predicate)` for a pure removal and a replacement collection otherwise.

### Extension methods — `CS-EXTENSIONS`

- **MUST** add an extension method only when the source type is unavailable or cannot be changed.
- **MUST** limit extensions to general behavior that belongs to the source type, in a shared library.
- **SHOULD** prefer an ordinary method where it makes ownership or dependencies clearer.

## Failures, resources, and concurrency

### Exceptions — `CS-ERRORS`

- **MUST** catch only exceptions the code can act on, with a specific type or an exception filter.
- **MUST NOT** use `catch (Exception)` as control flow, swallow an exception, or leave an empty catch.
- **MUST** preserve the original stack and cause: `throw;` to rethrow, an inner exception to wrap.
- **MUST** preserve validation, error taxonomy, cancellation, and retry semantics when moving a `try` block.
- **SHOULD** handle an exception at the boundary that can act on it, not at every layer.
- **SHOULD** use `TryParse`, a success boolean with `out`, or a domain result for expected failure.

### Resource disposal — `CS-RESOURCES`

- **MUST** make ownership and lifetime explicit for `IDisposable` and `IAsyncDisposable`.
- **MUST** use `using`, a `using` declaration, `await using`, or `try/finally` when the scope owns it.
- **MUST NOT** dispose an object owned by the caller, the DI container, the framework, or a cache.
- **MUST** preserve disposal order and asynchronous disposal behavior during a refactor.

### Async and cancellation — `CS-ASYNC`

- **MUST** return `Task` or `Task<T>`; `async void` is limited to framework event handlers.
- **MUST NOT** block with `Task.Result`, `Task.Wait()`, or another sync-over-async bridge; propagate
  `async` and `await` up the call chain.
- **MUST** decide whether cancellation propagates, is translated, or counts as success, and never catch
  and hide `OperationCanceledException`.
- **MUST NOT** start unobserved fire-and-forget work without an owner, lifetime, and error handling.
- **SHOULD** accept and propagate a `CancellationToken` where the surrounding API supports it.
- **MAY** use `ConfigureAwait` where the application or library policy requires it.

### Shared state — `CS-CONCURRENCY`

- **SHOULD** prefer immutable or thread-confined state with explicit ownership and visibility.
- **MUST NOT** lock on `this`, a publicly accessible object, a `Type`, or a string.
- **MUST NOT** assume individual operations on a concurrent collection make a multi-step update atomic.
- **SHOULD** prefer a concurrent collection or synchronization primitive to hand-rolled locking.
- **MUST** document thread-safety, blocking, cancellation, and callback reentrancy in a shared contract.

## Documentation, tests, and change safety

### Documentation — `CS-DOCUMENTATION`

- **MUST** document public and protected members with `///` XML where the contract is not obvious.
- **MUST** keep an implementation comment on its own line, starting with a space and an uppercase letter.
- **MUST NOT** narrate obvious code, restate the member name, or leave a stale comment.
- **SHOULD** give a TODO an owner, an issue, or a removal condition; never hide a defect behind one.

### Tests — `CS-TESTING`

- **MUST** make tests deterministic and assert observable behavior, contracts, errors, and side effects.
- **MUST NOT** weaken production visibility, nullability, validation, or error handling to pass a test.
- **MUST NOT** use `Thread.Sleep` or an arbitrary delay as the primary synchronization mechanism; use an
  injected clock, fake, stub, or controllable scheduler instead.
- **SHOULD** test boundary nullability, malformed input, cancellation, and disposal where in scope.
- **SHOULD** use parameterized tests for a meaningful matrix of equivalent cases.

### Refactoring — `CS-CHANGE`

- **MUST** preserve evaluation order, exception behavior, disposal, cancellation, and public API shape
  when extracting or moving code, unless the task changes that contract.
