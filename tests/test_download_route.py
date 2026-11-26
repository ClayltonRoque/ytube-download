from unittest.mock import ANY, patch
from uuid import UUID

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
