from unittest.mock import patch

import pytest
from yt_dlp.utils import DownloadError

from app.services.downloader import (
    MediaDownloadError,
    download_audio,
    download_media,
    download_video,
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


@patch("app.services.downloader.YoutubeDL")
def test_download_audio_uses_selected_format_and_mp3_bitrate(
    youtube_dl_class, tmp_path
):
    youtube_dl = youtube_dl_class.return_value.__enter__.return_value
    youtube_dl.extract_info.return_value = {"id": "AbC123_456-"}

    download_audio(
        VIDEO_URL,
        tmp_path / "downloads",
        audio_format="mp3",
        audio_quality="320",
    )

    options = youtube_dl_class.call_args.args[0]
    assert options["postprocessors"] == [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "320",
        }
    ]


@patch("app.services.downloader.YoutubeDL")
def test_download_audio_uses_selected_non_mp3_format(youtube_dl_class, tmp_path):
    youtube_dl = youtube_dl_class.return_value.__enter__.return_value
    youtube_dl.extract_info.return_value = {"id": "AbC123_456-"}

    download_audio(
        VIDEO_URL,
        tmp_path / "downloads",
        audio_format="flac",
    )

    options = youtube_dl_class.call_args.args[0]
    assert options["postprocessors"] == [
        {"key": "FFmpegExtractAudio", "preferredcodec": "flac"}
    ]


@patch("app.services.downloader.YoutubeDL")
def test_download_audio_rejects_invalid_options_without_creating_folder(
    youtube_dl_class, tmp_path
):
    output_folder = tmp_path / "downloads"

    with pytest.raises(ValueError):
        download_audio(
            VIDEO_URL,
            output_folder,
            audio_format="flac",
            audio_quality=192,
        )

    assert not output_folder.exists()
    youtube_dl_class.assert_not_called()


@patch("app.services.downloader.YoutubeDL")
def test_download_video_prefers_mp4_and_merges_with_ffmpeg(
    youtube_dl_class, tmp_path
):
    expected_info = {"id": "AbC123_456-", "title": "Test video"}
    youtube_dl = youtube_dl_class.return_value.__enter__.return_value
    youtube_dl.extract_info.return_value = expected_info

    result = download_video(VIDEO_URL, tmp_path / "downloads")

    assert result is expected_info
    options = youtube_dl_class.call_args.args[0]
    assert options["format"] == (
        "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/"
        "bestvideo+bestaudio/best"
    )
    assert options["merge_output_format"] == "mp4"
    assert options["noplaylist"] is True
    youtube_dl.extract_info.assert_called_once_with(VIDEO_URL, download=True)


def test_download_video_selects_available_resolution(tmp_path):
    with (
        patch("app.services.downloader.YoutubeDL") as youtube_dl_class,
        patch(
            "app.services.downloader.get_video_info",
            return_value={
                "formats": [{"height": 720, "vcodec": "avc1", "acodec": "none"}]
            },
        ) as get_video_info,
    ):
        youtube_dl = youtube_dl_class.return_value.__enter__.return_value
        youtube_dl.extract_info.return_value = {"id": "AbC123_456-"}

        download_video(VIDEO_URL, tmp_path / "downloads", video_quality="720")

    get_video_info.assert_called_once_with(VIDEO_URL)
    options = youtube_dl_class.call_args.args[0]
    assert options["format"] == (
        "bestvideo[height=720][ext=mp4]+bestaudio[ext=m4a]/"
        "best[height=720][ext=mp4]/bestvideo[height=720]+bestaudio/"
        "best[height=720]"
    )


def test_download_video_rejects_unavailable_resolution_before_download(tmp_path):
    with (
        patch("app.services.downloader.YoutubeDL") as youtube_dl_class,
        patch(
            "app.services.downloader.get_video_info",
            return_value={
                "formats": [{"height": 720, "vcodec": "avc1", "acodec": "none"}]
            },
        ),
    ):
        with pytest.raises(ValueError, match="não está disponível"):
            download_video(
                VIDEO_URL,
                tmp_path / "downloads",
                video_quality=1080,
            )

    youtube_dl_class.assert_not_called()
    assert not (tmp_path / "downloads").exists()


def test_download_video_rejects_unsupported_format_before_query(tmp_path):
    with (
        patch("app.services.downloader.YoutubeDL") as youtube_dl_class,
        patch("app.services.downloader.get_video_info") as get_video_info,
    ):
        with pytest.raises(ValueError, match="Formato de vídeo"):
            download_video(
                VIDEO_URL,
                tmp_path / "downloads",
                video_format="webm",
                video_quality=720,
            )

    youtube_dl_class.assert_not_called()
    get_video_info.assert_not_called()
