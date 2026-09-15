# General Code Style — Structural Design Rules

This module defines cross-language structural rules for the codebase. It is
written for prompt composition as well as for human use: each rule should lead
to an observable decision, an appropriately scoped change, and evidence before
the actor reports completion.

Language-specific guides (for example, `java.md` or `typescript.md`) govern
formatting, naming, APIs, and language idioms. This module governs design
structure: size, coupling, cohesion, duplication, readability, and
encapsulation. Do not use it to override a language guide or a higher-priority
user, system, or compatibility constraint.

## Normative language

-   **MUST:** Required. Treat a violation as a defect unless a documented
    higher-priority constraint or accepted exception applies.
-   **SHOULD:** The default choice. Deviate only when the context provides a
    clear reason and the result remains readable and consistent.
-   **MAY:** Permitted choice. Prefer the option that is easiest to understand,
    test, and change.

Numeric limits in this module are diagnostic thresholds, not automatic
refactoring commands. A threshold identifies a design signal; cohesion,
coupling, behavior, and the cost of the proposed change determine the action.

---

## Agent application protocol

When this module is selected for an assignment, apply it with the following
bounded procedure:

1.   State the behavior, public contract, and compatibility constraints that
     must remain unchanged.
2.   Select only the rule IDs relevant to the assigned paths and objective.
     Do not paste or apply every rule when the task does not involve it.
3.   Inspect the existing design and identify observable signals before
     proposing a refactor. Do not infer a violation from a name or line count
     alone.
4.   Choose the smallest change that improves the identified structure without
     creating a less cohesive abstraction, unnecessary indirection, or an
     unrelated cleanup.
5.   Verify behavior and the structural property using the assignment's
     required checks. Record accepted deviations rather than silently ignoring
     them.

Translate every selected rule in the operational prompt as a compact
**signal → decision → action → evidence** instruction. Use the phase's existing
output contract for the result; do not invent a second response schema. Ask
for a concise rationale and evidence, never for hidden chain-of-thought or a
verbatim private reasoning trace.

### Role-specific use

-   **Implementer:** Apply relevant rules only when they serve the objective.
    Preserve externally visible behavior and list any accepted structural
    exception with its reason.
-   **Reviewer:** Report material findings with the rule ID, path and line (or
    equivalent precise location), impact, and a proportionate recommendation.
    Do not demand a refactor solely because an approximate threshold was
    exceeded.
-   **Verifier:** Recheck each named finding and acceptance criterion against
    the resulting code and recorded commands. Treat missing evidence as an
    unresolved gap, not as proof that the rule passed.

---

## 1. Size limits

### Class or module size — `GEN-SIZE-CLASS`

-   **SHOULD** keep a class or cohesive module under approximately 200 lines.
    If it exceeds the threshold, look for a cohesive responsibility that can
    be extracted without turning the original into a coordinator of trivial
    forwarding methods.
-   Size alone is not a defect. Treat a large unit as a stronger signal when it
    also has high coupling, multiple reasons to change, or weak cohesion.
-   Do not split a unit merely to satisfy a line count. The extracted unit must
    have a clear name, responsibility, boundary, and independent reason to
    change.

### Method or function size — `GEN-SIZE-METHOD`

-   **SHOULD** keep a method or function under approximately 30 lines. A
    longer unit is a signal to inspect for multiple responsibilities,
    deeply nested control flow, or an unnamed concept.
-   Prefer extracting a well-named operation over adding comments that explain
    what a block does. Keep a block inline when extraction would hide a simple
    sequence or make the control flow harder to follow.
-   A function may remain above the threshold when it is a cohesive, clear
    algorithm and extraction would make its invariants or error handling less
    visible. Record that decision when the threshold is relevant to the task.

---

## 2. Coupling

### Dependency count — `GEN-COUPLING`

-   **SHOULD** keep constructor or field dependencies under approximately 7
    distinct runtime collaborators per class or module. A significantly higher
    count is a signal that responsibilities or change reasons may be mixed.
-   Count collaborators required to construct or operate the unit: injected
    services, gateways, repositories, policies, clients, and similar domain
    dependencies. Do not count primitives, value types, collection types, or
    standard-library helpers used only locally.
