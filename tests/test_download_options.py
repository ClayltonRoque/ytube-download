import pytest

from app.utils.validators import (
    validate_audio_options,
    validate_video_format,
    validate_video_quality,
)


@pytest.mark.parametrize("audio_format", ["mp3", "m4a", "flac", "wav", "opus"])
def test_validate_supported_audio_formats(audio_format):
    assert validate_audio_options(audio_format) == (audio_format, None)


@pytest.mark.parametrize("quality", [128, 192, 320, "128", "192", "320"])
def test_validate_mp3_qualities(quality):
    assert validate_audio_options("mp3", quality) == ("mp3", int(quality))


@pytest.mark.parametrize(
    ("audio_format", "quality"),
    [
        ("aac", None),
        ("mp3", 256),
        ("mp3", "320.0"),
        ("mp3", True),
        ("flac", 192),
    ],
)
def test_rejects_unsupported_audio_options(audio_format, quality):
    with pytest.raises(ValueError):
        validate_audio_options(audio_format, quality)


def test_validate_mp4_video_format_case_insensitively():
    assert validate_video_format("MP4") == "mp4"


def test_reject_unsupported_video_format():
    with pytest.raises(ValueError):
        validate_video_format("webm")


def test_validate_video_quality_only_when_video_format_exists():
    formats = [
        {"height": 720, "vcodec": "avc1"},
        {"height": 1080, "vcodec": "none"},
    ]

    assert validate_video_quality("720", formats) == 720
    assert validate_video_quality("best", formats) is None


@pytest.mark.parametrize("quality", [1080, "invalid", True])
def test_reject_unavailable_or_invalid_video_quality(quality):
    formats = [{"height": 720, "vcodec": "avc1"}]

    with pytest.raises(ValueError):
        validate_video_quality(quality, formats)
