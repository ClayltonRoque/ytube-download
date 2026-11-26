from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

import pytest
from spotipy.exceptions import SpotifyException

from app.services.spotify import (
    SpotifyConfigurationError,
    SpotifyQueryError,
    build_spotify_track_metadata,
    get_spotify_track_metadata,
)


TRACK_ID = "AbCdEfGhIjKlMnOpQrStUv"
TRACK = {
    "name": "Song & Dance",
    "artists": [{"name": "Example Artist"}, {"name": "Second Artist"}],
    "album": {
        "name": "Example Album",
        "images": [{"url": "https://i.scdn.co/image/example"}],
    },
    "duration_ms": 183_500,
}


@patch("app.services.spotify._spotify_client")
def test_get_spotify_track_metadata_queries_track_without_exposing_api_data(
    spotify_client,
):
    spotify_client.return_value.track.return_value = TRACK

    metadata = get_spotify_track_metadata(TRACK_ID, "client-id", "client-secret")

    spotify_client.assert_called_once_with("client-id", "client-secret")
    spotify_client.return_value.track.assert_called_once_with(TRACK_ID)
    assert metadata == {
        "title": "Song & Dance",
        "artists": ["Example Artist", "Second Artist"],
        "album": "Example Album",
        "thumbnail": "https://i.scdn.co/image/example",
        "duration": 183,
        "spotify_url": f"https://open.spotify.com/track/{TRACK_ID}",
        "youtube_search_url": (
            "https://www.youtube.com/results?"
            "search_query=Song+%26+Dance+Example+Artist+Second+Artist"
        ),
    }


def test_spotify_metadata_builder_requires_artist_and_title():
    with pytest.raises(SpotifyQueryError):
        build_spotify_track_metadata({"name": "Song", "artists": []}, TRACK_ID)


@patch("app.services.spotify._spotify_client")
def test_spotify_metadata_requires_client_credentials(spotify_client):
    with pytest.raises(SpotifyConfigurationError):
        get_spotify_track_metadata(TRACK_ID, None, None)

    spotify_client.assert_not_called()


@patch("app.services.spotify._spotify_client")
def test_spotify_service_reports_missing_track(spotify_client):
    spotify_client.return_value.track.side_effect = SpotifyException(
        404,
        -1,
        "Not found",
    )

    with pytest.raises(SpotifyQueryError, match="não foi encontrada"):
        get_spotify_track_metadata(TRACK_ID, "client-id", "client-secret")


def test_youtube_search_link_contains_track_and_artist_terms():
    metadata = build_spotify_track_metadata(TRACK, TRACK_ID)
    query = parse_qs(urlsplit(metadata["youtube_search_url"]).query)

    assert query == {
        "search_query": ["Song & Dance Example Artist Second Artist"]
    }
