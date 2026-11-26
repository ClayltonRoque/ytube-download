from threading import Event
from unittest.mock import ANY, patch
from uuid import UUID

import pytest

from app import create_app


VIDEO_URL = "https://www.youtube.com/watch?v=AbC123_456-"


def create_test_app(download_folder):
    app = create_app()
    app.testing = True
    app.config["DOWNLOAD_FOLDER"] = str(download_folder)
    return app


@patch("app.routes.downloads.download_audio", return_value={"id": "test-video"})
def test_download_endpoint_creates_audio_task(download_audio, tmp_path):
    app = create_test_app(tmp_path)

    response = app.test_client().post(
        "/api/download",
        json={
            "url": VIDEO_URL,
            "media_type": "audio",
            "format": "mp3",
            "quality": "192",
        },
    )

    assert response.status_code == 202
    payload = response.get_json()
    assert payload["success"] is True
    task_id = payload["task"]["id"]
    assert UUID(task_id).hex == task_id
    task = app.extensions["download_task_manager"].get_task(task_id)
    assert task is not None
    assert task.future is not None
    task.future.result(timeout=2)
    assert app.extensions["download_task_manager"].get_task(task_id).status == (
        "completed"
    )
    download_audio.assert_called_once_with(
        VIDEO_URL,
        str(tmp_path),
        audio_format="mp3",
        audio_quality=192,
        progress_hook=ANY,
    )


@patch("app.routes.downloads.download_video", return_value={"id": "test-video"})
def test_download_endpoint_creates_video_task(download_video, tmp_path):
    app = create_test_app(tmp_path)

    response = app.test_client().post(
        "/api/download",
        json={
            "url": VIDEO_URL,
            "media_type": "video",
            "quality": "720",
        },
    )

    assert response.status_code == 202
    payload = response.get_json()
    task_id = payload["task"]["id"]
    task = app.extensions["download_task_manager"].get_task(task_id)
    assert task is not None
    assert task.future is not None
    task.future.result(timeout=2)
    assert app.extensions["download_task_manager"].get_task(task_id).status == (
        "completed"
    )
    download_video.assert_called_once_with(
        VIDEO_URL,
        str(tmp_path),
        video_format="mp4",
        video_quality=720,
        progress_hook=ANY,
    )


@patch("app.routes.downloads.download_audio")
def test_download_endpoint_rejects_invalid_options_without_scheduling(
    download_audio, tmp_path
):
    app = create_test_app(tmp_path)

    response = app.test_client().post(
        "/api/download",
        json={
            "url": VIDEO_URL,
            "media_type": "audio",
            "format": "flac",
            "quality": 192,
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_options"
    download_audio.assert_not_called()


def test_progress_endpoint_returns_task_state_and_sanitized_progress(tmp_path):
    app = create_test_app(tmp_path)
    task_manager = app.extensions["download_task_manager"]
    started = Event()
    release = Event()
    progress_info = {
        "status": "downloading",
        "downloaded_bytes": 64,
        "total_bytes": 128,
        "filename": "/private/path/video.mp4",
    }

    def wait_for_release(progress_hook):
        progress_hook(progress_info)
        started.set()
        assert release.wait(timeout=5)

    task = task_manager.create_task(wait_for_release)
    assert task.future is not None
    try:
        assert started.wait(timeout=2)
        response = app.test_client().get(
            f"/api/download/progress/{task.id}"
        )
    finally:
        release.set()

    task.future.result(timeout=2)
    assert response.status_code == 200
    assert response.get_json() == {
        "success": True,
        "task": {
            "id": task.id,
            "status": "running",
            "progress": {
                "status": "downloading",
                "downloaded_bytes": 64,
                "total_bytes": 128,
                "percentage": 50.0,
                "speed": None,
                "eta": None,
            },
            "error": None,
        },
    }

    completed_response = app.test_client().get(
        f"/api/download/progress/{task.id}"
    )
    assert completed_response.get_json()["task"]["status"] == "completed"


def test_progress_endpoint_returns_not_found_for_unknown_task(tmp_path):
    response = create_test_app(tmp_path).test_client().get(
        "/api/download/progress/not-a-task"
    )

    assert response.status_code == 404
    assert response.get_json() == {
        "success": False,
        "error": {
            "code": "task_not_found",
            "message": "Tarefa de download não encontrada.",
        },
    }


def test_progress_endpoint_hides_unexpected_failure_details(tmp_path):
    app = create_test_app(tmp_path)
    task_manager = app.extensions["download_task_manager"]

    def fail_with_internal_path(progress_hook):
        raise OSError("permission denied: /private/downloads")

    task = task_manager.create_task(fail_with_internal_path)
    assert task.future is not None
    with pytest.raises(OSError):
        task.future.result(timeout=2)

    response = app.test_client().get(f"/api/download/progress/{task.id}")

    assert response.status_code == 200
    assert response.get_json()["task"]["error"] == (
        "Não foi possível concluir o download."
    )
    assert "/private/downloads" not in response.get_data(as_text=True)


def test_file_endpoint_serves_completed_task_as_attachment(tmp_path):
    app = create_test_app(tmp_path)
    output_file = tmp_path / "completed.mp3"
    output_file.write_bytes(b"audio data")
    task = app.extensions["download_task_manager"].create_task(
        lambda progress_hook: {"filepath": str(output_file)}
    )
    assert task.future is not None
    task.future.result(timeout=2)

    response = app.test_client().get(f"/api/download/file/{task.id}")

    assert response.status_code == 200
    assert response.data == b"audio data"
    assert response.headers["Content-Disposition"] == (
        'attachment; filename=completed.mp3'
    )


def test_file_endpoint_rejects_task_that_is_not_completed(tmp_path):
    app = create_test_app(tmp_path)
    started = Event()
    release = Event()

    def wait_for_release(progress_hook):
        started.set()
        assert release.wait(timeout=5)

    task = app.extensions["download_task_manager"].create_task(wait_for_release)
    assert task.future is not None
    try:
        assert started.wait(timeout=2)
        response = app.test_client().get(f"/api/download/file/{task.id}")
    finally:
        release.set()

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "file_not_ready"


def test_file_endpoint_does_not_serve_files_outside_download_folder(tmp_path):
    download_folder = tmp_path / "downloads"
    download_folder.mkdir()
    app = create_test_app(download_folder)
    outside_file = tmp_path / "outside.mp4"
    outside_file.write_bytes(b"secret")
    task = app.extensions["download_task_manager"].create_task(
        lambda progress_hook: {"filepath": str(outside_file)}
    )
    assert task.future is not None
    task.future.result(timeout=2)

    response = app.test_client().get(f"/api/download/file/{task.id}")

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "file_unavailable"
