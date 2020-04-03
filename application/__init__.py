import os

from flask import Flask, render_template, session, g

from application.db import get_db
from application.auth import login_required
from application.tasks import scrape_movie_command, scrape_home_movies_command


def create_app():
    app = Flask(__name__)

    db_path = os.path.join(os.path.dirname(__file__), "db.sqlite")
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        DATABASE=db_path,
        ACTIVATION_FILE=os.environ.get("ACTIVATION_FILE"),
        DATETIME_FORMAT=os.environ.get("DATETIME_FORMAT")
    )

    from . import db
    db.init_app(app)

    from . import auth, quiz
    app.register_blueprint(auth.bp)
    app.register_blueprint(quiz.bp)

    app.cli.add_command(scrape_movie_command)
    app.cli.add_command(scrape_home_movies_command)

    @app.before_request
    def load_logged_in_user():
        user_id = session.get("user_id")

        if user_id is None:
            g.user = None
        else:
            g.user = (
                get_db().execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()
            )

    @app.route('/home', methods=("GET",))
    @login_required
    def home():
        return render_template("home.html")

    return app
