import re
from os import PathLike
from pathlib import Path
from typing import Any


_VIDEO_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{11}\Z")
_DOWNLOAD_EXTENSIONS = {
    "mp3",
    "m4a",
    "flac",
    "wav",
    "opus",
    "mp4",
    "webm",
    "mkv",
    "mov",
    "avi",
    "m4v",
    "3gp",
    "ts",
}


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
    valid_video_id = isinstance(video_id, str) and bool(
        _VIDEO_ID_PATTERN.fullmatch(video_id)
    )
    if (
        valid_video_id
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

    if valid_video_id:
        matching_files = set()
        try:
            for candidate in root.glob(f"{video_id}.*"):
                if candidate.suffix[1:] not in _DOWNLOAD_EXTENSIONS:
                    continue
                try:
                    resolved_file = candidate.resolve(strict=True)
                    resolved_file.relative_to(root)
                except (OSError, RuntimeError, ValueError):
                    continue
                if resolved_file.is_file():
                    matching_files.add(resolved_file)
        except OSError as exc:
            raise DownloadFileError(
                "O arquivo concluído não está disponível."
            ) from exc

        if len(matching_files) == 1:
            return matching_files.pop()

    raise DownloadFileError("O arquivo concluído não está disponível.")
