from pathlib import Path
from typing import Any

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from app.services.youtube import YouTubeQueryError, get_video_info
from app.utils.validators import (
    parse_video_quality,
    validate_audio_options,
    validate_video_format,
    validate_video_quality,
    validate_youtube_url,
)


class MediaDownloadError(RuntimeError):
    pass


def _execute_download(
    url: str,
    download_folder: str | Path,
    media_options: dict[str, Any],
) -> dict[str, Any]:
    validated_url = validate_youtube_url(url)
    output_folder = Path(download_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    options = {
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "outtmpl": str(output_folder / "%(id)s.%(ext)s"),
        **media_options,
    }

    try:
        with YoutubeDL(options) as youtube_dl:
            info = youtube_dl.extract_info(validated_url, download=True)
    except DownloadError as exc:
        raise MediaDownloadError("Não foi possível baixar o vídeo.") from exc

    if not isinstance(info, dict) or info.get("_type") == "playlist":
        raise MediaDownloadError("O endereço não retornou dados de um vídeo.")

    return info


def download_media(url: str, download_folder: str | Path) -> dict[str, Any]:
    return _execute_download(
        url,
        download_folder,
        {"format": "bestvideo*+bestaudio/best"},
    )


def download_audio(
    url: str,
    download_folder: str | Path,
    audio_format: str = "mp3",
    audio_quality: int | str | None = None,
) -> dict[str, Any]:
    audio_format, audio_quality = validate_audio_options(audio_format, audio_quality)
    postprocessor = {
        "key": "FFmpegExtractAudio",
        "preferredcodec": audio_format,
    }
    if audio_quality is not None:
        postprocessor["preferredquality"] = str(audio_quality)

    return _execute_download(
        url,
        download_folder,
        {
            "format": "bestaudio/best",
            "postprocessors": [postprocessor],
        },
    )


def download_video(
    url: str,
    download_folder: str | Path,
    video_format: str = "mp4",
    video_quality: int | str | None = None,
) -> dict[str, Any]:
    video_format = validate_video_format(video_format)
    validated_quality = parse_video_quality(video_quality)
    if validated_quality is not None:
        validated_url = validate_youtube_url(url)
        try:
            video_info = get_video_info(validated_url)
        except YouTubeQueryError as exc:
            raise MediaDownloadError(
                "Não foi possível validar a resolução do vídeo."
            ) from exc
        validated_quality = validate_video_quality(
            validated_quality,
            video_info.get("formats", []),
        )

    if validated_quality is None:
        format_selector = (
            f"bestvideo[ext={video_format}]+bestaudio[ext=m4a]/"
            f"best[ext={video_format}]/bestvideo+bestaudio/best"
        )
    else:
        format_selector = (
            f"bestvideo[height={validated_quality}][ext={video_format}]+"
            "bestaudio[ext=m4a]/"
            f"best[height={validated_quality}][ext={video_format}]/"
            f"bestvideo[height={validated_quality}]+bestaudio/"
            f"best[height={validated_quality}]"
        )

    return _execute_download(
        url,
        download_folder,
        {
            "format": format_selector,
            "merge_output_format": video_format,
        },
    )
