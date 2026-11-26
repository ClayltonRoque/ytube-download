from unittest.mock import patch

from app import create_app
from app.services.youtube import YouTubeQueryError


VIDEO_URL = "https://www.youtube.com/watch?v=AbC123_456-"


def create_client():
    app = create_app()
    app.testing = True
    return app.test_client()


@patch("app.routes.downloads.get_video_info")
def test_metadata_endpoint_returns_service_result(get_video_info):
    info = {
        "id": "AbC123_456-",
        "title": "Test video",
        "thumbnail": "https://i.ytimg.com/vi/AbC123_456-/hqdefault.jpg",
        "duration": 180,
        "description": "Internal yt-dlp data",
        "formats": [
            {
                "format_id": "18",
                "ext": "mp4",
                "format_note": "360p",
                "resolution": "640x360",
                "height": 360,
                "fps": 30,
                "filesize": 1024,
                "vcodec": "avc1",
                "acodec": "mp4a",
                "url": "https://media.example/temporary",
            }
        ],
    }
    get_video_info.return_value = info

    response = create_client().post("/api/metadata", json={"url": VIDEO_URL})

    assert response.status_code == 200
    assert response.get_json() == {
        "success": True,
        "metadata": {
            "title": "Test video",
            "thumbnail": "https://i.ytimg.com/vi/AbC123_456-/hqdefault.jpg",
            "duration": 180,
            "formats": [
                {
                    "format_id": "18",
                    "ext": "mp4",
                    "format_note": "360p",
                    "resolution": "640x360",
                    "height": 360,
                    "fps": 30,
                    "filesize": 1024,
                    "video_codec": "avc1",
                    "audio_codec": "mp4a",
                }
            ],
        },
    }
    get_video_info.assert_called_once_with(VIDEO_URL)


def test_metadata_endpoint_requires_json_object():
    response = create_client().post(
        "/api/metadata", data="not json", content_type="text/plain"
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "success": False,
        "error": {
            "code": "invalid_request",
            "message": "Envie um objeto JSON com o campo 'url'.",
        },
    }


@patch("app.routes.downloads.get_video_info")
def test_metadata_endpoint_rejects_invalid_url_without_querying(get_video_info):
    response = create_client().post(
        "/api/metadata", json={"url": "https://example.com/video"}
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "success": False,
        "error": {
            "code": "invalid_url",
            "message": "A URL deve pertencer ao YouTube.",
        },
    }
    get_video_info.assert_not_called()


@patch("app.routes.downloads.get_video_info")
def test_metadata_endpoint_returns_bad_gateway_for_provider_error(get_video_info):
    get_video_info.side_effect = YouTubeQueryError("Consulta indisponível.")

    response = create_client().post("/api/metadata", json={"url": VIDEO_URL})

    assert response.status_code == 502
    assert response.get_json() == {
        "success": False,
        "error": {
            "code": "provider_error",
            "message": "Consulta indisponível.",
        },
    }
