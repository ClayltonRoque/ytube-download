from flask import Flask

from app.routes.downloads import bp as downloads_bp
from app.routes.main import bp as main_bp


def create_app():
    app = Flask(__name__)
    app.register_blueprint(main_bp)
    app.register_blueprint(downloads_bp)
    return app