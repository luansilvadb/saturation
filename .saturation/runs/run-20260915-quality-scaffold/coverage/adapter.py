"""Small stdlib line and branch coverage adapter for the quality run."""

from __future__ import annotations

import dis
import json
import runpy
import sys
import threading
from pathlib import Path
from types import CodeType
from typing import Any, Dict, Iterable, List, Set, Tuple


ADAPTER_VERSION = "stdlib-trace-branch-v1"
COVERAGE_THRESHOLD = 80.0
ROOT = Path(__file__).resolve().parents[4]
EVALS = ROOT / ".agents" / "skills" / "saturation" / "evals"
TARGETS = (
    EVALS / "reasoning_scaffold.py",
    EVALS / "quality_comparison.py",
)
TESTS = (
    EVALS / "test_quality_comparison.py",
    EVALS / "test_quality_comparison_edges.py",
    EVALS / "test_quality_comparison_missing_branches.py",
    EVALS / "test_quality_comparison_numeric_edges.py",
)
REPORT_PATH = Path(__file__).with_name("coverage-report.json")


def _code_objects(code: CodeType) -> Iterable[CodeType]:
    """Yield a code object and all nested function/comprehension objects."""

    yield code
    for constant in code.co_consts:
        if isinstance(constant, CodeType):
            yield from _code_objects(constant)


def _canonical(path: str) -> str:
    """Normalize a trace filename for stable Windows comparisons."""

    return str(Path(path).resolve())


def _relative(path: Path) -> str:
    """Return a repository-relative POSIX path for evidence records."""

    return path.relative_to(ROOT).as_posix()


def _branch_opcode(instruction: dis.Instruction) -> bool:
    """Return whether an instruction has two control-flow outcomes."""

    name = instruction.opname
    return name == "FOR_ITER" or name.startswith("JUMP_IF_") or name.startswith(
        "POP_JUMP_"
    )


def _authored_code(code: CodeType) -> bool:
    """Keep branch sites in authored functions, not compiler helpers."""

    return (
        "__annotate__" not in code.co_qualname
        and "<" not in code.co_qualname
    )


def _static_sites() -> Tuple[
    Dict[str, Set[int]], Dict[str, Dict[Tuple[str, int, int], Any]]
]:
    """Collect executable lines and conditional jump sites from source."""

    line_sites: Dict[str, Set[int]] = {}
    branch_sites: Dict[str, Dict[Tuple[str, int, int], Any]] = {}
    for source_path in TARGETS:
        path = _canonical(str(source_path))
        source = source_path.read_text(encoding="utf-8")
        source_lines = len(source.splitlines())
        compiled = compile(source, path, "exec")
        lines: Set[int] = set()
        branches: Dict[Tuple[str, int, int], Any] = {}
        for code in _code_objects(compiled):
            if not _authored_code(code):
                continue
            line_ranges = list(code.co_lines())
            instructions = list(dis.get_instructions(code))
            for index, instruction in enumerate(instructions):
                line = next(
                    (
                        line
                        for start, end, line in line_ranges
                        if start <= instruction.offset < end
                    ),
                    None,
                )
                if (
                    isinstance(line, int)
                    and not isinstance(line, bool)
                    and 1 <= line <= source_lines
                ):
                    lines.add(line)
                if not _branch_opcode(instruction):
                    continue
                next_offset = None
                if index + 1 < len(instructions):
                    next_offset = instructions[index + 1].offset
                target = instruction.argval
                if (
                    isinstance(line, int)
                    and not isinstance(line, bool)
                    and isinstance(target, int)
                    and next_offset is not None
                ):
                    key = (
                        code.co_qualname,
                        code.co_firstlineno,
                        instruction.offset,
                    )
                    branches[key] = {
                        "line": line,
                        "target": target,
                        "fallthrough": next_offset,
                    }
        line_sites[path] = lines
        branch_sites[path] = branches
    return line_sites, branch_sites


