from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable, ParamSpec, TypeVar


_DOWNLOAD_EXECUTOR = ThreadPoolExecutor(
    max_workers=2,
    thread_name_prefix="media-download",
)

Parameters = ParamSpec("Parameters")
Result = TypeVar("Result")


def submit_download(
    function: Callable[Parameters, Result],
    /,
    *args: Parameters.args,
    **kwargs: Parameters.kwargs,
) -> Future[Result]:
    return _DOWNLOAD_EXECUTOR.submit(function, *args, **kwargs)
