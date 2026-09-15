"""Focused tests for the in-memory saturation evaluator."""

from __future__ import annotations

import copy
import unittest

import grader


def _events() -> list[dict[str, object]]:
    """Return a valid observation for two isolated assignments."""

    return [
        {
            "kind": "context_frozen",
            "path": ".saturation/context.md",
            "frozen": True,
        },
        {
            "kind": "assignment",
            "assignment_id": "core",
            "session_id": "S-core-1",
            "fresh_session": True,
            "read_scope": [
                ".saturation/context.md",
                "src/core",
                ".agents/skills/saturation/code_styleguides/typescript.md",
            ],
            "write_scope": ["src/core"],
            "style_guides": [
                ".agents/skills/saturation/code_styleguides/typescript.md"
            ],
        },
        {
            "kind": "assignment",
            "assignment_id": "docs",
            "session_id": "S-docs-1",
            "fresh_session": True,
            "read_scope": [
                ".saturation/context.md",
                "README.md",
                ".agents/skills/saturation/code_styleguides/general.md",
            ],
            "write_scope": ["README.md"],
            "style_guides": [
                ".agents/skills/saturation/code_styleguides/general.md"
            ],
        },
        {"kind": "check", "name": "tests", "status": "pass"},
        {"kind": "check", "name": "review", "status": "pass"},
        {
            "kind": "integrated",
            "status": "complete",
            "changed_paths": ["src/core/sim.ts", "README.md"],
        },
        {"kind": "durable_path", "path": ".saturation/context.md"},
        {"kind": "durable_path", "path": "src/core/sim.ts"},
        {"kind": "durable_path", "path": "README.md"},
    ]


class ObserverTests(unittest.TestCase):
    """Verify that runtime observations stay detached and in memory."""

    def test_observer_returns_a_detached_snapshot(self) -> None:
        observer = grader.RunObserver()
        observer.record("context_frozen", path=".saturation/context.md", frozen=True)

        snapshot = observer.snapshot()
        snapshot[0]["path"] = "changed"

        self.assertEqual(observer.snapshot()[0]["path"], ".saturation/context.md")

    def test_empty_event_kind_is_rejected(self) -> None:
        observer = grader.RunObserver()

        with self.assertRaises(ValueError):
            observer.record("", value=True)


class GraderTests(unittest.TestCase):
    """Verify useful runtime invariants without trace persistence."""

    def test_complete_observation_passes(self) -> None:
        result = grader.evaluate_events(_events())

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["metrics"]["assignments"], 2)
        self.assertEqual(result["metrics"]["forbidden_durable_paths"], 0)
        self.assertEqual(result["errors"], [])

    def test_mapping_snapshot_is_supported(self) -> None:
        result = grader.evaluate_observation({"events": _events()})

        self.assertEqual(result["status"], "pass")

    def test_additive_event_kinds_and_fields_are_ignored(self) -> None:
        events = _events()
        events[0]["future_field"] = "ignored"
        events.insert(1, {"kind": "future_metric", "value": 1})

        result = grader.evaluate_events(events)

        self.assertEqual(result["status"], "pass")

    def test_runtime_artifacts_are_rejected_when_persisted(self) -> None:
        events = _events()
        events.append(
            {"kind": "durable_path", "path": ".saturation/runs/trace.json"}
        )

        result = grader.evaluate_events(events)

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["checks"]["no_runtime_artifacts"]["status"], "fail")
        self.assertEqual(result["metrics"]["forbidden_durable_paths"], 1)

    def test_reused_session_is_rejected(self) -> None:
        events = _events()
        events[2]["session_id"] = events[1]["session_id"]

        result = grader.evaluate_events(events)

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["checks"]["fresh_sessions"]["status"], "fail")

    def test_overlapping_write_scopes_are_rejected(self) -> None:
        events = _events()
        events[2]["write_scope"] = ["src"]

        result = grader.evaluate_events(events)

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["checks"]["disjoint_scopes"]["status"], "fail")

    def test_missing_style_guide_is_rejected(self) -> None:
        events = _events()
        events[1]["style_guides"] = []

        result = grader.evaluate_events(events)

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["checks"]["style_guides"]["status"], "fail")

    def test_failed_check_is_rejected(self) -> None:
        events = _events()
        events[3]["status"] = "fail"

        result = grader.evaluate_events(events)

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["checks"]["verification"]["status"], "fail")

    def test_out_of_scope_integration_is_rejected(self) -> None:
        events = _events()
        events[5] = {
            "kind": "integrated",
            "status": "complete",
            "changed_paths": ["src/game/renderer.ts"],
        }

        result = grader.evaluate_events(events)

        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["checks"]["integration"]["status"], "fail")

    def test_invalid_event_input_is_rejected_without_writing(self) -> None:
        result = grader.evaluate_observation(None)

        self.assertEqual(result["status"], "fail")
        self.assertIn("events must be a sequence", result["errors"][0])

    def test_evaluation_does_not_mutate_input(self) -> None:
        events = _events()
        before = copy.deepcopy(events)

        grader.evaluate_events(events)

        self.assertEqual(events, before)


if __name__ == "__main__":
    unittest.main()
