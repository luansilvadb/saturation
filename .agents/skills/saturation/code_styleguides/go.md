# Go Code Style Guide

### Formatting — `GO-FORMAT`

- **MUST** run `gofmt` (or `go fmt`) on every changed file; its output is the
  formatting rule of record.

### Naming — `GO-NAMING`

- **MUST** set visibility through capitalization: an exported identifier starts
  with an uppercase letter, an unexported one with a lowercase letter.
- **SHOULD** use `MixedCaps`/`mixedCaps` for a multi-word name and keep a
  package name short, lowercase, and free of underscores.
- **MUST NOT** prefix a getter with `Get`; the getter for field `owner` is
  `Owner()`.

### Interfaces — `GO-INTERFACES`

- **SHOULD** name a one-method interface after its method plus `-er`
  (`Reader`, `Writer`).
- **SHOULD** declare an interface where it is consumed and limit it to the
  methods that caller uses.

### Errors — `GO-ERRORS`

- **MUST NOT** discard an error with the blank identifier (`_`); handle it or
  return it to the caller.
- **MUST** return an error as the last result value instead of signalling a
  failure through a sentinel or a panic.
- **MUST NOT** call `panic` outside `init` or startup; reserve it for a state
  the program cannot continue from.
- **SHOULD** release an acquired resource with `defer` immediately after
  acquiring it.

### Concurrency — `GO-CONCURRENCY`

- **SHOULD** have the function that starts goroutines also own the mechanism
  that waits for them to finish.
