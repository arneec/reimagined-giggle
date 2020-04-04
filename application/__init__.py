import os

from logging.config import dictConfig
from flask import Flask, render_template, session, g

from application.db import get_db
from application.auth import login_required
from application.tasks import scrape_movie_command, scrape_home_movies_command

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s: %(message)s',
    }},
    'handlers': {'file': {
        'class': 'logging.FileHandler',
        'filename': 'app.logs',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['file']
    }
})


def create_app():
    app = Flask(__name__)

    db_path = os.path.join(os.path.dirname(__file__), "db.sqlite")
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        DATABASE=db_path,
        ACTIVATION_FILE=os.environ.get("ACTIVATION_FILE"),
        DATETIME_FORMAT=os.environ.get("DATETIME_FORMAT"),
        QUESTION_TIMEOUT_SECONDS=int(os.environ.get("QUESTION_TIMEOUT_SECONDS")),
        QUIZ_TIMEOUT_SECONDS=int(os.environ.get("QUIZ_TIMEOUT_SECONDS")),
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

    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.exception(e)
        return '<h1>Some error occurred in the server.</h1><p>Please REFRESH to continue.</p>'

    @app.route('/', methods=("GET",))
    @login_required
    def home():
        db = get_db()
        leaderboards = db.execute(
            "SELECT user.username, quiz_state.id as quiz_id, COUNT(question_option.id) AS score "
            "FROM user "
            "INNER JOIN quiz_state on user.id=quiz_state.user_id "
            "INNER JOIN quiz_question on quiz_state.id=quiz_question.quiz_id "
            "INNER JOIN question_option on quiz_question.user_answer = question_option.id "
            "WHERE quiz_state.locked = 1 AND question_option.is_correct = 1 "
            "GROUP BY user.id, quiz_state.id "
            "ORDER BY score DESC "
            "LIMIT 10").fetchall()

        return render_template("home.html", leaderboards=leaderboards)

    return app
