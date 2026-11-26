from functools import lru_cache
from typing import Any
from urllib.parse import urlencode

from requests.exceptions import RequestException
from spotipy import Spotify
from spotipy.cache_handler import MemoryCacheHandler
from spotipy.exceptions import SpotifyException, SpotifyOauthError
from spotipy.oauth2 import SpotifyClientCredentials


class SpotifyConfigurationError(RuntimeError):
    pass


class SpotifyQueryError(RuntimeError):
    pass


@lru_cache(maxsize=4)
def _spotify_client(client_id: str, client_secret: str) -> Spotify:
    auth_manager = SpotifyClientCredentials(
        client_id=client_id,
        client_secret=client_secret,
        cache_handler=MemoryCacheHandler(),
    )
    return Spotify(
        auth_manager=auth_manager,
        requests_timeout=10,
        retries=0,
        status_retries=0,
    )


def build_spotify_track_metadata(
    track: dict[str, Any],
    track_id: str,
) -> dict[str, Any]:
    title = track.get("name")
    raw_artists = track.get("artists")
    artists = (
        [
            artist["name"]
            for artist in raw_artists
            if isinstance(artist, dict) and isinstance(artist.get("name"), str)
        ]
        if isinstance(raw_artists, list)
        else []
    )
    if not isinstance(title, str) or not title.strip() or not artists:
        raise SpotifyQueryError("O Spotify retornou metadados incompletos para a faixa.")

    album = track.get("album")
    album_name = album.get("name") if isinstance(album, dict) else None
    images = album.get("images", []) if isinstance(album, dict) else []
    thumbnail = (
        next(
            (
                image["url"]
                for image in images
                if isinstance(image, dict)
                and isinstance(image.get("url"), str)
                and image["url"].startswith("https://")
            ),
            None,
        )
        if isinstance(images, list)
        else None
    )

    duration_ms = track.get("duration_ms")
    duration = None
    if (
        isinstance(duration_ms, int)
        and not isinstance(duration_ms, bool)
        and duration_ms >= 0
    ):
        duration = duration_ms // 1000
    search_query = f"{title.strip()} {' '.join(artists)}"
    return {
        "title": title.strip(),
        "artists": artists,
        "album": album_name if isinstance(album_name, str) else None,
        "thumbnail": thumbnail,
        "duration": duration,
        "spotify_url": f"https://open.spotify.com/track/{track_id}",
        "youtube_search_url": (
            "https://www.youtube.com/results?"
            f"{urlencode({'search_query': search_query})}"
        ),
    }


def get_spotify_track_metadata(
    track_id: str,
    client_id: str | None,
    client_secret: str | None,
) -> dict[str, Any]:
    if not client_id or not client_secret:
        raise SpotifyConfigurationError(
            "Configure SPOTIFY_CLIENT_ID e SPOTIFY_CLIENT_SECRET para "
            "consultar faixas do Spotify."
        )

    try:
        track = _spotify_client(client_id, client_secret).track(track_id)
    except SpotifyException as exc:
        if exc.http_status == 404:
            raise SpotifyQueryError("A faixa não foi encontrada no Spotify.") from exc
        raise SpotifyQueryError(
            "Não foi possível consultar os metadados no Spotify."
        ) from exc
    except (SpotifyOauthError, RequestException) as exc:
        raise SpotifyQueryError(
            "Não foi possível acessar o Spotify. Verifique a conexão e as credenciais."
        ) from exc

    if not isinstance(track, dict):
        raise SpotifyQueryError("O Spotify retornou uma resposta inválida.")
    return build_spotify_track_metadata(track, track_id)
