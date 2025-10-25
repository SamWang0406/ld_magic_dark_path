from __future__ import annotations

import os
import time
from typing import Iterable, Optional, List

from core.adb_controller import capture_screen
from core.logger import get_logger
from core.task import Task, TaskContext, TaskResult


class TaskRunner:
    def __init__(
        self,
        tasks: Iterable[Task],
        *,
        screenshot_path: str = "screen.png",
        match_threshold: float = 0.8,
        check_interval: float = 1.0,
        click_cooldown: float = 2.0,
        device_id: Optional[str] = None,
    ) -> None:
        self.tasks: List[Task] = list(tasks)
        self.screenshot_path = screenshot_path
        self.match_threshold = float(match_threshold)
        self.check_interval = float(check_interval)
        self.click_cooldown = float(click_cooldown)
        self.device_id = device_id
        self.logger = get_logger("runner")

    def loop(self) -> None:
        self.logger.info(
            f"Runner start: tasks={[t.name for t in self.tasks]}, interval={self.check_interval}, "
            f"cooldown={self.click_cooldown}, threshold={self.match_threshold}"
        )

        while True:
            try:
                # 1) Capture once for all tasks
                capture_screen(self.screenshot_path, device_id=self.device_id)

                # 2) Build context and execute tasks in order
                ctx = TaskContext(
                    screenshot_path=self.screenshot_path,
                    match_threshold=self.match_threshold,
                    device_id=self.device_id,
                )

                acted_any = False
                for task in self.tasks:
                    result: TaskResult = task.tick(ctx)
                    if result.message:
                        # 將多行訊息逐行輸出，讓每一步都有獨立時間戳
                        for line in str(result.message).splitlines():
                            line = line.strip()
                            if line:
                                self.logger.info(f"[{task.name}] {line}")
                    acted_any = acted_any or result.acted

                # 3) Sleep policy
                time.sleep(self.click_cooldown if acted_any else self.check_interval)

            except Exception as e:
                self.logger.error(f"Runner error: {e}")
                time.sleep(self.check_interval)


def build_runner_from_env(tasks: Iterable[Task]) -> TaskRunner:
    screenshot_path = os.getenv("SCREENSHOT_PATH", "screen.png")
    match_threshold = float(os.getenv("MATCH_THRESHOLD", "0.8"))
    check_interval = float(os.getenv("CHECK_INTERVAL", "1.0"))
    click_cooldown = float(os.getenv("CLICK_COOLDOWN", "2.0"))
    device_id = os.getenv("ADB_DEVICE")
    return TaskRunner(
        tasks,
        screenshot_path=screenshot_path,
        match_threshold=match_threshold,
        check_interval=check_interval,
        click_cooldown=click_cooldown,
        device_id=device_id,
    )
