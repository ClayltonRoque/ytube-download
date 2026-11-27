import pytest

from app.utils.file_manager import DownloadFileError, resolve_download_file


def test_resolve_download_file_returns_file_inside_download_folder(tmp_path):
    download_folder = tmp_path / "downloads"
    download_folder.mkdir()
    output_file = download_folder / "video.mp4"
    output_file.write_bytes(b"video")

    resolved = resolve_download_file(
        {"filepath": str(output_file)},
        download_folder,
    )

    assert resolved == output_file.resolve()


def test_resolve_download_file_accepts_relative_filename(tmp_path):
    download_folder = tmp_path / "downloads"
    download_folder.mkdir()
    output_file = download_folder / "audio.mp3"
    output_file.write_bytes(b"audio")

    assert resolve_download_file(
        {"_filename": "audio.mp3"},
        download_folder,
    ) == output_file.resolve()


def test_resolve_download_file_accepts_zip_archives(tmp_path):
    download_folder = tmp_path / "downloads"
    download_folder.mkdir()
    output_file = download_folder / "Favorites.zip"
    output_file.write_bytes(b"archive")

    assert resolve_download_file(
        {"filepath": str(output_file), "ext": "zip"},
        download_folder,
    ) == output_file.resolve()


def test_resolve_download_file_falls_back_to_video_id_and_final_extension(
    tmp_path,
):
    download_folder = tmp_path / "downloads"
    download_folder.mkdir()
    output_file = download_folder / "AbC123_456-.mp3"
    output_file.write_bytes(b"audio")

    resolved = resolve_download_file(
        {
            "filepath": str(download_folder / "AbC123_456-.webm"),
            "id": "AbC123_456-",
            "ext": "mp3",
        },
        download_folder,
    )

    assert resolved == output_file.resolve()


def test_resolve_download_file_falls_back_when_reported_extension_is_stale(
    tmp_path,
):
    download_folder = tmp_path / "downloads"
    download_folder.mkdir()
    output_file = download_folder / "AbC123_456-.mp3"
    output_file.write_bytes(b"audio")

    resolved = resolve_download_file(
        {
            "filepath": str(download_folder / "AbC123_456-.webm"),
            "id": "AbC123_456-",
            "ext": "webm",
        },
        download_folder,
    )

    assert resolved == output_file.resolve()


def test_resolve_download_file_rejects_ambiguous_id_fallback(tmp_path):
    download_folder = tmp_path / "downloads"
    download_folder.mkdir()
    (download_folder / "AbC123_456-.mp3").write_bytes(b"audio")
    (download_folder / "AbC123_456-.mp4").write_bytes(b"video")

    with pytest.raises(DownloadFileError):
        resolve_download_file(
            {"id": "AbC123_456-", "ext": "webm"},
            download_folder,
        )


@pytest.mark.parametrize(
    "download_info",
    [
        {},
        {"filepath": "../outside.mp4"},
        {"filepath": "missing.mp4"},
        {"filepath": 123},
        {"id": "AbC123_456-", "ext": ["mp3"]},
    ],
)
def test_resolve_download_file_rejects_missing_or_unsafe_paths(
    tmp_path, download_info
):
    download_folder = tmp_path / "downloads"
    download_folder.mkdir()

    with pytest.raises(DownloadFileError):
        resolve_download_file(download_info, download_folder)


def test_resolve_download_file_rejects_symlink_outside_download_folder(tmp_path):
    download_folder = tmp_path / "downloads"
    download_folder.mkdir()
    outside_file = tmp_path / "secret.txt"
    outside_file.write_text("secret")
    (download_folder / "linked.txt").symlink_to(outside_file)

    with pytest.raises(DownloadFileError):
        resolve_download_file(
            {"filepath": "linked.txt"},
            download_folder,
        )
