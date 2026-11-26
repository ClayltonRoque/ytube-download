from typing import Any
from urllib.parse import urlencode

from fetchtune import Resolver, ResolverError
from fetchtune.providers.spotify import SpotifyProvider


class FetchTuneMetadataError(RuntimeError):
    pass


def get_spotify_track_metadata(track_id: str) -> dict[str, Any]:
    spotify_url = f"https://open.spotify.com/track/{track_id}"
    resolver = Resolver(
        providers=[SpotifyProvider()],
        enrichment=False,
    )

    try:
        track = resolver.resolve(spotify_url)
    except ResolverError as exc:
        raise FetchTuneMetadataError(
            "Não foi possível consultar os metadados da faixa no Spotify."
        ) from exc

    title = getattr(track, "title", None)
    if not isinstance(title, str) or not title.strip():
        raise FetchTuneMetadataError(
            "O FetchTune retornou metadados incompletos para a faixa."
        )

    raw_artists = getattr(track, "artist_names", [])
    artists = [
        artist.strip()
        for artist in raw_artists
        if isinstance(artist, str) and artist.strip()
    ] if isinstance(raw_artists, list) else []
    if not artists:
        raise FetchTuneMetadataError(
            "O FetchTune não encontrou o artista da faixa."
        )

    album = getattr(track, "album", None)
    album_name = getattr(album, "name", None)
    cover_url = getattr(track, "cover_url", None)
    duration_ms = getattr(track, "duration_ms", None)
    duration = (
        duration_ms // 1000
        if isinstance(duration_ms, int)
        and not isinstance(duration_ms, bool)
        and duration_ms >= 0
        else None
    )
    search_query = f"{title.strip()} {' '.join(artists)}"

    return {
        "title": title.strip(),
        "artists": artists,
        "album": album_name if isinstance(album_name, str) else None,
        "thumbnail": cover_url if isinstance(cover_url, str) else None,
        "duration": duration,
        "spotify_url": spotify_url,
        "youtube_search_url": (
            "https://www.youtube.com/results?"
            f"{urlencode({'search_query': search_query})}"
        ),
    }
