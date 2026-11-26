from unittest.mock import patch

from app import create_app
from app.services.youtube import YouTubeQueryError


VIDEO_URL = "https://www.youtube.com/watch?v=AbC123_456-"
SPOTIFY_URL = "https://open.spotify.com/track/AbCdEfGhIjKlMnOpQrStUv"


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


@patch("app.routes.downloads.get_spotify_track_metadata")
def test_metadata_endpoint_returns_spotify_track_metadata(get_track_metadata):
    metadata = {
        "title": "Song",
        "artists": ["Artist"],
        "album": "Album",
        "thumbnail": None,
        "duration": 120,
        "spotify_url": SPOTIFY_URL,
        "youtube_search_url": (
            "https://www.youtube.com/results?search_query=Song+Artist"
        ),
    }
    get_track_metadata.return_value = metadata

    response = create_client().post("/api/metadata", json={"url": SPOTIFY_URL})

    assert response.status_code == 200
    assert response.get_json() == {
        "success": True,
        "provider": "spotify",
        "metadata": metadata,
    }
    get_track_metadata.assert_called_once_with("AbCdEfGhIjKlMnOpQrStUv")


@patch("app.routes.downloads.get_spotify_track_metadata")
def test_metadata_endpoint_rejects_spotify_playlists_without_querying(
    get_track_metadata,
):
    response = create_client().post(
        "/api/metadata",
        json={"url": "https://open.spotify.com/playlist/AbCdEfGhIjKlMnOpQrStUv"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_url"
    get_track_metadata.assert_not_called()


@patch("app.routes.downloads.get_spotify_track_metadata")
def test_metadata_endpoint_returns_bad_gateway_for_fetchtune_error(
    get_track_metadata,
):
    from app.services.fetchtune_metadata import FetchTuneMetadataError

    get_track_metadata.side_effect = FetchTuneMetadataError("Consulta indisponível.")

    response = create_client().post("/api/metadata", json={"url": SPOTIFY_URL})

    assert response.status_code == 502
    assert response.get_json()["error"] == {
        "code": "provider_error",
        "message": "Consulta indisponível.",
    }
