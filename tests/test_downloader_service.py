from unittest.mock import patch

import pytest
from yt_dlp.utils import DownloadError

from app.services.downloader import (
    MediaDownloadError,
    download_audio,
    download_media,
)


VIDEO_URL = "https://www.youtube.com/watch?v=AbC123_456-"


@patch("app.services.downloader.YoutubeDL")
def test_download_media_uses_safe_output_template_and_downloads(
    youtube_dl_class, tmp_path
):
    expected_info = {"id": "AbC123_456-", "title": "Test video"}
    youtube_dl = youtube_dl_class.return_value.__enter__.return_value
    youtube_dl.extract_info.return_value = expected_info

    result = download_media(VIDEO_URL, tmp_path / "downloads")

    assert result is expected_info
    assert (tmp_path / "downloads").is_dir()
    options = youtube_dl_class.call_args.args[0]
    assert options["format"] == "bestvideo*+bestaudio/best"
    assert options["noplaylist"] is True
    assert options["outtmpl"] == str(
        tmp_path / "downloads" / "%(id)s.%(ext)s"
    )
    youtube_dl.extract_info.assert_called_once_with(VIDEO_URL, download=True)


@patch("app.services.downloader.YoutubeDL")
def test_download_media_rejects_invalid_url_without_creating_folder(
    youtube_dl_class, tmp_path
):
    output_folder = tmp_path / "downloads"

    with pytest.raises(ValueError):
        download_media("https://example.com/video", output_folder)

    assert not output_folder.exists()
    youtube_dl_class.assert_not_called()


@patch("app.services.downloader.YoutubeDL")
def test_download_media_wraps_ytdlp_errors(youtube_dl_class, tmp_path):
    youtube_dl = youtube_dl_class.return_value.__enter__.return_value
    youtube_dl.extract_info.side_effect = DownloadError("provider error")

    with pytest.raises(MediaDownloadError) as error:
        download_media(VIDEO_URL, tmp_path / "downloads")

    assert isinstance(error.value.__cause__, DownloadError)


@patch("app.services.downloader.YoutubeDL")
def test_download_media_rejects_playlist_results(youtube_dl_class, tmp_path):
    youtube_dl = youtube_dl_class.return_value.__enter__.return_value
    youtube_dl.extract_info.return_value = {"_type": "playlist", "entries": []}

    with pytest.raises(MediaDownloadError):
        download_media(VIDEO_URL, tmp_path / "downloads")


@patch("app.services.downloader.YoutubeDL")
def test_download_audio_extracts_mp3_with_ffmpeg(youtube_dl_class, tmp_path):
    expected_info = {"id": "AbC123_456-", "title": "Test video"}
    youtube_dl = youtube_dl_class.return_value.__enter__.return_value
    youtube_dl.extract_info.return_value = expected_info

    result = download_audio(VIDEO_URL, tmp_path / "downloads")

    assert result is expected_info
    options = youtube_dl_class.call_args.args[0]
    assert options["format"] == "bestaudio/best"
    assert options["postprocessors"] == [
        {"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}
    ]
    assert options["noplaylist"] is True
    youtube_dl.extract_info.assert_called_once_with(VIDEO_URL, download=True)
