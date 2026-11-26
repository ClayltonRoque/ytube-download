import re

from flask import Blueprint, current_app, jsonify, request, send_file

from app.services.downloader import download_audio, download_video
from app.services.download_tasks import DownloadTaskManager
from app.services.spotify import (
    SpotifyConfigurationError,
    SpotifyQueryError,
    get_spotify_track_metadata,
)
from app.services.youtube import (
    YouTubeQueryError,
    build_video_metadata,
    get_video_info,
)
from app.utils.validators import (
    is_spotify_url,
    parse_video_quality,
    validate_audio_options,
    validate_spotify_track_url,
    validate_video_format,
    validate_youtube_url,
)
from app.utils.file_manager import DownloadFileError, resolve_download_file


bp = Blueprint("downloads", __name__, url_prefix="/api")
_INVALID_FILENAME_CHARACTERS = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')


def _error_response(code, message, status_code):
    return jsonify(
        {
            "success": False,
            "error": {
                "code": code,
                "message": message,
            },
        }
    ), status_code


def _download_name(download_info, file_path):
    title = download_info.get("title")
    if not isinstance(title, str):
        return file_path.name

    safe_title = _INVALID_FILENAME_CHARACTERS.sub("", title)
    safe_title = " ".join(safe_title.split()).strip(" .")
    if not safe_title:
        return file_path.name
    return f"{safe_title}{file_path.suffix}"


@bp.post("/metadata")
def metadata():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _error_response(
            "invalid_request",
            "Envie um objeto JSON com o campo 'url'.",
            400,
        )

    url = data.get("url")
    if is_spotify_url(url):
        try:
            track_id = validate_spotify_track_url(url)
        except ValueError as exc:
            return _error_response("invalid_url", str(exc), 400)

        try:
            spotify_metadata = get_spotify_track_metadata(
                track_id,
                current_app.config.get("SPOTIFY_CLIENT_ID"),
                current_app.config.get("SPOTIFY_CLIENT_SECRET"),
            )
        except SpotifyConfigurationError as exc:
            return _error_response("spotify_not_configured", str(exc), 503)
        except SpotifyQueryError as exc:
            return _error_response("provider_error", str(exc), 502)

        return jsonify(
            {
                "success": True,
                "provider": "spotify",
                "metadata": spotify_metadata,
            }
        )

    try:
        url = validate_youtube_url(url)
    except ValueError as exc:
        return _error_response("invalid_url", str(exc), 400)

    try:
        info = get_video_info(url)
    except YouTubeQueryError as exc:
        return _error_response("provider_error", str(exc), 502)

    return jsonify({"success": True, "metadata": build_video_metadata(info)})


@bp.post("/download")
def start_download():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _error_response(
            "invalid_request",
            "Envie um objeto JSON com URL, tipo de mídia e opções.",
            400,
        )

    try:
        url = validate_youtube_url(data.get("url"))
    except ValueError as exc:
        return _error_response("invalid_url", str(exc), 400)

    media_type = data.get("media_type")
    if media_type == "audio":
        try:
            audio_format, audio_quality = validate_audio_options(
                data.get("format", "mp3"),
                data.get("quality"),
            )
        except ValueError as exc:
            return _error_response("invalid_options", str(exc), 400)

        download_function = download_audio
        download_options = {
            "audio_format": audio_format,
            "audio_quality": audio_quality,
        }
    elif media_type == "video":
        try:
            video_format = validate_video_format(data.get("format", "mp4"))
            video_quality = parse_video_quality(data.get("quality"))
        except ValueError as exc:
            return _error_response("invalid_options", str(exc), 400)

        download_function = download_video
        download_options = {
            "video_format": video_format,
            "video_quality": video_quality,
        }
    else:
        return _error_response(
            "invalid_media_type",
            "O tipo de mídia deve ser 'audio' ou 'video'.",
            400,
        )

    task_manager: DownloadTaskManager = current_app.extensions[
        "download_task_manager"
    ]
    task = task_manager.create_task(
        download_function,
        url,
        current_app.config["DOWNLOAD_FOLDER"],
        **download_options,
    )

    return jsonify(
        {
            "success": True,
            "task": {
                "id": task.id,
                "status": task.status,
            },
        }
    ), 202


@bp.get("/download/progress/<task_id>")
def download_progress(task_id):
    task_manager: DownloadTaskManager = current_app.extensions[
        "download_task_manager"
    ]
    task = task_manager.get_task(task_id)
    if task is None:
        return _error_response(
            "task_not_found",
            "Tarefa de download não encontrada.",
            404,
        )

    return jsonify(
        {
            "success": True,
            "task": {
                "id": task.id,
                "status": task.status,
                "progress": task.progress,
                "error": task.error,
            },
        }
    )


@bp.get("/download/file/<task_id>")
def download_file(task_id):
    task_manager: DownloadTaskManager = current_app.extensions[
        "download_task_manager"
    ]
    task = task_manager.get_task(task_id)
    if task is None:
        return _error_response(
            "task_not_found",
            "Tarefa de download não encontrada.",
            404,
        )
    if task.status != "completed" or task.future is None:
        return _error_response(
            "file_not_ready",
            "O arquivo ainda não está disponível.",
            409,
        )

    download_info = task.future.result()
    try:
        file_path = resolve_download_file(
            download_info,
            current_app.config["DOWNLOAD_FOLDER"],
        )
    except DownloadFileError as exc:
        return _error_response("file_unavailable", str(exc), 404)

    return send_file(
        file_path,
        as_attachment=True,
        download_name=_download_name(download_info, file_path),
    )
