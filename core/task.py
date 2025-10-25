from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Optional


@dataclass
class TaskContext:
    """Shared runtime context passed to tasks each tick."""

    screenshot_path: str
    match_threshold: float
    device_id: Optional[str]


@dataclass
class TaskResult:
    """Outcome of a single task tick."""

    acted: bool = False  # e.g., performed a tap/click
    message: str = ""


class Task(Protocol):
    name: str

    def tick(self, ctx: TaskContext) -> TaskResult:
        """Run one iteration of the task with current screenshot available.

        Implementations should be resilient to errors and return TaskResult,
        raising only on unrecoverable issues.
        """
        ...

