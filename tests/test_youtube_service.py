from unittest.mock import patch

import pytest
from yt_dlp.utils import DownloadError

from app.services.youtube import YouTubeQueryError, get_video_info


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
