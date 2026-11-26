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


def build_video_metadata(info: dict[str, Any]) -> dict[str, Any]:
    available_formats = info.get("formats")
    if not isinstance(available_formats, list):
        available_formats = []

    formats = []
    for video_format in available_formats:
        if not isinstance(video_format, dict) or not video_format.get("format_id"):
            continue

        filesize = video_format.get("filesize")
        if filesize is None:
            filesize = video_format.get("filesize_approx")

        formats.append(
            {
                "format_id": video_format["format_id"],
                "ext": video_format.get("ext"),
                "format_note": video_format.get("format_note"),
                "resolution": video_format.get("resolution"),
                "height": video_format.get("height"),
                "fps": video_format.get("fps"),
                "filesize": filesize,
                "video_codec": video_format.get("vcodec"),
                "audio_codec": video_format.get("acodec"),
            }
        )

    return {
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "formats": formats,
    }
