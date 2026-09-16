# C++ Style Guide

Language target: C++20. Follow the standard the repository configures; no
non-standard compiler extension outside a project-provided wrapper.

### Formatter — `CPP-FORMATTING`

- **MUST** run the repository's configured formatter on every changed file; it
  decides indentation, line breaking, braces, include order, and whitespace.
- **MUST NOT** reformat code you did not otherwise touch.
- **SHOULD** mark an intentional fallthrough with `[[fallthrough]];` and omit
  `default:` only in exhaustive enum switches that rely on compiler diagnostics.

### Naming — `CPP-NAMING`

- **MUST** use `PascalCase` for types, concepts, and functions, `snake_case` for
  variables, namespaces, and accessors, `kPascalCase` for constants and
  enumerators, and a trailing underscore for data members (`member_`).
- **MUST** capitalize an abbreviation as one word, as in `StartRpc()`.
- **SHOULD** use `.cc`, `.h`, and `.inc` (textual inclusion only) with lowercase
  underscore names that avoid collision with system headers.
- **SHOULD** use `int` for ordinary integers, an exact-width type when size or
  range matters, and unsigned only for bit patterns or modular arithmetic.
- **SHOULD** use `float` or `double`, not `long double`, for portability.

### Headers — `CPP-HEADERS`

- **MUST** keep a header self-contained and ODR-safe: it compiles alone, carries
  the template, `inline`, and `constexpr` definitions its users need; every
  entity has one definition.
- **MUST** include what you use and never rely on a transitive include.
- **SHOULD** use a project/path-based guard such as `FOO_BAR_BAZ_H_` for
  `foo/src/bar/baz.h`, and give each `.cc` its own `.h`.
- **SHOULD** prefer a direct include; **MAY** forward declare a project-owned
  type that materially cuts compile time, and **MUST NOT** forward declare a
  type the project does not own or declare anything in `namespace std`.

### Classes and operators — `CPP-CLASSES`

- **SHOULD** use `struct` for passive data with public named fields and no
  invariants, `class` when encapsulation or invariants matter, and a named
  struct over `std::pair`.
- **MUST** keep data members `private` unless they are constants, and limit
  `protected` to what subclasses need.
- **SHOULD** keep method bodies out of the class definition except trivial or
  technically performance-critical functions.
- **MUST** mark a single-argument constructor and a conversion operator
  `explicit`; **MAY** omit it on a single-`std::initializer_list` constructor
  that intends copy-initialization.
- **MUST NOT** call a virtual function from a constructor or destructor.
- **SHOULD** use the project's factory or `Init` pattern when construction can
  fail and exceptions are disabled.
- **SHOULD** make copy and move behavior explicit, declare both operations of a
  pair once either is user-declared, and default special members rather than
  write the Rule of Five.
- **SHOULD** prefer composition over implementation inheritance, use `public`
  inheritance for a genuine is-a relationship, and mark an override with exactly
  one of `override` or `final`; **MUST NOT** use multiple implementation
  inheritance.
- **SHOULD** comment a class with its purpose, invariants, and synchronization
  assumptions.
- **SHOULD** overload an operator only when its meaning is conventional for the
  type, with binary operators as non-members.
- **MUST NOT** overload `&&`, `||`, the comma operator, or unary `&`, and
  **MUST NOT** define or use user-defined literals.

### Functions — `CPP-FUNCTIONS`

- **MUST** pass a required input by value or `const` reference, a required
  output by non-`const` reference, an optional input by `const` pointer, and an
  optional output by non-`const` pointer.
- **SHOULD** put input-only parameters before outputs and return a value rather
  than write through an output parameter.
- **MUST NOT** require an argument to outlive the call; **MUST** document
  nullability and retained lifetime at the declaration when a member stores an
  input pointer or reference.
- **MAY** return a raw pointer when nullability is part of the contract, and
  **SHOULD** never let a public header function deduce its return type.
- **SHOULD** keep the leading return type and use a trailing return type only
  when required or substantially clearer.
