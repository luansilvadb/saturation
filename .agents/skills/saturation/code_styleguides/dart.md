# Dart Code Style Guide

### Imports — `DART-IMPORTS`

- **MUST** order import sections as `dart:`, then `package:`, then relative,
  and sort each section alphabetically.
- **MUST** place `export` directives in their own section after all imports.
- **MUST NOT** import another package's `src/` library or use an import path
  that reaches into or out of `lib`.
- **SHOULD** use a relative path for an import inside the `lib` boundary.

### Formatting — `DART-FORMAT`

- **MUST** run `dart format` on every changed file; its output is the
  formatting rule of record.

### Null safety — `DART-NULL-SAFETY`

- **MUST NOT** initialize a variable, field, or default value to `null`
  explicitly, nor compare a non-nullable boolean with `true` or `false`.
- **SHOULD** model an unset value as a nullable type with type promotion or a
  null-check pattern.
- **MUST NOT** use `late` for initialization order that a constructor
  initializer list or a nullable field can express.
- **MUST NOT** declare a public `late final` field without an initializer.

### Collection conversion — `DART-CAST`

- **SHOULD** convert a collection with `List<T>.from()`, `map<T>()`, or
  `whereType<T>()` instead of `cast<T>()`, which defers the failure to element
  access.

### Error handling — `DART-ERRORS`

- **MUST NOT** catch an error without acting on it: the `catch` clause either
  handles the failure or rethrows.
- **MUST** use `rethrow`, not `throw error`, to preserve the original stack
  trace.
- **SHOULD** catch with an `on` clause naming a typed exception declared for
  that failure mode.
- **MUST NOT** catch `Error` or its subtypes, and **SHOULD** throw an `Error`
  subtype only for a programming mistake.

### Equality — `DART-EQUALITY`

- **MUST** override `hashCode` whenever `==` is overridden.
- **MUST** take a non-nullable `Object` parameter in `==` and keep the relation
  reflexive, symmetric, transitive, and consistent.
- **SHOULD** keep custom equality on an immutable class and let a mutable class
  use identity.

### Constructors and parameters — `DART-CONSTRUCTORS`

- **MUST** use initializing formals (`this.field`) when a constructor only
  assigns fields.
- **SHOULD** make a constructor `const` when every field is `final` and
  initialized in the constructor.
- **SHOULD** accept a boolean flag and an omittable argument as a named
  parameter, and express a range as an inclusive start with an exclusive end.
