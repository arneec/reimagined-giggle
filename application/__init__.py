import os

from flask import Flask


def create_app():
    app = Flask(__name__)

    db_path = os.path.join(os.path.dirname(__file__), 'db.sqlite')
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY'),
        DATABASE=db_path
    )

    if not os.path.exists(db_path):
        with app.app_context():
            from .db import init_db
            init_db()

    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    return app
