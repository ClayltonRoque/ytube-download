from typing import Any

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from app.utils.validators import is_youtube_playlist_url, validate_youtube_url


class YouTubeQueryError(RuntimeError):
    pass


def _thumbnail_from_info(info: dict[str, Any]) -> str | None:
    thumbnail = info.get("thumbnail")
    if isinstance(thumbnail, str) and thumbnail.strip():
        return thumbnail

    thumbnails = info.get("thumbnails")
    if not isinstance(thumbnails, list):
        return None

    candidates = []
    for index, item in enumerate(thumbnails):
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if not isinstance(url, str) or not url.strip():
            continue
        width = item.get("width")
        height = item.get("height")
        width = (
            width if isinstance(width, int) and not isinstance(width, bool) else 0
        )
        height = (
            height if isinstance(height, int) and not isinstance(height, bool) else 0
        )
        candidates.append(((width * height, width + height, index), url))

    if not candidates:
        return None
    return max(candidates, key=lambda candidate: candidate[0])[1]


def get_video_info(url: str) -> dict[str, Any]:
    validated_url = validate_youtube_url(url)
    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": not is_youtube_playlist_url(validated_url),
        "skip_download": True,
    }
    if is_youtube_playlist_url(validated_url):
        options["extract_flat"] = True

    try:
        with YoutubeDL(options) as youtube_dl:
            info = youtube_dl.extract_info(validated_url, download=False)
    except DownloadError as exc:
        raise YouTubeQueryError("Não foi possível consultar os dados do vídeo.") from exc

    if not isinstance(info, dict):
        raise YouTubeQueryError("O endereço não retornou dados de mídia.")
    if is_youtube_playlist_url(validated_url) and info.get("_type") != "playlist":
        raise YouTubeQueryError("O endereço não retornou dados de uma playlist.")
    if not is_youtube_playlist_url(validated_url) and info.get("_type") == "playlist":
        raise YouTubeQueryError("O endereço não retornou dados de um vídeo.")

    return info


def build_video_metadata(info: dict[str, Any]) -> dict[str, Any]:
    if info.get("_type") == "playlist":
        entries = info.get("entries")
        item_count = (
            sum(1 for entry in entries if isinstance(entry, dict))
            if isinstance(entries, (list, tuple))
            else info.get("playlist_count")
        )
        if not isinstance(item_count, int) or isinstance(item_count, bool):
            item_count = None
        thumbnail = _thumbnail_from_info(info)
        if thumbnail is None and isinstance(entries, (list, tuple)):
            for entry in entries:
                if isinstance(entry, dict):
                    thumbnail = _thumbnail_from_info(entry)
                    if thumbnail is not None:
                        break
        return {
            "title": info.get("title"),
            "thumbnail": thumbnail,
            "item_count": item_count,
            "is_playlist": True,
            "formats": [],
        }

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
