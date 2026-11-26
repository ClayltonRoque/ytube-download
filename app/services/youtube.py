from typing import Any

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from app.utils.validators import validate_youtube_url


class YouTubeQueryError(RuntimeError):
    pass


def get_video_info(url: str) -> dict[str, Any]:
    validated_url = validate_youtube_url(url)
    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
    }

    try:
        with YoutubeDL(options) as youtube_dl:
            info = youtube_dl.extract_info(validated_url, download=False)
    except DownloadError as exc:
        raise YouTubeQueryError("Não foi possível consultar os dados do vídeo.") from exc

    if not isinstance(info, dict) or info.get("_type") == "playlist":
        raise YouTubeQueryError("O endereço não retornou dados de um vídeo.")

    return info
