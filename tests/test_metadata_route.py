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
    info = {"id": "AbC123_456-", "title": "Test video"}
    get_video_info.return_value = info

    response = create_client().post("/api/metadata", json={"url": VIDEO_URL})

    assert response.status_code == 200
    assert response.get_json() == {"success": True, "metadata": info}
    get_video_info.assert_called_once_with(VIDEO_URL)


def test_metadata_endpoint_requires_json_object():
    response = create_client().post(
        "/api/metadata", data="not json", content_type="text/plain"
    )

    assert response.status_code == 400
    assert "error" in response.get_json()


@patch("app.routes.downloads.get_video_info")
def test_metadata_endpoint_rejects_invalid_url_without_querying(get_video_info):
    response = create_client().post(
        "/api/metadata", json={"url": "https://example.com/video"}
    )

    assert response.status_code == 400
    get_video_info.assert_not_called()


@patch("app.routes.downloads.get_video_info")
def test_metadata_endpoint_returns_bad_gateway_for_provider_error(get_video_info):
    get_video_info.side_effect = YouTubeQueryError("Consulta indisponível.")

    response = create_client().post("/api/metadata", json={"url": VIDEO_URL})

    assert response.status_code == 502
    assert response.get_json() == {"error": "Consulta indisponível."}
