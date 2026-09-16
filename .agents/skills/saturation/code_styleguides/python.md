# Python Code Style Guide

### Linting — `PY-LINT`

- **MUST** run `pylint` with the repository configuration on every changed
  module.

### Imports — `PY-IMPORTS`

- **SHOULD** import a module with `import x`, and use `from x import y` only
  when `y` is a submodule.

### Exceptions — `PY-EXCEPTIONS`

- **MUST NOT** write a bare `except:` clause; catch the specific exception the
  block handles.
- **SHOULD** raise a built-in exception class, or a project subclass of one,
  with a message naming the violated condition.

### Docstrings — `PY-DOCSTRINGS`

- **SHOULD** give a public function a one-line summary followed by `Args:`,
  `Returns:`, and `Raises:` sections for the parts that apply.

### Truthiness — `PY-TRUTHINESS`

- **SHOULD** test for `None` with `is None` / `is not None`, and reserve a
  truthiness test for an empty collection or string.

### Types — `PY-TYPES`

- **SHOULD** annotate the parameters and the return type of every public
  function.

### Public surface — `PY-INTERNAL`

- **MUST** prefix a module-level or class member that is not part of the public
  API with a single leading underscore.

### Markers — `PY-TODO`

- **MUST** format an outstanding work item as `TODO(username): description`,
  naming the owner.
