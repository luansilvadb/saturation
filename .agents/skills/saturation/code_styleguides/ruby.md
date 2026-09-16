# Ruby Code Style Guide

### Frozen string literals — `RB-FROZEN-STRINGS`

- **MUST** start every Ruby source file with the `# frozen_string_literal:
  true` magic comment.

### Blocks over loops — `RB-BLOCKS`

- **MUST** process a collection with a block (`each`, `map`, `select`,
  `reduce`) or an `Enumerator` instead of an explicit `for` or `while` loop.

### Explicit returns — `RB-RETURNS`

- **SHOULD** rely on the implicit value of a method's last expression, and
  reserve an explicit `return` for an early guard clause.

### Exception handling — `RB-EXCEPTIONS`

- **MUST NOT** rescue bare `Exception`, and **MUST NOT** leave a `rescue` that
  swallows the error; name the specific error class the block handles.
- **SHOULD** include the observed context in the message of a raised error.

### Keyword arguments — `RB-KEYWORD-ARGS`

- **SHOULD** declare keyword arguments for a method that takes a boolean flag
  or more than two parameters.

### Nil handling — `RB-SAFE-NAVIGATION`

- **SHOULD** use safe navigation (`&.`) or conditional assignment (`||=`,
  `&&=`) where a value may legitimately be nil.
- **MUST NOT** use safe navigation to hide a value the code requires.

### Naming — `RB-NAMING`

- **MUST** end a predicate method's name with `?` and a method that mutates
  its receiver with `!`.
