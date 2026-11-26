from pathlib import Path
from typing import Any

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from app.utils.validators import validate_youtube_url


class MediaDownloadError(RuntimeError):
    pass


def download_media(url: str, download_folder: str | Path) -> dict[str, Any]:
    validated_url = validate_youtube_url(url)
    output_folder = Path(download_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    options = {
        "format": "bestvideo*+bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "outtmpl": str(output_folder / "%(id)s.%(ext)s"),
    }

    try:
        with YoutubeDL(options) as youtube_dl:
            info = youtube_dl.extract_info(validated_url, download=True)
    except DownloadError as exc:
        raise MediaDownloadError("Não foi possível baixar o vídeo.") from exc

    if not isinstance(info, dict) or info.get("_type") == "playlist":
        raise MediaDownloadError("O endereço não retornou dados de um vídeo.")

    return info
