from threading import get_ident

import pytest

from app.services.download_runner import submit_download


def test_submit_download_runs_in_a_worker_thread():
    caller_thread = get_ident()

    future = submit_download(get_ident)

    assert future.result(timeout=2) != caller_thread


def test_submit_download_exposes_worker_exceptions():
    def fail():
        raise RuntimeError("download failed")

    future = submit_download(fail)

    with pytest.raises(RuntimeError, match="download failed"):
        future.result(timeout=2)
