from threading import Event

import pytest

from app.services.download_tasks import DownloadTaskManager


def test_download_task_tracks_running_and_completed_states():
    task_manager = DownloadTaskManager()
    started = Event()
    release = Event()

    def wait_for_release():
        started.set()
        assert release.wait(timeout=5)
        return "finished"

    task = task_manager.create_task(wait_for_release)
    try:
        assert started.wait(timeout=2)
        assert task_manager.get_task(task.id).status == "running"
    finally:
        release.set()

    assert task.future is not None
    assert task.future.result(timeout=2) == "finished"
    assert task_manager.get_task(task.id).status == "completed"


def test_download_task_tracks_failures_and_preserves_future_exception():
    task_manager = DownloadTaskManager()

    def fail():
        raise RuntimeError("download failed")

    task = task_manager.create_task(fail)

    assert task.future is not None
    with pytest.raises(RuntimeError, match="download failed"):
        task.future.result(timeout=2)

    failed_task = task_manager.get_task(task.id)
    assert failed_task.status == "failed"
    assert failed_task.error == "download failed"


def test_download_task_ids_are_unique():
    task_manager = DownloadTaskManager()

    first_task = task_manager.create_task(lambda: None)
    second_task = task_manager.create_task(lambda: None)

    assert first_task.id != second_task.id
