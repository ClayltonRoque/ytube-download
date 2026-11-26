from flask import Blueprint, jsonify, request

from app.services.youtube import (
    YouTubeQueryError,
    build_video_metadata,
    get_video_info,
)
from app.utils.validators import validate_youtube_url


bp = Blueprint("downloads", __name__, url_prefix="/api")


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


@bp.post("/metadata")
def metadata():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _error_response(
            "invalid_request",
            "Envie um objeto JSON com o campo 'url'.",
            400,
        )

    try:
        url = validate_youtube_url(data.get("url"))
    except ValueError as exc:
        return _error_response("invalid_url", str(exc), 400)

    try:
        info = get_video_info(url)
    except YouTubeQueryError as exc:
        return _error_response("provider_error", str(exc), 502)

    return jsonify({"success": True, "metadata": build_video_metadata(info)})
