# Google C++ Style Guide — Agent Summary

Use this module when creating, reviewing, or modifying C++ code. It is a
concise operational summary of the [Google C++ Style
Guide](https://google.github.io/styleguide/cppguide.html), not a replacement
for the full guide.

## How to apply this module

Use the following priority order:

1. Explicit user requirements, compatibility constraints, and build settings.
2. Established conventions in the repository and the files being modified.
3. This module and the upstream Google C++ Style Guide.

-   **MUST** preserve observable behavior, public API/ABI, and required
    platform or compiler compatibility unless the task explicitly changes
    them.
-   **MUST** follow the local style when modifying existing non-conforming
    code, unless the task is an intentional migration.
-   **SHOULD** use repository-provided formatting, lint, and build tools when
    they exist. Do not introduce a new tool or reformat unrelated code merely
    to satisfy this summary.
-   **MAY** deviate from a heuristic when the deviation makes the code safer,
    clearer, or compatible with a documented constraint. Record a material
    deviation and its reason instead of silently waiving it.

In this document, **MUST** is a requirement, **SHOULD** is the default choice,
and **MAY** is a permitted choice.

## 1. Language version and file names

-   **Version:** Google code targets C++20 and does not use C++23 features.
    Follow the repository's actual language standard when it differs, and do
    not introduce a feature newer than that standard.
-   **Extensions:** Do not use non-standard compiler extensions. A portability
    wrapper supplied and approved by the project is the exception.
-   **Files:** C++ implementation files use `.cc`, headers use `.h`, and files
    intended for textual inclusion use `.inc` sparingly.
-   **File names:** Use lowercase names with underscores or dashes, following
    the local convention. If no convention exists, prefer underscores. Choose
    specific names and avoid collisions with common system headers.

## 2. Naming

Choose names that expose intent to a reader who is unfamiliar with the local
implementation. Avoid unexplained abbreviations and do not shorten words by
deleting internal letters. Capitalize an abbreviation as one word, for example
`StartRpc()`, not `StartRPC()`.

-   **Types:** PascalCase with no underscores: `MyClass`, `MyEnum`,
    `PropertiesMap`.
-   **Concepts and type template parameters:** Use the type-name convention,
    for example `Sortable` and `T`.
-   **Non-type template parameters:** Follow variable or constant naming,
    depending on whether the parameter represents a value or a fixed limit.
-   **Functions:** PascalCase: `GetValue()`, `OpenFileOrDie()`.
-   **Accessors and mutators:** Use `snake_case`: `count()` and
    `set_count(value)`.
-   **Variables:** Use `snake_case`. Class data members, including static data
    members that are not constants, end with an underscore: `member_`.
-   **Constants and enumerators:** Use `kPascalCase`: `kMaxRetries`, `kOk`.
    Variables with static storage duration use the same constant-style form.
-   **Namespaces:** Use unique, project-based `snake_case` names. Avoid
    top-level names that can collide with another project.
-   **Macros:** Avoid them. If one is unavoidable, use a project-specific
    `ALL_CAPS` name such as `MYPROJECT_FEATURE_FLAG`.
-   **Integers:** Use `int` for ordinary integers. Use an exact-width type such
    as `int64_t` when size or range matters, and use `size_t` or `ptrdiff_t`
    when the API requires it. Do not use an unsigned type merely to express
    non-negativity; use it for bit patterns or modular arithmetic when that is
    the actual meaning.
-   **Floating point:** Use `float` or `double`; avoid `long double` for
    portability.

## 3. Headers and dependencies

### Header requirements

-   Headers **MUST** be self-contained: they compile when included on their
    own and include everything needed for their declarations and definitions.
-   Use a project/path-based `#define` guard. For `foo/src/bar/baz.h` in
    project `foo`, use:

    ```cpp
    #ifndef FOO_BAR_BAZ_H_
    #define FOO_BAR_BAZ_H_

    // Declarations.

    #endif  // FOO_BAR_BAZ_H_
    ```

-   Apply Include What You Use: include the header that directly provides each
    external declaration or definition. Do not rely on transitive includes.
-   A `.cc` file normally has a corresponding `.h`; unit tests and small
    executables are common exceptions.
-   Put template definitions and required inline or `constexpr` definitions in
    a header. Keep public inline definitions short, usually ten lines or fewer,
    and ensure every header definition is ODR-safe.

### Forward declarations

Avoid forward declarations when a direct include is practical. Never forward
declare entities that the project does not own, and never declare anything in
`namespace std`. A forward declaration of a project-owned type may be used
when it materially reduces compile-time cost or preserves a necessary
dependency boundary; do not add indirection solely to avoid an include.

### Include order

For a `.cc` file, put its related header first. Then separate non-empty groups
with one blank line and order each group alphabetically:

1. The related header.
2. C headers and system headers, including POSIX or Windows headers and rare
   angle-bracketed third-party `.h` headers such as `<Python.h>`.
3. C++ standard-library headers without a file extension, such as `<string>`.
4. Other library headers.
5. Project headers.

Use angle brackets for standard and system headers. Use the project's source
tree path for project headers; do not use `.` or `..` aliases.

## 4. Formatting

-   Use spaces, never tabs, and indent two spaces per block. Do not add
    trailing whitespace.
-   Keep code lines at or below 80 characters. A line may exceed the limit only
    when splitting would damage a URL, an unsplittable string literal, an
    include, a header guard, or a similarly clear exception.
-   Use UTF-8 for rare non-ASCII source text. Avoid the `u8` prefix when
    possible because its semantics differ across C++ versions.
-   Put a space after control keywords and before an opening brace:
    `if (condition) {`. Do not add padding inside parentheses.
-   Use braces for control-flow blocks by default. A brief single-statement
    exception is allowed only when the local style permits it; never omit
    braces in a way that makes an `if`/`else` or `do`/`while` pairing unclear.
-   Function definitions keep the opening brace on the last declaration line,
    not on a line by itself:

    ```cpp
    ReturnType ClassName::FunctionName(
        Type first,
        Type second) {
      return result;
    }
    ```

-   Wrap calls at the opening parenthesis or indent a fully wrapped argument
    list by four spaces. Align continuation arguments when practical, and do
    not insert padding just inside parentheses.
-   When a constructor initializer list must wrap, put the colon on the next
    line with four spaces of indentation and align subsequent initializers:

    ```cpp
    MyClass::MyClass(int value)
        : value_(value),
          other_(value + 1) {}
    ```

-   Do not indent the contents of a namespace. Close multi-line namespaces with
    a comment, for example `}  // namespace project`.
-   Keep `public:`, `protected:`, and `private:` in that order, indented one
    space inside a class; members use the normal two-space indentation.
-   Keep spaces around assignment and ordinary binary operators, and no space
    between a unary operator and its operand. Do not put spaces inside
    `vector<int>`.
-   Use `char* pointer` and `const T& reference`; the `*` or `&` attaches to
    the type, not the variable name.
-   Do not needlessly parenthesize a return expression: use `return result;`.
    Parentheses are appropriate when they clarify a complex expression.
-   Put the `#` of every preprocessor directive at the beginning of the line,
    even when the directive appears inside an indented block.
-   Use a `default` case for switches that are not exhaustive enum switches.
    An enum switch may omit `default` when compiler exhaustiveness diagnostics
    are intentionally relied upon. Annotate intentional fallthrough with
    `[[fallthrough]];`.
-   Floating-point literals normally include a radix point and digits on both
    sides, such as `1.0f` and `-0.5`.
-   Use vertical whitespace sparingly: separate related chunks, not every code
    block.

## 5. Classes, structs, and operators

### Class design

-   Use `struct` for passive data with public fields and no invariants that
    direct field access could break. Use `class` when encapsulation, behavior,
    or invariants matter. Prefer a named struct over `std::pair` or
    `std::tuple` when the fields have meaningful names.
-   Class data members are `private` unless they are constants. Limit
    `protected` to member functions that subclasses genuinely need.
-   Order declarations as follows, omitting empty access sections:
    1. Types and type aliases.
    2. Non-static data members in a struct, when applicable.
    3. Static constants.
    4. Factory functions.
    5. Constructors and assignment operators.
    6. Destructor.
    7. Other functions.
    8. Other data members.
-   Do not put large method bodies in the class definition. Inline only trivial,
    very short, or technically performance-critical functions.
-   Mark single-argument constructors and conversion operators `explicit`.
    A constructor taking a single `std::initializer_list` may omit `explicit`
    when copy-initialization is intentionally supported.
-   Avoid virtual calls in constructors. When initialization can fail and
    exceptions are disabled, use the project's factory, status, or `Init`
    pattern instead of leaving a partially initialized object.

### Copying, moving, and inheritance

-   Make the public API's copy and move behavior clear. Support copying or
    moving only when the semantics are meaningful and the cost is expected.
-   Default or delete special members when that communicates the intended
    semantics. If one copy operation is explicitly declared or deleted, make
    the other copy operation explicit as well; apply the same rule to move
    operations. Do not implement the Rule of Five mechanically when the
    compiler-generated operations are correct.
-   Prefer composition over implementation inheritance. When inheriting, use
    `public` inheritance and keep the relationship a genuine “is-a” relation.
-   Mark overrides with exactly one of `override` or, when appropriate, `final`;
    do not repeat `virtual` on an override. Multiple implementation
    inheritance is strongly discouraged.

### Operators

Overload operators only when the result is conventional and unsurprising.
Binary operators generally work best as non-members. Never overload `&&`, `||`,
the comma operator, or unary `&`. Do not define or use user-defined literals.

## 6. Functions and APIs

-   Prefer a small, focused function. A function longer than about 40 lines is
    a signal to look for a cohesive extraction, not an automatic refactoring
    command.
-   Prefer return values over output parameters. Return by value when practical;
    otherwise return by reference. Return a raw pointer only when nullability
    is part of the contract.
-   Required input parameters are usually values or `const` references. Use a
    non-`const` reference for a required output or input/output parameter, a
    `const` pointer for an optional input, and a non-`const` pointer for an
    optional output or input/output parameter.
-   Put input-only parameters before output parameters. Treat this as a default,
    not a reason to break a coherent existing API.
-   Use `std::string_view` or `std::span` for non-owning views when their
    lifetime and invalidation rules are clear. Do not let a borrowed reference
    or view outlive the object it refers to.
-   Do not design a function to require a reference argument to outlive the
    call. If a member retains an input pointer or reference, document its
    nullability and lifetime requirement at the declaration.
-   Use overloads only when a reader can understand the behavior from the call
    site without resolving complex overload-selection rules. Document a
    related overload set with one umbrella comment before the first overload.
-   Do not use default arguments on virtual functions. Elsewhere, use them only
    when the default is fixed and improves the declaration's readability; use
    overloads when the default would be surprising.
-   Keep the ordinary leading-return-type syntax in most functions. Use a
    trailing return type only when it is required or substantially clearer,
    which is rare. Public functions in headers should almost never deduce their
    return type.
-   Put attributes such as `[[nodiscard]]` at the beginning of a declaration,
    before the return type.
-   Mark methods `const` when they do not change logical state. `const`
    operations should be safe to call concurrently with one another; document
    the class as thread-unsafe when that guarantee does not hold.

## 7. Scope, lifetime, and ownership

### Scope and linkage

-   Put code in a named namespace whenever possible. Do not use a
    using-directive such as `using namespace foo`, and never add declarations
    to `namespace std`. A targeted using-declaration may be local to a `.cc`
    file or function when it improves readability.
-   Give file-local definitions internal linkage with an unnamed namespace or
    `static` in `.cc` files. Do not use either mechanism in headers.
-   Declare locals in the narrowest useful scope and initialize them at the
    declaration. A loop may justify constructing an expensive reusable object
    outside the loop; make that choice based on lifetime and performance.

### Static and thread-local objects

-   Objects with static storage duration must be trivially destructible. Prefer
    `constexpr` for true constants and `constinit` to enforce constant
    initialization. Avoid non-local dynamic initialization.
-   Do not use global or static `std::string`, dynamic containers, or smart
    pointers. A function-local static may use dynamic initialization when the
    repository's policy permits it; review its lifetime and thread safety.
-   Namespace- or class-scope `thread_local` variables must use `constinit` (or
    `constexpr` where appropriate). Function-local `thread_local` variables do
    not have the same initialization-order issue, but their destruction and
    per-thread memory cost still require review.

### Ownership

-   Prefer values and RAII. Every dynamically allocated resource must have a
    clear owner.
-   Use `std::unique_ptr` for exclusive ownership and move it to transfer
    ownership. Use `std::shared_ptr` only when shared ownership is genuinely
    required and its cost, lifetime, and cycle risks are understood.
-   Raw pointers and references should normally be non-owning. Make nullability,
    retained lifetime, and invalidation rules explicit in the API or comments.
-   Avoid manual `new`/`delete` in application code. Never use `std::auto_ptr`.

## 8. Modern C++ and library use

### Type deduction and templates

-   Use `auto` only when deduction makes the code clearer or safer, such as
    iterator types or `std::make_unique` results. Do not use it merely to avoid
    writing an informative type.
-   Keep public API types explicit. Avoid deduced return types in public headers
    and do not use `auto` parameters in non-lambda functions; use named template
    parameters instead.
-   Structured bindings are useful for pairs, tuples, and map entries. Give
    bindings meaningful names and comment the underlying field names when the
    binding order would otherwise be unclear.
-   Use class template argument deduction only when the resulting type is
    obvious and the deduction guide is intentional. Prefer explicit types when
    deduction hides important information.
-   Prefer standard concepts and `requires(Condition)` over `std::enable_if`.
    Use concepts sparingly, avoid `template<Concept T>` in this style, and do
    not expose a new concept in a public header without a clear API benefit.
-   Avoid complicated template metaprogramming. Isolate unavoidable machinery
    in implementation details, document the resulting constraints, and keep
    compiler diagnostics understandable.

### Initialization, casts, and lambdas

-   Choose `=`, `()`, or `{}` consistently with the surrounding code. Braced
    initialization prevents narrowing, but be aware that a non-empty brace list
    prefers an `std::initializer_list` constructor. C++20 designated
    initializers are allowed only in declaration order.
-   Use C++-style casts. Prefer brace initialization for arithmetic conversion,
    `static_cast` for ordinary explicit conversions, and `std::bit_cast` for
    same-size bit reinterpretation. Avoid C-style casts and reserve
    `reinterpret_cast` for carefully reviewed low-level code.
-   Use `nullptr` for pointers and `\0` for the null character, never `NULL` or
    the integer literal `0` for those meanings.
-   Use `sizeof(variable)` when measuring a particular variable; use
    `sizeof(type)` only when the type itself is the subject of the operation.
-   Use prefix increment and decrement unless the value of the postfix
    expression is required.
-   Use `constexpr` for true compile-time constants or functions that support
    them, `constinit` for constant initialization of non-constant objects, and
    `consteval` only when compile-time evaluation is mandatory. Do not use them
    merely to force inlining.
-   Specify `noexcept` when it is useful and correct, especially for move
    operations. Do not add a complicated specification that does not express a
    meaningful contract.
-   Use lambdas where they clarify a local callback. Prefer explicit captures
    when a lambda can escape its scope. Default captures are acceptable only
    when the lambda is short and its lifetime is obviously bounded; remember
    that capturing a pointer by value does not extend the pointee's lifetime.

### Error handling, RTTI, and libraries

-   Do not write C++ exception-based control flow in code governed by Google's
    policy. Use the repository's status, error-code, or optional-value
    conventions. Integrate third-party exceptions only under an explicit
    project boundary and policy.
-   Avoid RTTI (`dynamic_cast` and `typeid`) in production design. It is allowed
    when needed in tests or a carefully justified hierarchy. Do not replace it
    with a hand-rolled type-tag workaround.
-   Prefer the standard library and libraries already approved by the project.
    Do not add a third-party dependency for convenience without checking its
    ownership, license, security, and maintenance policy.
-   Use streams where appropriate and keep their use simple, especially for
    logging and test diagnostics. Overload `<<` only for value-like types and
    output the user-visible value rather than implementation details. Follow
    the repository's logging and formatting library when one exists.
-   Avoid macros, especially in headers and public APIs. Prefer functions,
    enums, `constexpr`, or `const` variables. If a local macro is unavoidable,
    define it immediately before use, give it a unique project prefix, and
    `#undef` it immediately after use. Header guards are the exception.
-   In code following Google's complete restrictions, do not use `<ratio>`,
    `<cfenv>`, `<fenv.h>`, or `<filesystem>`. A higher-priority repository
    policy may establish a different approved alternative.
-   Follow project-approved portability wrappers instead of directly using
    architecture-specific intrinsics, inline assembly, or other extensions.

## 9. Comments and documentation

-   New files follow the repository's license boilerplate and file-comment
    policy. Do not add author lines unless the project explicitly requires
    them.
-   Add a comment for every non-obvious class or struct explaining its purpose,
    intended use, invariants, and synchronization assumptions.
-   Function declaration comments explain what the function does and how to use
    it. Mention meaningful inputs, outputs, nullability, retained references,
    mutation, lifetime, and performance implications. Start with a verb phrase,
    such as “Returns …”. Simple accessors may omit a comment.
-   Implementation comments explain why tricky code exists or how an important
    invariant is maintained. Do not narrate code that a better name or smaller
    function would make obvious.
-   Document non-obvious data-member invariants and sentinel values. Global
    variables need a comment explaining their purpose and why they are global.
-   Use `//` or `/* */` consistently. Write comments as readable prose with
    correct capitalization and punctuation.
-   A `TODO` includes `TODO` plus a bug ID, owner, issue, or other useful
    identifier. Include a specific date or event when the TODO is time-bound.

## 10. Verification checklist

Before reporting a C++ change as complete:

-   Confirm the repository's language version, local formatting rules, and
    relevant build or lint commands.
-   Check changed headers for self-containment, direct includes, guard naming,
    and correct include order.
-   Check public APIs for ownership, nullability, lifetime, copy/move, and
    thread-safety contracts.
-   Check changed code for naming, braces, indentation, line length, namespace
    scope, casts, and accidental macro or exception use.
-   Run the narrowest applicable formatter, lint, build, and tests; do not hide
    dependency installation or unrelated environment changes in a validation
    command.
-   Inspect the final diff for unrelated reformatting, stale comments, and
    undocumented material deviations.

**Be consistent.** When a local convention conflicts with this summary, follow
the local convention and preserve the reason for the difference.
