# General Code Style — Structural Design Rules

This document defines cross-language structural design rules that apply to
every language and framework used in this project. It is an operational
instruction block: understand the rules, apply them while coding, and verify
the result before reporting completion.

Language-specific guides (e.g. `java.md`, `typescript.md`) handle formatting,
naming, and language-idiomatic constructs. This file handles **design
structure**: size, coupling, cohesion, duplication, and encapsulation.

## Normative language

-   **MUST:** Required. Treat a violation as a defect unless a documented
    higher-priority constraint applies.
-   **SHOULD:** The default choice. Deviate only when the context provides a
    clear reason and the choice remains readable and consistent.
-   **MAY:** Permitted choice. Prefer the option that keeps the code easiest
    to understand and change.

---

## 1. Size limits

### Class size

-   **SHOULD** keep classes under approximately 200 lines. When a class
    exceeds this threshold, look for a cohesive subset of its responsibilities
    that can be extracted into a new class.
-   A class that is large on its own is not necessarily a defect, but a class
    that is large *and* has high coupling or low cohesion almost always is.

### Method size

-   **SHOULD** keep methods under approximately 30 lines. A method longer
    than this typically does more than one thing and should be decomposed.
-   Prefer extracting a well-named method over adding inline comments that
    explain *what* a block does. If you need a comment to explain the next
    block, that block is probably a method.

---

## 2. Coupling

-   **SHOULD** keep constructor or field dependencies under approximately 7
    per class. A class with significantly more dependencies likely has too
    many responsibilities.
-   Count every type injected, imported for field/constructor use, or
    otherwise required to instantiate the class. Utility types from the
    standard library (e.g. `String`, `List`, `Map`, primitives) do not count.
-   When the limit is exceeded, identify clusters of dependencies that are
    used together and extract them into a collaborator class.

### Example — before (12 dependencies)

```text
class OrderController {
  // 12 fields: orderRepo, customerRepo, paymentGateway, invoiceService,
  //   taxCalculator, discountEngine, inventoryClient, shippingClient,
  //   notificationService, auditLog, metricsCollector, featureFlags
}
```

### Example — after (4 dependencies)

```text
class OrderController {
  // 4 fields: orderWorkflow, paymentWorkflow, fulfillmentWorkflow, auditLog
}

class OrderWorkflow {
  // 3 fields: orderRepo, customerRepo, featureFlags
}

class PaymentWorkflow {
  // 3 fields: paymentGateway, invoiceService, taxCalculator
}

class FulfillmentWorkflow {
  // 3 fields: inventoryClient, shippingClient, notificationService
}
```

Each new class groups dependencies that change together and can be understood,
tested, and modified independently.

---

## 3. Cohesion and encapsulation

-   **SHOULD** keep behavior close to the data it operates on. If a method
    operates primarily on another object's state, it belongs on that object.
-   **MUST NOT** write logic that reads multiple getters from another object
    to make a decision. Move the decision to the object that owns the data.
    This is the *Feature Envy* antipattern.

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

The caller asks the object; the object decides. This keeps the decision
testable in isolation, eliminates coupling to internal structure, and prevents
the same logic from being duplicated across callers.

---

## 4. First-Class Collections

-   **SHOULD** wrap a collection in a named class when the same filtering,
    mapping, or reducing logic appears in more than one call site.
-   The wrapper class encapsulates the iteration and gives semantic names to
    queries over the collection. This eliminates duplicated stream pipelines
    and makes the intent readable.

### Example — duplicated collection logic (wrong)

```text
// In ControllerA
boolean hasValidated = steps.stream()
    .anyMatch(s -> s.getValidationStatus() == VALIDATED);

// In ControllerB — same logic duplicated
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

The collection wrapper is the single place that knows how to query validation
status. If the data model changes, only the wrapper changes.

---

## 5. Duplication

-   **MUST** extract duplicated logic when the same pattern appears in more
    than one location.
-   Choose the extraction strategy based on the semantic relationship:
    -   **Shared method** in the same class, when the duplication is local.
    -   **Domain class or service**, when the duplication spans multiple
        classes and represents a reusable concept.
    -   **First-Class Collection** (Section 4), when the duplication is
        iteration over a collection.
-   Two blocks do not need to be character-identical to be duplicates. If they
    express the same intent with minor parameter differences, they are
    duplicates.

---

## 6. Readability and simplicity

-   **SHOULD** prefer simple solutions over complex ones.
-   **SHOULD** avoid overly clever or obscure constructs.
-   **SHOULD** follow existing patterns in the codebase. Do not introduce a
    new pattern when an established one handles the same concern.
-   **SHOULD** maintain consistent formatting, naming, and structure across
    files. Defer to the language-specific guide for details.

---

## 7. Documentation

-   **SHOULD** document *why* something is done, not just *what*.
-   **SHOULD** keep documentation up-to-date with code changes.
-   **MUST NOT** add documentation that merely restates what the code already
    says. Focus on intent, constraints, trade-offs, and non-obvious behavior.

---

## Verification checklist

Before reporting completion, verify the following structural properties:

-   No class exceeds approximately 200 lines without justification.
-   No method exceeds approximately 30 lines without justification.
-   No class has more than approximately 7 constructor/field dependencies.
-   No method reads multiple getters from another object to make a decision
    that the object itself should make (Feature Envy).
-   No collection iteration logic is duplicated across call sites without
    a First-Class Collection wrapper.
-   No logic block is duplicated across files without extraction.
-   Behavior lives close to the data it operates on.

Report any threshold exceeded and the reason it was accepted.
