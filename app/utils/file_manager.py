import re
from os import PathLike
from pathlib import Path
from typing import Any


_VIDEO_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{11}\Z")
_DOWNLOAD_EXTENSIONS = {"mp3", "m4a", "flac", "wav", "opus", "mp4"}


class DownloadFileError(RuntimeError):
    pass


def resolve_download_file(
    download_info: Any,
    download_folder: str | Path,
) -> Path:
    if not isinstance(download_info, dict):
        raise DownloadFileError("O arquivo concluído não está disponível.")

    file_name = download_info.get("filepath") or download_info.get("_filename")
    try:
        root = Path(download_folder).resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise DownloadFileError("O arquivo concluído não está disponível.") from exc

    if not root.is_dir():
        raise DownloadFileError("O arquivo concluído não está disponível.")

    candidates = []
    if isinstance(file_name, (str, PathLike)) and file_name:
        candidates.append(Path(file_name))

    video_id = download_info.get("id")
    extension = download_info.get("ext")
    if (
        isinstance(video_id, str)
        and _VIDEO_ID_PATTERN.fullmatch(video_id)
        and isinstance(extension, str)
        and extension in _DOWNLOAD_EXTENSIONS
    ):
        candidates.append(Path(f"{video_id}.{extension}"))

    for candidate in candidates:
        if not candidate.is_absolute():
            candidate = root / candidate
        try:
            resolved_file = candidate.resolve(strict=True)
            resolved_file.relative_to(root)
        except (OSError, RuntimeError, ValueError):
            continue
        if resolved_file.is_file():
            return resolved_file

    raise DownloadFileError("O arquivo concluído não está disponível.")
