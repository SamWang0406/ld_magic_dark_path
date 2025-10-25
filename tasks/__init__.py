from __future__ import annotations

import os
from typing import List

from tasks.cow_level import CowLevelTask


REGISTRY = {
    "cow_level": CowLevelTask,
}


def build_tasks_from_env() -> List[object]:
    """Create task instances from env var TASKS (comma-separated).

    Default: cow_level
    """
    csv = os.getenv("TASKS", "cow_level").strip()
    names = [n.strip() for n in csv.split(",") if n.strip()]
    tasks = []
    for name in names:
        cls = REGISTRY.get(name)
        if not cls:
            # Unknown task names are ignored but can be logged by caller
            continue
        tasks.append(cls())
    return tasks

