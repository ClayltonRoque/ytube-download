import re
from urllib.parse import parse_qs, urlsplit


_YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}
_VIDEO_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{11}\Z")
_VIDEO_PATHS = {"embed", "live", "shorts", "v"}
_AUDIO_FORMATS = {"mp3", "m4a", "flac", "wav", "opus"}
_MP3_QUALITIES = {128, 192, 320}
_VIDEO_FORMATS = {"mp4"}


def validate_youtube_url(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Informe uma URL válida do YouTube.")

    url = value.strip()
    if not url or any(character.isspace() for character in url):
        raise ValueError("Informe uma URL válida do YouTube.")

    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Informe uma URL válida do YouTube.") from exc

    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"} or hostname is None:
        raise ValueError("A URL deve usar HTTP ou HTTPS.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("A URL não pode conter credenciais.")

    hostname = hostname.lower()
    if hostname not in _YOUTUBE_HOSTS:
        raise ValueError("A URL deve pertencer ao YouTube.")

    expected_port = 80 if scheme == "http" else 443
    if port is not None and port != expected_port:
        raise ValueError("A URL contém uma porta não permitida.")

    query = parse_qs(parsed.query, keep_blank_values=True)
    if "list" in query:
        raise ValueError("URLs de playlists ainda não são suportadas.")

    video_id = None
    path_segments = [segment for segment in parsed.path.split("/") if segment]

    if hostname.endswith("youtu.be"):
        if len(path_segments) == 1:
            video_id = path_segments[0]
    elif parsed.path.rstrip("/") == "/watch":
        video_ids = query.get("v", [])
        if len(video_ids) == 1:
            video_id = video_ids[0]
    elif (
        len(path_segments) == 2
        and path_segments[0] in _VIDEO_PATHS
        and (not hostname.endswith("youtube-nocookie.com") or path_segments[0] == "embed")
    ):
        video_id = path_segments[1]

    if video_id is None or _VIDEO_ID_PATTERN.fullmatch(video_id) is None:
        raise ValueError("A URL não contém um ID de vídeo válido do YouTube.")

    return url


def _parse_quality(value, option_name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{option_name} deve ser um número inteiro.")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isascii() and value.isdigit():
        return int(value)
    raise ValueError(f"{option_name} deve ser um número inteiro.")


def validate_audio_options(
    audio_format: str,
    audio_quality: int | str | None = None,
) -> tuple[str, int | None]:
    if not isinstance(audio_format, str):
        raise ValueError("Formato de áudio inválido.")

    audio_format = audio_format.lower()
    if audio_format not in _AUDIO_FORMATS:
        raise ValueError("Formato de áudio não suportado.")
    if audio_quality is None:
        return audio_format, None
    if audio_format != "mp3":
        raise ValueError("A seleção de bitrate está disponível apenas para MP3.")

    quality = _parse_quality(audio_quality, "Bitrate MP3")
    if quality not in _MP3_QUALITIES:
        raise ValueError("Bitrate MP3 deve ser 128, 192 ou 320 kbps.")

    return audio_format, quality


def validate_video_format(video_format: str) -> str:
    if not isinstance(video_format, str) or video_format.lower() not in _VIDEO_FORMATS:
        raise ValueError("Formato de vídeo não suportado.")
    return video_format.lower()


def parse_video_quality(video_quality: int | str | None) -> int | None:
    if video_quality is None:
        return None
    if isinstance(video_quality, str) and video_quality.lower() in {"auto", "best"}:
        return None

    return _parse_quality(video_quality, "Resolução de vídeo")


def validate_video_quality(
    video_quality: int | str | None,
    available_formats: list[dict],
) -> int | None:
    quality = parse_video_quality(video_quality)
    if quality is None:
        return None
    if not isinstance(available_formats, list):
        available_formats = []
    has_video_quality = any(
        isinstance(video_format, dict)
        and video_format.get("height") == quality
        and video_format.get("vcodec") not in (None, "none")
        for video_format in available_formats
    )
    if not has_video_quality:
        raise ValueError("A resolução selecionada não está disponível neste vídeo.")

    return quality
