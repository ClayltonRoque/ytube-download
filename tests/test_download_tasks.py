from threading import Event

import pytest

from app.services.download_tasks import DownloadTaskManager


def test_download_task_tracks_running_and_completed_states():
    task_manager = DownloadTaskManager()
    started = Event()
    release = Event()

    def wait_for_release(progress_hook):
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

    def fail(progress_hook):
        raise RuntimeError("download failed")

    task = task_manager.create_task(fail)

    assert task.future is not None
    with pytest.raises(RuntimeError, match="download failed"):
        task.future.result(timeout=2)

    failed_task = task_manager.get_task(task.id)
    assert failed_task.status == "failed"
    assert failed_task.error == "Não foi possível concluir o download."


def test_download_task_stores_sanitized_progress():
    task_manager = DownloadTaskManager()
    progress_info = {
        "status": "downloading",
        "downloaded_bytes": 64,
        "total_bytes_estimate": 128,
        "speed": 32.5,
        "eta": 2,
        "filename": "/private/path/video.mp4",
    }

    def report_progress(progress_hook):
        progress_hook(progress_info)

    task = task_manager.create_task(report_progress)
    assert task.future is not None
    task.future.result(timeout=2)

    stored_progress = task_manager.get_task(task.id).progress
    assert stored_progress == {
        "status": "downloading",
        "downloaded_bytes": 64,
        "total_bytes": 128,
        "percentage": 50.0,
        "speed": 32.5,
        "eta": 2,
    }
    assert "filename" not in stored_progress


def test_download_task_marks_finished_progress_as_complete():
    task_manager = DownloadTaskManager()

    def report_finished(progress_hook):
        progress_hook({"status": "finished"})

    task = task_manager.create_task(report_finished)
    assert task.future is not None
    task.future.result(timeout=2)

    assert task_manager.get_task(task.id).progress["percentage"] == 100.0


def test_download_task_ids_are_unique():
    task_manager = DownloadTaskManager()

    first_task = task_manager.create_task(lambda progress_hook: None)
    second_task = task_manager.create_task(lambda progress_hook: None)

    assert first_task.id != second_task.id
