import os

from flask import Flask, render_template

from application.tasks import scrape_movie_data_command, scrape_populate_movie_command


def create_app():
    app = Flask(__name__)

    db_path = os.path.join(os.path.dirname(__file__), "db.sqlite")
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        DATABASE=db_path,
        ACTIVATION_FILE=os.environ.get("ACTIVATION_FILE"),
    )

    from . import db
    db.init_app(app)

    from . import auth
    app.register_blueprint(auth.bp)

    app.cli.add_command(scrape_movie_data_command)
    app.cli.add_command(scrape_populate_movie_command)

    @app.route('/home', methods=("GET",))
    def home():
        return render_template("home.html")

    return app
