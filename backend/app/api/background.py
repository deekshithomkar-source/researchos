from fastapi import BackgroundTasks
from app.services.execution import execute_research


class FastAPIResearchExecutor:
    """Development adapter only. Replace this dependency to move to a durable queue."""
    def __init__(self, background_tasks: BackgroundTasks):
        self.background_tasks = background_tasks

    def enqueue(self, research_id: str) -> None:
        self.background_tasks.add_task(execute_research, research_id)


def get_executor(background_tasks: BackgroundTasks):
    return FastAPIResearchExecutor(background_tasks)
