import logging
from concurrent.futures import Future
from dataclasses import dataclass, field, replace
from threading import Lock
from typing import Any, Callable, Literal
from uuid import uuid4

from app.services.download_runner import submit_download


logger = logging.getLogger(__name__)

DownloadStatus = Literal["queued", "running", "completed", "failed"]


@dataclass
class DownloadTask:
    id: str
    status: DownloadStatus = "queued"
    error: str | None = None
    future: Future[Any] | None = field(default=None, repr=False, compare=False)


class DownloadTaskManager:
    def __init__(self):
        self._tasks: dict[str, DownloadTask] = {}
        self._lock = Lock()

    def create_task(
        self,
        function: Callable[..., Any],
        /,
        *args: Any,
        **kwargs: Any,
    ) -> DownloadTask:
        task = DownloadTask(id=uuid4().hex)
        with self._lock:
            self._tasks[task.id] = task

        future = submit_download(
            self._run_task,
            task.id,
            function,
            args,
            kwargs,
        )
        with self._lock:
            task.future = future
            return replace(task)

    def get_task(self, task_id: str) -> DownloadTask | None:
        with self._lock:
            task = self._tasks.get(task_id)
            return replace(task) if task is not None else None

    def _run_task(
        self,
        task_id: str,
        function: Callable[..., Any],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> Any:
        self._update_task(task_id, status="running")
        try:
            result = function(*args, **kwargs)
        except Exception as exc:
            logger.exception("Download task %s failed", task_id)
            self._update_task(task_id, status="failed", error=str(exc))
            raise

        self._update_task(task_id, status="completed")
        return result

    def _update_task(
        self,
        task_id: str,
        *,
        status: DownloadStatus,
        error: str | None = None,
    ) -> None:
        with self._lock:
            task = self._tasks[task_id]
            task.status = status
            task.error = error
