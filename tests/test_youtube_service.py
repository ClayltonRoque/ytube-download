from unittest.mock import patch

import pytest
from yt_dlp.utils import DownloadError

from app.services.youtube import (
    YouTubeQueryError,
    build_video_metadata,
    get_video_info,
)


VIDEO_URL = "https://www.youtube.com/watch?v=AbC123_456-"


@patch("app.services.youtube.YoutubeDL")
def test_get_video_info_extracts_metadata_without_downloading(youtube_dl_class):
    expected_info = {"id": "AbC123_456-", "title": "Test video"}
    youtube_dl = youtube_dl_class.return_value.__enter__.return_value
    youtube_dl.extract_info.return_value = expected_info

    result = get_video_info(VIDEO_URL)

    assert result is expected_info
    youtube_dl_class.assert_called_once_with(
        {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "skip_download": True,
        }
    )
    youtube_dl.extract_info.assert_called_once_with(VIDEO_URL, download=False)


@patch("app.services.youtube.YoutubeDL")
def test_get_video_info_validates_url_before_calling_ytdlp(youtube_dl_class):
    with pytest.raises(ValueError):
        get_video_info("https://example.com/watch?v=AbC123_456-")

    youtube_dl_class.assert_not_called()


@patch("app.services.youtube.YoutubeDL")
def test_get_video_info_wraps_ytdlp_download_errors(youtube_dl_class):
    youtube_dl = youtube_dl_class.return_value.__enter__.return_value
    youtube_dl.extract_info.side_effect = DownloadError("provider error")

    with pytest.raises(YouTubeQueryError) as error:
        get_video_info(VIDEO_URL)

    assert isinstance(error.value.__cause__, DownloadError)


@patch("app.services.youtube.YoutubeDL")
def test_get_video_info_rejects_playlist_results(youtube_dl_class):
    youtube_dl = youtube_dl_class.return_value.__enter__.return_value
    youtube_dl.extract_info.return_value = {"_type": "playlist", "entries": []}

    with pytest.raises(YouTubeQueryError):
        get_video_info(VIDEO_URL)


@patch("app.services.youtube.YoutubeDL")
def test_get_video_info_rejects_missing_results(youtube_dl_class):
    youtube_dl = youtube_dl_class.return_value.__enter__.return_value
    youtube_dl.extract_info.return_value = None

    with pytest.raises(YouTubeQueryError):
        get_video_info(VIDEO_URL)


@patch("app.services.youtube.YoutubeDL")
def test_get_video_info_extracts_playlist_entries(youtube_dl_class):
    playlist_url = "https://www.youtube.com/playlist?list=PLabc_123"
    expected_info = {"_type": "playlist", "title": "Playlist", "entries": []}
    youtube_dl = youtube_dl_class.return_value.__enter__.return_value
    youtube_dl.extract_info.return_value = expected_info

    assert get_video_info(playlist_url) is expected_info
    assert youtube_dl_class.call_args.args[0]["noplaylist"] is False
    assert youtube_dl_class.call_args.args[0]["extract_flat"] is True
    youtube_dl.extract_info.assert_called_once_with(playlist_url, download=False)


def test_build_video_metadata_uses_approximate_filesize_and_skips_invalid_formats():
    metadata = build_video_metadata(
        {
            "title": "Test video",
            "formats": [
                {"format_id": "audio", "filesize_approx": 512},
                {"ext": "mp4"},
                "invalid format",
            ],
        }
    )

    assert metadata == {
        "title": "Test video",
        "thumbnail": None,
        "duration": None,
        "formats": [
            {
                "format_id": "audio",
                "ext": None,
                "format_note": None,
                "resolution": None,
                "height": None,
                "fps": None,
                "filesize": 512,
                "video_codec": None,
                "audio_codec": None,
            }
        ],
    }


def test_build_video_metadata_returns_empty_formats_when_unavailable():
    assert build_video_metadata({"title": "Test video"}) == {
        "title": "Test video",
        "thumbnail": None,
        "duration": None,
        "formats": [],
    }


def test_build_video_metadata_returns_playlist_title_and_item_count():
    assert build_video_metadata(
        {
            "_type": "playlist",
            "title": "Favorites",
            "entries": [{"id": "one"}, None, {"id": "two"}],
        }
    ) == {
        "title": "Favorites",
        "thumbnail": None,
        "item_count": 2,
        "is_playlist": True,
        "formats": [],
    }


def test_build_video_metadata_uses_highest_resolution_playlist_thumbnail():
    metadata = build_video_metadata(
        {
            "_type": "playlist",
            "thumbnail": None,
            "thumbnails": [
                {"url": "https://i.ytimg.com/low.jpg", "width": 120, "height": 90},
                {"url": "https://i.ytimg.com/high.jpg", "width": 640, "height": 480},
                {"url": "https://i.ytimg.com/medium.jpg", "width": 320, "height": 180},
            ],
        }
    )

    assert metadata["thumbnail"] == "https://i.ytimg.com/high.jpg"


def test_build_video_metadata_falls_back_to_first_available_entry_thumbnail():
    metadata = build_video_metadata(
        {
            "_type": "playlist",
            "entries": [
                {"id": "one"},
                {
                    "id": "two",
                    "thumbnails": [
                        {
                            "url": "https://i.ytimg.com/entry.jpg",
                            "width": 480,
                            "height": 360,
                        }
                    ],
                },
            ],
        }
    )

    assert metadata["thumbnail"] == "https://i.ytimg.com/entry.jpg"
