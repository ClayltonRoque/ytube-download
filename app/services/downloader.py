from pathlib import Path
from typing import Any, Callable

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


ProgressHook = Callable[[dict[str, Any]], None]


def _execute_download(
    url: str,
    download_folder: str | Path,
    media_options: dict[str, Any],
    progress_hook: ProgressHook | None = None,
    *,
    allow_search: bool = False,
) -> dict[str, Any]:
    validated_url = url if allow_search else validate_youtube_url(url)
    output_folder = Path(download_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    options = {
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "outtmpl": str(output_folder / "%(id)s.%(ext)s"),
        **media_options,
    }
    if progress_hook is not None:
        options["progress_hooks"] = [progress_hook]

    try:
        with YoutubeDL(options) as youtube_dl:
            info = youtube_dl.extract_info(validated_url, download=True)
    except DownloadError as exc:
        raise MediaDownloadError("Não foi possível baixar o vídeo.") from exc

    if allow_search and isinstance(info, dict) and info.get("_type") == "playlist":
        entries = info.get("entries")
        info = next((entry for entry in entries or [] if isinstance(entry, dict)), None)
    if not isinstance(info, dict) or info.get("_type") == "playlist":
        raise MediaDownloadError("O endereço não retornou dados de um vídeo.")

    return info


def download_media(
    url: str,
    download_folder: str | Path,
    progress_hook: ProgressHook | None = None,
) -> dict[str, Any]:
    return _execute_download(
        url,
        download_folder,
        {"format": "bestvideo*+bestaudio/best"},
        progress_hook,
    )


def download_audio(
    url: str,
    download_folder: str | Path,
    audio_format: str = "mp3",
    audio_quality: int | str | None = None,
    progress_hook: ProgressHook | None = None,
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
        progress_hook,
    )


def download_spotify_audio(
    metadata: dict[str, Any],
    download_folder: str | Path,
    audio_format: str = "mp3",
    audio_quality: int | str | None = None,
    progress_hook: ProgressHook | None = None,
) -> dict[str, Any]:
    """Find a Spotify track on YouTube and tag the result with FetchTune metadata."""
    title = metadata.get("title")
    artists = metadata.get("artists")
    if not isinstance(title, str) or not title.strip() or not isinstance(artists, list):
        raise ValueError("Os metadados da faixa estão incompletos.")
    artists = [artist.strip() for artist in artists if isinstance(artist, str) and artist.strip()]
    if not artists:
        raise ValueError("Os metadados da faixa estão incompletos.")

    audio_format, audio_quality = validate_audio_options(audio_format, audio_quality)
    postprocessor = {"key": "FFmpegExtractAudio", "preferredcodec": audio_format}
    if audio_quality is not None:
        postprocessor["preferredquality"] = str(audio_quality)
    tag_args = ["-metadata", f"title={title.strip()}", "-metadata", f"artist={', '.join(artists)}"]
    album = metadata.get("album")
    if isinstance(album, str) and album.strip():
        tag_args.extend(["-metadata", f"album={album.strip()}"])

    return _execute_download(
        f"ytsearch1:{title.strip()} {' '.join(artists)}",
        download_folder,
        {
            "format": "bestaudio/best",
            "postprocessors": [postprocessor, {"key": "FFmpegMetadata"}],
            "postprocessor_args": {"FFmpegMetadata": tag_args},
        },
        progress_hook,
        allow_search=True,
    )


def download_video(
    url: str,
    download_folder: str | Path,
    video_format: str = "mp4",
    video_quality: int | str | None = None,
    progress_hook: ProgressHook | None = None,
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
        progress_hook,
    )