-   When the signal is present, map each dependency to the responsibility that
    uses it. Extract a collaborator only when the cluster changes together and
    can be understood, tested, and modified independently.
-   Do not hide coupling behind a generic `Facade`, `Manager`, or pass-through
    wrapper that merely moves fields without creating a meaningful boundary.

### Example — before (12 collaborators)

```text
class OrderController {
  // orderRepo, customerRepo, paymentGateway, invoiceService,
  // taxCalculator, discountEngine, inventoryClient, shippingClient,
  // notificationService, auditLog, metricsCollector, featureFlags
}
```

### Example — after (cohesive clusters)

```text
class OrderController {
  // orderWorkflow, paymentWorkflow, fulfillmentWorkflow, auditLog
}

class OrderWorkflow {
  // orderRepo, customerRepo, featureFlags
}

class PaymentWorkflow {
  // paymentGateway, invoiceService, taxCalculator
}

class FulfillmentWorkflow {
  // inventoryClient, shippingClient, notificationService
}
```

The extraction is useful because each cluster represents a meaningful workflow,
not because the number 7 was reached mechanically.

---

## 3. Cohesion and encapsulation

### Behavior ownership — `GEN-ENCAPSULATION`

-   **SHOULD** keep behavior close to the data it operates on. If an operation
    primarily depends on another object's state, prefer an operation, value
    object, collection abstraction, or pure module owned by that concept.
-   **MUST NOT** make a domain decision by traversing another object's internals
    through multiple accessors when the data owner can express the decision.
    This is the *Feature Envy* signal.
-   Do not force an artificial class in a procedural or functional design. A
    cohesive pure function or module can own the decision when that is the
    established architecture.
-   Accessor use for DTO projection, serialization, persistence mapping,
    read-model queries, and adapter boundaries is not automatically Feature
    Envy. Evaluate whether the code is making a domain decision or merely
    translating data.

### Example — Feature Envy (wrong)

```text
// In OrderController — reading getters from `order` to decide
if (order.getStatus() == VALIDATED
    && order.getPayment().isConfirmed()
    && order.getItems().stream().allMatch(Item::isAvailable)) {
  ship(order);
}
```

### Example — encapsulated (correct)

```text
// In Order — the object that owns the data decides
public boolean isReadyToShip() {
  return status == VALIDATED
      && payment.isConfirmed()
      && items.allAvailable();
}

// In OrderController — delegates the decision
if (order.isReadyToShip()) {
  ship(order);
}
```

The caller asks the object; the object decides. This reduces knowledge of
internal structure and gives the decision one place to test and reuse.

---

## 4. First-Class Collections

### Named collection abstractions — `GEN-COLLECTION`

-   **SHOULD** introduce a named collection abstraction when a collection has
    domain invariants, semantic queries, or repeated filtering, mapping, and
    reducing logic across call sites.
-   **MAY** keep a raw collection for one simple local iteration when it has no
    domain behavior or invariant. Do not create a wrapper only to rename
    `map`, `filter`, or `length`.
-   The abstraction must encapsulate the iteration and expose semantic
    operations. Keep mutation and representation rules at the boundary instead
    of leaking the internal collection to every caller.

### Example — duplicated collection logic (wrong)

```text
// In ControllerA
boolean hasValidated = steps.stream()
    .anyMatch(s -> s.getValidationStatus() == VALIDATED);

// In ControllerB — same domain query duplicated
boolean hasValidated = steps.stream()
    .anyMatch(s -> s.getValidationStatus() == VALIDATED);
```

### Example — First-Class Collection (correct)

```text
class FunnelSteps {
  private final List<Step> steps;

  boolean hasAnyValidated() {
    return steps.stream()
        .anyMatch(s -> s.getValidationStatus() == VALIDATED);
  }

  boolean areAllValidated() {
    return steps.stream()
        .allMatch(s -> s.getValidationStatus() == VALIDATED);
  }
}

// In ControllerA and ControllerB
if (funnelSteps.hasAnyValidated()) { ... }
```

