import logging
from concurrent.futures import Future
from dataclasses import dataclass, field, replace
from math import isfinite
from threading import Lock
from typing import Any, Callable, Literal
from uuid import uuid4

from app.services.download_runner import submit_download
from app.services.downloader import MediaDownloadError


logger = logging.getLogger(__name__)

DownloadStatus = Literal["queued", "running", "completed", "failed"]
ProgressData = dict[str, str | int | float | None]


@dataclass
class DownloadTask:
    id: str
    status: DownloadStatus = "queued"
    error: str | None = None
    progress: ProgressData | None = None
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
            if task is None:
                return None
            progress = task.progress.copy() if task.progress is not None else None
            return replace(task, progress=progress)

    def _run_task(
        self,
        task_id: str,
        function: Callable[..., Any],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> Any:
        self._update_task(task_id, status="running")
        try:
            result = function(
                *args,
                progress_hook=lambda info: self._record_progress(task_id, info),
                **kwargs,
            )
        except Exception as exc:
            logger.exception("Download task %s failed", task_id)
            error = (
                str(exc)
                if isinstance(exc, (MediaDownloadError, ValueError))
                else "Não foi possível concluir o download."
            )
            self._update_task(task_id, status="failed", error=error)
            raise

        self._update_task(task_id, status="completed")
        return result

    def _record_progress(self, task_id: str, info: dict[str, Any]) -> None:
        status = info.get("status")
        if not isinstance(status, str):
            status = "unknown"

        downloaded_bytes = self._number(info.get("downloaded_bytes"))
        total_bytes = self._number(info.get("total_bytes")) or self._number(
            info.get("total_bytes_estimate")
        )
        percentage = None
        if total_bytes is not None and total_bytes > 0 and downloaded_bytes is not None:
            percentage = min(100.0, max(0.0, downloaded_bytes / total_bytes * 100))
        elif status == "finished":
            percentage = 100.0

        self._update_progress(
            task_id,
            {
                "status": status,
                "downloaded_bytes": downloaded_bytes,
                "total_bytes": total_bytes,
                "percentage": percentage,
                "speed": self._number(info.get("speed")),
                "eta": self._number(info.get("eta")),
            },
        )

    @staticmethod
    def _number(value: Any) -> int | float | None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        if isinstance(value, float) and not isfinite(value):
            return None
        return value

    def _update_progress(self, task_id: str, progress: ProgressData) -> None:
        with self._lock:
            self._tasks[task_id].progress = progress

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
