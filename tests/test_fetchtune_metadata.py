from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

import pytest
from fetchtune import ResolverError
from fetchtune.providers.spotify import SpotifyProvider

from app.services.fetchtune_metadata import (
    FetchTuneMetadataError,
    get_spotify_track_metadata,
)


TRACK_ID = "AbCdEfGhIjKlMnOpQrStUv"


def create_track():
    return SimpleNamespace(
        title="Song Title",
        artist_names=["Artist One", "Artist Two"],
        album=SimpleNamespace(name="Album Name"),
        cover_url="https://i.scdn.co/image/cover",
        duration_ms=183_500,
    )


@patch("app.services.fetchtune_metadata.Resolver")
def test_resolves_metadata_with_only_spotify_provider_and_no_enrichment(
    resolver_class,
):
    resolver_class.return_value.resolve.return_value = create_track()

    metadata = get_spotify_track_metadata(TRACK_ID)

    resolver_args = resolver_class.call_args.kwargs
    assert len(resolver_args["providers"]) == 1
    assert isinstance(resolver_args["providers"][0], SpotifyProvider)
    assert resolver_args["enrichment"] is False
    resolver_class.return_value.resolve.assert_called_once_with(
        f"https://open.spotify.com/track/{TRACK_ID}"
    )
    assert metadata == {
        "title": "Song Title",
        "artists": ["Artist One", "Artist Two"],
        "album": "Album Name",
        "thumbnail": "https://i.scdn.co/image/cover",
        "duration": 183,
        "spotify_url": f"https://open.spotify.com/track/{TRACK_ID}",
        "youtube_search_url": (
            "https://www.youtube.com/results?"
            "search_query=Song+Title+Artist+One+Artist+Two"
        ),
    }
    query = parse_qs(urlsplit(metadata["youtube_search_url"]).query)
    assert query == {"search_query": ["Song Title Artist One Artist Two"]}


@patch("app.services.fetchtune_metadata.Resolver")
def test_wraps_fetch_tune_resolution_errors_without_leaking_details(resolver_class):
    resolver_class.return_value.resolve.side_effect = ResolverError(
        "private upstream response"
    )

    with pytest.raises(FetchTuneMetadataError) as error:
        get_spotify_track_metadata(TRACK_ID)

    assert "private upstream response" not in str(error.value)


@patch("app.services.fetchtune_metadata.Resolver")
def test_rejects_incomplete_fetch_tune_metadata(resolver_class):
    resolver_class.return_value.resolve.return_value = SimpleNamespace(
        title="Song Title",
        artist_names=[],
    )

    with pytest.raises(FetchTuneMetadataError, match="artista"):
        get_spotify_track_metadata(TRACK_ID)
