from flask import Flask

from app.config import load_config
from app.routes.downloads import bp as downloads_bp
from app.routes.main import bp as main_bp
from app.services.download_tasks import DownloadTaskManager


def create_app():
    app = Flask(__name__)
    app.config.from_mapping(load_config())
    app.extensions["download_task_manager"] = DownloadTaskManager()
    app.register_blueprint(main_bp)
    app.register_blueprint(downloads_bp)
    return app