The wrapper is valuable because it is the single place that knows the query's
meaning. If the data model changes, callers do not need to repeat the change.

---

## 5. Duplication

### Semantic duplication — `GEN-DUPLICATION`

-   **MUST NOT** duplicate materially identical domain behavior across call
    sites. Two blocks are duplicates when they express the same intent, even
    when names or parameters differ slightly.
-   Before extracting, compare semantics, validation, error handling, side
    effects, and expected change reasons. Do not abstract code that merely
    looks similar but has different contracts or is likely to evolve
    independently.
-   Choose the extraction strategy based on the semantic relationship:
    -   **Shared method or function** in the same unit when duplication is
        local.
    -   **Domain class, value object, or service** when duplication spans
        units and represents a reusable concept.
    -   **First-Class Collection** (Section 4) when duplication is collection
        behavior.
-   Prefer a small, explicit duplication over a vague abstraction when the
    abstraction would require flags, conditionals, or a misleading name. If
    the duplication is intentional, record why it should remain separate.

---

## 6. Readability and simplicity

### Intent and consistency — `GEN-READABILITY`

-   **SHOULD** prefer the simplest solution that makes the behavior and
    invariants clear.
-   **SHOULD** use names that express domain intent and avoid clever, obscure,
    or compressed constructs that make the next change harder.
-   **SHOULD** follow established patterns in the codebase. Do not introduce a
    new abstraction or architectural pattern when an existing one handles the
    same concern.
-   **SHOULD** maintain consistent formatting, naming, and structure across
    files; defer syntax and idioms to the applicable language guide.
-   When simplifying, preserve evaluation order, failure behavior, observable
    side effects, and public contracts.

---

## 7. Documentation

### Intent and constraints — `GEN-DOCUMENTATION`

-   **SHOULD** document why a non-obvious decision is necessary, including
    constraints, trade-offs, invariants, or external behavior.
-   **SHOULD** keep documentation synchronized with code changes.
-   **MUST NOT** add documentation that merely restates what the code already
    says. Prefer a better name or smaller operation when the comment would only
    narrate implementation steps.

---

## Exception and trade-off policy

Accept a structural deviation only when all of the following are true:

-   the relevant rule is a heuristic or a genuine higher-priority constraint
    prevents the preferred design;
-   the current design remains understandable and the proposed refactor would
    create greater coupling, weaker cohesion, needless indirection, or
    behavior risk; and
-   the actor records the rule ID, precise location, reason, impact, and the
    verification that supports the decision.

“It works” or “the threshold is only approximate” is not sufficient evidence by
itself. Do not silently waive a relevant rule, and do not turn an accepted
exception into a precedent for unrelated code without checking its context.

---

## Verification checklist

Before reporting completion, use the checks relevant to the assignment:

-   The behavior, public contract, and compatibility assumptions to preserve
    are explicit.
-   Only relevant rule IDs were applied; unrelated cleanup was not introduced.
-   Each suspected issue has direct evidence at a precise path and location.
-   No class or cohesive module exceeds approximately 200 lines without a
    recorded design reason (`GEN-SIZE-CLASS`).
-   No method or function exceeds approximately 30 lines without a recorded
    design reason (`GEN-SIZE-METHOD`).
-   No unit has more than approximately 7 meaningful runtime collaborators
    without a recorded design reason (`GEN-COUPLING`).
-   No domain decision depends on another object's internal state through
    avoidable accessor traversal (`GEN-ENCAPSULATION`).
-   Repeated collection behavior has a named abstraction when its semantics or
    invariants justify one (`GEN-COLLECTION`).
-   Materially duplicated domain behavior is extracted or explicitly justified
    (`GEN-DUPLICATION`).
-   The result follows local patterns, preserves side effects and failure
    behavior, and remains easy to understand (`GEN-READABILITY`).
-   Documentation explains intent and constraints rather than narrating code
    (`GEN-DOCUMENTATION`).
-   Appropriate target and regression checks pass, or a documented, scoped
    reason explains why a check is not applicable.

Report every relevant threshold that was exceeded, the decision taken, and the
evidence or reason supporting it. Use the phase output contract and its
registered evidence fields for the final report.
