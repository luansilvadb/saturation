"""Portable command-line wrapper for the local saturation trace grader."""

from __future__ import annotations

import sys
from pathlib import Path


EVALS_DIR = Path(__file__).resolve().parent
if str(EVALS_DIR) not in sys.path:
    sys.path.insert(0, str(EVALS_DIR))

from grader import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
