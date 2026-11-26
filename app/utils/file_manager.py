from os import PathLike
from pathlib import Path
from typing import Any


class DownloadFileError(RuntimeError):
    pass


def resolve_download_file(
    download_info: Any,
    download_folder: str | Path,
) -> Path:
    if not isinstance(download_info, dict):
        raise DownloadFileError("O arquivo concluído não está disponível.")

    file_name = download_info.get("filepath") or download_info.get("_filename")
    if not isinstance(file_name, (str, PathLike)) or not file_name:
        raise DownloadFileError("O arquivo concluído não está disponível.")

    try:
        root = Path(download_folder).resolve(strict=True)
        candidate = Path(file_name)
        if not candidate.is_absolute():
            candidate = root / candidate
        resolved_file = candidate.resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise DownloadFileError("O arquivo concluído não está disponível.") from exc

    try:
        resolved_file.relative_to(root)
    except ValueError as exc:
        raise DownloadFileError("O arquivo concluído não está disponível.") from exc

    if not root.is_dir() or not resolved_file.is_file():
        raise DownloadFileError("O arquivo concluído não está disponível.")

    return resolved_file
