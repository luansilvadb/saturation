# JavaScript Code Style Guide

### Modules — `JS-MODULES`

- **MUST** write a new file as an ES module using `import` and `export`.
- **MUST** export named bindings; a module has no default export.

### Variable declarations — `JS-DECLARATIONS`

- **MUST** declare a binding with `const`, and use `let` only where the binding
  is reassigned.
- **MUST NOT** use `var`.

### Equality — `JS-EQUALITY`

- **MUST** compare with `===` and `!==`, converting a value explicitly first
  when the operands have different types.

### Iteration — `JS-ITERATION`

- **SHOULD** iterate an array with `for-of` and reserve `for-in` for
  enumerating an object's keys.

### Disallowed features — `JS-DISALLOWED`

- **MUST NOT** use `eval` or the `Function` constructor; parse the input with
  `JSON.parse` or dispatch through a table of functions.
- **MUST NOT** modify a built-in prototype (`Array.prototype.foo = ...`) or a
  host object's prototype; put the operation in a function or subclass the
  built-in.