def _run() -> Dict[str, Any]:
    """Run the target tests and return the raw coverage observation."""

    line_sites, branch_sites = _static_sites()
    target_paths = set(line_sites)
    line_hits: Set[Tuple[str, int]] = set()
    branch_hits: Set[Tuple[str, int, int, str]] = set()
    pending: Dict[int, List[Tuple[str, int, int, int, int]]] = {}

    def resolve_pending(frame_id: int, offset: int) -> None:
        """Record a branch when a line or opcode event reaches its edge."""

        candidates = pending.get(frame_id, [])
        remaining: List[Tuple[str, int, int, int, int]] = []
        for prior in candidates:
            if offset == prior[3]:
                branch_hits.add(
                    (prior[0], prior[1], prior[2], "taken")
                )
            elif offset == prior[4]:
                branch_hits.add(
                    (prior[0], prior[1], prior[2], "fallthrough")
                )
            else:
                remaining.append(prior)
        if remaining:
            pending[frame_id] = remaining
        else:
            pending.pop(frame_id, None)

    def tracer(frame: Any, event: str, argument: Any) -> Any:
        path = _canonical(frame.f_code.co_filename)
        if event == "call":
            if path not in target_paths or not _authored_code(frame.f_code):
                return None
            frame.f_trace_opcodes = True
            return tracer
        if path not in target_paths:
            return tracer
        frame_id = id(frame)
        if not _authored_code(frame.f_code):
            return tracer
        if event == "line":
            resolve_pending(frame_id, frame.f_lasti)
            frame_key = (
                frame.f_code.co_qualname,
                frame.f_code.co_firstlineno,
            )
            for key, branch in branch_sites[path].items():
                if key[:2] != frame_key or branch["line"] != frame.f_lineno:
                    continue
                candidate = (
                    path,
                    branch["line"],
                    key[2],
                    branch["target"],
                    branch["fallthrough"],
                )
                if candidate not in pending.setdefault(frame_id, []):
                    pending[frame_id].append(candidate)
            line_hits.add((path, frame.f_lineno))
        elif event == "opcode":
            offset = frame.f_lasti
            resolve_pending(frame_id, offset)
            key = (
                frame.f_code.co_qualname,
                frame.f_code.co_firstlineno,
                offset,
            )
            branch = branch_sites[path].get(key)
            if branch is not None:
                candidate = (
                    path,
                    branch["line"],
                    offset,
                    branch["target"],
                    branch["fallthrough"],
                )
                if candidate not in pending.setdefault(frame_id, []):
                    pending[frame_id].append(candidate)
        elif event in ("return", "exception"):
            pending.pop(frame_id, None)
        return tracer

    sys.settrace(tracer)
    threading.settrace(tracer)
    try:
        sys.path.insert(0, str(EVALS))
        for test_path in TESTS:
            try:
                runpy.run_path(str(test_path), run_name="__main__")
            except SystemExit as exit_signal:
                if exit_signal.code not in (None, 0):
                    raise
    finally:
        sys.settrace(None)
        threading.settrace(None)

    line_total = sum(len(lines) for lines in line_sites.values())
    line_covered = sum(
        (path, line) in line_hits
        for path, lines in line_sites.items()
        for line in lines
    )
    branch_total = sum(len(branches) * 2 for branches in branch_sites.values())
    branch_covered = len(branch_hits)
    line_percent = 100.0 * line_covered / line_total if line_total else 100.0
    branch_percent = (
        100.0 * branch_covered / branch_total if branch_total else 100.0
    )
    return {
        "adapter_version": ADAPTER_VERSION,
        "python": sys.version.split()[0],
        "sources": [_relative(path) for path in TARGETS],
        "commands": [_relative(path) for path in TESTS],
        "line": {
            "covered": line_covered,
            "total": line_total,
            "percent": round(line_percent, 2),
        },
        "branch": {
            "covered": branch_covered,
            "total": branch_total,
            "percent": round(branch_percent, 2),
        },
        "gate": {
            "threshold_percent": COVERAGE_THRESHOLD,
            "status": (
                "pass"
                if line_percent >= COVERAGE_THRESHOLD
                and branch_percent >= COVERAGE_THRESHOLD
                else "fail"
            ),
        },
        "branch_sites": [
            {
                "source": _relative(Path(site[0])),
                "line": site[1],
                "offset": site[2],
                "outcome": site[3],
            }
            for site in sorted(branch_hits)
        ],
    }


if __name__ == "__main__":
    result = _run()
    REPORT_PATH.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result["line"], sort_keys=True))
    print(json.dumps(result["branch"], sort_keys=True))
    if result["gate"]["status"] != "pass":
        raise SystemExit("coverage threshold was not met")
