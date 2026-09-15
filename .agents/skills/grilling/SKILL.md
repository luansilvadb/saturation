---
name: grilling
description: Run a structured, risk-aware design review by challenging a user's plan, architecture, proposal, or decision set one decision at a time. Use when the user asks to be grilled, challenged, interrogated, or wants to stress-test a plan before implementation; do not use for simple factual questions or ordinary execution.
---

# Grilling

Use this skill to turn an unvalidated plan into a shared, decision-complete understanding before execution.

## Guardrails

- Keep the user as the decision-maker. Separate verifiable facts from choices; state concise rationale and do not request or expose private chain-of-thought.
- Inspect the codebase, local files, and other available read-only sources for discoverable facts before asking. Ask only for missing, ambiguous, or preference-dependent decisions.
- Scale the depth to impact, irreversibility, cost, and blast radius. Do not invent branches or interrogate low-impact details that can safely use a default.
- Ask exactly one decision question per turn. Give a clearly labeled recommendation and its main trade-off before asking.
- Do not implement the plan, mutate files, send messages, or trigger external changes while grilling. Read-only investigation is allowed.
- Honor requests to skip, park, stop, or proceed. If the user delegates a decision, choose the recommended default, label it as an assumption, and keep it revisitable.

## Workflow

1. Frame the review.
   - Restate the desired outcome in one sentence.
   - Identify the scope, non-goals, stakeholders, constraints, success criteria, and risk level as they become relevant.
   - Build a compact decision map. Order decisions by dependency and impact, starting with root choices that constrain downstream branches.
   - Verify facts with available read-only tools before asking about them. If no concrete plan exists, ask for the desired outcome and current approach as the next single question.

2. Ask one question at a time. Use this shape:

   ```text
   Decision N — [decision to resolve]
   Known / verified: [relevant facts and constraints]
   Recommendation: [preferred answer]
   Trade-off / risk: [main reason and consequence]
   Question: [one answerable decision question]
   ```

3. Process each answer.
   - Confirm the decision in one sentence and record its downstream implications.
   - Remove resolved branches from the map and expose the next highest-impact dependency.
   - Surface contradictions with earlier answers instead of silently reconciling them.
   - Challenge important assumptions with a concrete counterexample, failure mode, or edge case, then ask the next decision question.
   - Label unknown facts as unknown and propose how to verify them; do not make the user guess a fact that can be checked.

4. Cover only relevant risk areas: objective and scope, users and workflow, alternatives and rationale, constraints and dependencies, data, security and privacy, performance and reliability, migration, rollout, observability, ownership, rollback, and acceptance criteria.

5. Close the review when all high-impact decisions have a chosen value, owner, or explicit default; success criteria and non-goals are clear; material dependencies and risk controls are addressed; and no important contradictions remain. Then present a concise shared-understanding summary containing:

   - objective, scope, and non-goals;
   - decisions and their key trade-offs;
   - assumptions and items to verify;
   - risks, mitigations, and rollback/ownership expectations;
   - acceptance criteria and the proposed next step.

   Ask one final confirmation: "Do you confirm this shared understanding and authorize execution?"

After explicit confirmation, hand off to the requested execution workflow without silently expanding scope. If the user ends the review early, summarize the unresolved decisions and do not execute the plan.
