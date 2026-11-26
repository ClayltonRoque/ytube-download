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
