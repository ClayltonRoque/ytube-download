import pytest

from app.utils.validators import (
    is_spotify_url,
    is_youtube_playlist_url,
    validate_spotify_track_url,
    validate_youtube_url,
)


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=AbC123_456-",
        "http://m.youtube.com/watch?v=AbC123_456-",
        "https://music.youtube.com/watch?v=AbC123_456-",
        "https://youtu.be/AbC123_456-?si=share-token",
        "https://www.youtube.com/shorts/AbC123_456-",
        "https://www.youtube.com/live/AbC123_456-",
        "https://www.youtube.com/embed/AbC123_456-",
        "https://www.youtube-nocookie.com/embed/AbC123_456-",
    ],
)
def test_accepts_supported_video_urls(url):
    assert validate_youtube_url(url) == url


def test_strips_surrounding_whitespace():
    assert validate_youtube_url("  https://youtu.be/AbC123_456-  ") == (
        "https://youtu.be/AbC123_456-"
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/playlist?list=PLabc_123",
        "https://www.youtube.com/watch?v=AbC123_456-&list=PLabc_123",
        "https://youtu.be/AbC123_456-?list=PLabc_123",
    ],
)
def test_accepts_playlist_urls(url):
    assert validate_youtube_url(url) == url
    assert is_youtube_playlist_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "",
        None,
        "https://example.com/watch?v=AbC123_456-",
        "https://youtube.com.evil.example/watch?v=AbC123_456-",
        "ftp://youtube.com/watch?v=AbC123_456-",
        "https://user@youtube.com/watch?v=AbC123_456-",
        "https://youtube.com:8443/watch?v=AbC123_456-",
        "https://youtube.com/watch",
        "https://youtube.com/watch?v=short",
        "https://youtube.com/playlist",
        "https://youtube.com/playlist?list=",
        "https://youtube.com/playlist?list=abc&list=def",
        "https://youtube-nocookie.com/shorts/AbC123_456-",
    ],
)
def test_rejects_unsupported_or_malformed_urls(url):
    with pytest.raises(ValueError):
        validate_youtube_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://open.spotify.com/track/AbCdEfGhIjKlMnOpQrStUv",
        "https://open.spotify.com/intl-pt/track/AbCdEfGhIjKlMnOpQrStUv?si=share-token",
    ],
)
def test_accepts_spotify_track_urls_and_returns_track_id(url):
    assert is_spotify_url(url)
    assert validate_spotify_track_url(url) == "AbCdEfGhIjKlMnOpQrStUv"


@pytest.mark.parametrize(
    "url",
    [
        "http://open.spotify.com/track/AbCdEfGhIjKlMnOpQrStUv",
        "https://open.spotify.com/album/AbCdEfGhIjKlMnOpQrStUv",
        "https://open.spotify.com/playlist/AbCdEfGhIjKlMnOpQrStUv",
        "https://open.spotify.com/track/short",
        "https://open.spotify.com.evil.example/track/AbCdEfGhIjKlMnOpQrStUv",
        "https://user@open.spotify.com/track/AbCdEfGhIjKlMnOpQrStUv",
        "https://open.spotify.com:8443/track/AbCdEfGhIjKlMnOpQrStUv",
    ],
)
def test_rejects_unsupported_spotify_urls(url):
    with pytest.raises(ValueError):
        validate_spotify_track_url(url)


def test_is_spotify_url_rejects_non_spotify_values():
    assert not is_spotify_url("https://spotify.com/track/AbCdEfGhIjKlMnOpQrStUv")
    assert not is_spotify_url("not a URL")
