import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_config():
    load_dotenv(PROJECT_ROOT / ".env")

    download_folder = Path(os.getenv("DOWNLOAD_FOLDER", "downloads"))
    if not download_folder.is_absolute():
        download_folder = PROJECT_ROOT / download_folder

    return {
        "SECRET_KEY": os.getenv("SECRET_KEY") or None,
        "DOWNLOAD_FOLDER": str(download_folder),
    }
