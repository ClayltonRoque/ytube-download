import re
import zipfile
from pathlib import Path
from typing import Any, Callable

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from app.services.youtube import YouTubeQueryError, get_video_info
from app.utils.validators import (
    is_youtube_playlist_url,
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


def download_playlist(
    url: str,
    download_folder: str | Path,
    media_type: str = "audio",
    audio_format: str = "mp3",
    audio_quality: int | str | None = None,
    video_format: str = "mp4",
    video_quality: int | str | None = None,
    progress_hook: ProgressHook | None = None,
) -> dict[str, Any]:
    validated_url = validate_youtube_url(url)
    if not is_youtube_playlist_url(validated_url):
        raise ValueError("Informe uma URL de playlist do YouTube.")

    try:
        playlist_info = get_video_info(validated_url)
    except YouTubeQueryError as exc:
        raise MediaDownloadError(
            "Não foi possível consultar os dados da playlist."
        ) from exc
    playlist_title = playlist_info.get("title")
    if not isinstance(playlist_title, str) or not playlist_title.strip():
        raise MediaDownloadError("Não foi possível identificar o nome da playlist.")
    playlist_entries = playlist_info.get("entries")
    playlist_count = playlist_info.get("playlist_count")
    if not isinstance(playlist_count, int) or isinstance(playlist_count, bool):
        playlist_count = (
            sum(1 for entry in playlist_entries if isinstance(entry, dict))
            if isinstance(playlist_entries, (list, tuple))
            else None
        )
    safe_title = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', "", playlist_title)
    safe_title = " ".join(safe_title.split()).strip(" .")[:180]
    if not safe_title:
        safe_title = "playlist"

    output_root = Path(download_folder)
    playlist_folder = output_root / safe_title
    playlist_folder.mkdir(parents=True, exist_ok=True)

    if media_type == "audio":
        audio_format, audio_quality = validate_audio_options(
            audio_format, audio_quality
        )
        postprocessor = {
            "key": "FFmpegExtractAudio",
            "preferredcodec": audio_format,
        }
        if audio_quality is not None:
            postprocessor["preferredquality"] = str(audio_quality)
        media_options = {
            "format": "bestaudio/best",
            "postprocessors": [postprocessor],
        }
    elif media_type == "video":
        video_format = validate_video_format(video_format)
        validated_quality = parse_video_quality(video_quality)
        if validated_quality is not None:
            validated_quality = validate_video_quality(
                validated_quality,
                playlist_info.get("formats", []),
            )
        format_selector = (
            f"bestvideo[ext={video_format}]+bestaudio[ext=m4a]/"
            f"best[ext={video_format}]/bestvideo+bestaudio/best"
        )
        if validated_quality is not None:
            format_selector = (
                f"bestvideo[height={validated_quality}][ext={video_format}]+"
                "bestaudio[ext=m4a]/"
                f"best[height={validated_quality}][ext={video_format}]/"
                f"bestvideo[height={validated_quality}]+bestaudio/"
                f"best[height={validated_quality}]"
            )
        media_options = {
            "format": format_selector,
            "merge_output_format": video_format,
        }
    else:
        raise ValueError("O tipo de mídia deve ser 'audio' ou 'video'.")

    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": False,
        "outtmpl": str(playlist_folder / "%(title)s [%(id)s].%(ext)s"),
        **media_options,
    }
    if progress_hook is not None:
        def report_playlist_progress(info: dict[str, Any]) -> None:
            entry_info = info.get("info_dict")
            if not isinstance(entry_info, dict):
                entry_info = {}

            current_index = entry_info.get("playlist_index")
            if not isinstance(current_index, int) or isinstance(current_index, bool):
                current_index = None
            current_count = entry_info.get("playlist_count")
            if not isinstance(current_count, int) or isinstance(current_count, bool):
                current_count = playlist_count
            title = entry_info.get("title")

            progress_hook(
                {
                    "is_playlist": True,
                    "status": info.get("status"),
                    "playlist_index": current_index,
                    "playlist_count": current_count,
                    "title": title if isinstance(title, str) else None,
                }
            )

        options["progress_hooks"] = [report_playlist_progress]

    try:
        with YoutubeDL(options) as youtube_dl:
            result = youtube_dl.extract_info(validated_url, download=True)
    except DownloadError as exc:
        raise MediaDownloadError("Não foi possível baixar a playlist.") from exc

    if not isinstance(result, dict) or result.get("_type") != "playlist":
        raise MediaDownloadError("O endereço não retornou dados de uma playlist.")

    downloaded_files = []
    try:
        for candidate in playlist_folder.rglob("*"):
            if candidate.is_file():
                resolved = candidate.resolve(strict=True)
                resolved.relative_to(playlist_folder.resolve(strict=True))
                downloaded_files.append(resolved)
    except (OSError, RuntimeError, ValueError) as exc:
        raise MediaDownloadError(
            "Não foi possível localizar os arquivos da playlist."
        ) from exc
    if not downloaded_files:
        raise MediaDownloadError("A playlist não contém arquivos para compactar.")
    downloaded_files.sort()

    archive_path = output_root / f"{safe_title}.zip"
    try:
        with zipfile.ZipFile(
            archive_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            for file_path in downloaded_files:
                archive.write(file_path, file_path.relative_to(playlist_folder))
    except OSError as exc:
        raise MediaDownloadError("Não foi possível compactar a playlist.") from exc

    return {
        "filepath": str(archive_path),
        "title": safe_title,
        "ext": "zip",
    }
