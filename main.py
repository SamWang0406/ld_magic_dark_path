from core.logger import get_logger
from core.runner import build_runner_from_env
from tasks import build_tasks_from_env


def main() -> None:
    logger = get_logger("main")
    tasks = build_tasks_from_env()

    missing = []
    if not tasks:
        missing.append("TASKS 環境變數未對應到任何任務，將不執行。預設為 'cow_level'")
    for msg in missing:
        logger.warning(msg)

    runner = build_runner_from_env(tasks)
    logger.info("啟動 ld_magic_dark_path 多任務常駐程序")
    runner.loop()


if __name__ == "__main__":
    main()