- **MUST** put attributes such as `[[nodiscard]]` before the return type.
- **MUST** mark a method `const` when it does not change logical state and keep
  `const` operations safe to call concurrently; document the class as
  thread-unsafe otherwise.
- **SHOULD** add `noexcept` where it is correct and useful, especially on move
  operations.
- **SHOULD** use an overload only when the call site alone makes the selected
  behavior clear, and **MUST NOT** use a default argument on a virtual function.
- **SHOULD** use `std::string_view` or `std::span` for a non-owning view whose
  lifetime and invalidation rules are clear at the call site; a borrowed
  pointer, reference, or view **MUST NOT** outlive its referent.

### Scope, storage, and ownership — `CPP-SCOPE`

- **MUST** put declarations in a named namespace and **MUST NOT** add to
  `namespace std` or write `using namespace foo`; a targeted using-declaration
  stays local to one file.
- **SHOULD** give a file-local entity internal linkage with an unnamed namespace
  or `static` in a `.cc` file, never in a header, and declare a local in the
  narrowest scope that works, initialized at the declaration.
- **MUST** keep a static-storage-duration object trivially destructible and
  **MUST NOT** use a global or static `std::string`, dynamic container, or smart
  pointer.
- **SHOULD** use `constexpr` for a true constant and `constinit` to enforce
  constant initialization; **MUST** declare a namespace- or class-scope
  `thread_local` `constinit` or `constexpr`.
- **MAY** use dynamic initialization in a function-local static when the
  repository permits it, after checking its lifetime and thread safety.
- **SHOULD** hold resources by value under RAII and give each dynamic allocation
  one clear owner.
- **SHOULD** use `std::unique_ptr` for exclusive ownership and `std::shared_ptr`
  only when shared ownership is genuinely required and its cost and cycle risk
  is understood; move a `unique_ptr` to transfer ownership.
- **MUST** treat a raw pointer or reference as non-owning and state its
  nullability and lifetime; **MUST NOT** call `new` or `delete` directly in
  application code.

### Modern C++ — `CPP-MODERN`

- **SHOULD** use `auto` only where deduction is clearer or safer, such as an
  iterator type, **MAY** use class template argument deduction when the type is
  obvious, and **MUST NOT** use `auto` parameters in non-lambda functions.
- **MAY** use a structured binding for a pair, tuple, or map entry, with
  meaningful names.
- **SHOULD** prefer concepts and `requires` over `std::enable_if`, avoid
  `template<Concept T>` in this style, and isolate unavoidable metaprogramming
  behind documented implementation details.
- **MUST** use a designated initializer only in declaration order.
- **SHOULD** choose `=`, `()`, or `{}` consistently with surrounding code,
  knowing that a non-empty brace list prefers an `std::initializer_list`
  constructor.
- **SHOULD** use `constexpr` for a true compile-time constant or function and
  `constinit` for constant initialization; **MAY** use `consteval` when
  compile-time evaluation is mandatory.
- **MUST** use `nullptr` for a pointer and `'\0'` for the null character, never
  `NULL` or `0`, and **SHOULD** keep a cast explicit: braced initialization for
  arithmetic conversion, `static_cast` for an ordinary explicit conversion, and
  `std::bit_cast` for same-size bit reinterpretation.

### Libraries, errors, and macros — `CPP-LIBRARIES`

- **MUST NOT** use exceptions or exception-based control flow outside a
  project-approved boundary; use the repository's status or error-code
  conventions.
- **SHOULD** avoid RTTI (`dynamic_cast`, `typeid`) in production design, **MAY**
  use it in tests or a justified hierarchy, and **MUST NOT** replace it with a
  hand-rolled type tag.
- **SHOULD** use the standard library and project-approved dependencies; check
  ownership, license, security, and maintenance before adding another.
- **SHOULD** follow the repository's logging and formatting library, overload
  `<<` only for value-like types, and print the user-visible value.
- **MUST NOT** use a macro where a function, enum, `constexpr`, or `const`
  variable works; a local macro gets a project prefix and an immediate `#undef`
  after use.
