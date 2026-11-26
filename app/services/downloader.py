from pathlib import Path
from typing import Any

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from app.utils.validators import validate_youtube_url


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


def download_audio(url: str, download_folder: str | Path) -> dict[str, Any]:
    return _execute_download(
        url,
        download_folder,
        {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                }
            ],
        },
    )
