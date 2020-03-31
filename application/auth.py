import os
import uuid
import functools

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
    current_app,
)
from werkzeug.security import check_password_hash, generate_password_hash

from application.db import get_db

bp = Blueprint("auth", __name__, url_prefix="/auth")


def get_activation_file():
    return os.path.join(
        current_app.root_path, "storage", current_app.config["ACTIVATION_FILE"]
    )


@bp.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        username = request.form["username"]
        db = get_db()
        error = None

        if not username:
            error = "Username is required."
        elif (
                db.execute("SELECT id FROM user WHERE username = ?", (username,)).fetchone()
                is not None
        ):
            error = "User {} is already registered.".format(username)

        if error is None:
            password = uuid.uuid4().hex
            db.execute(
                "INSERT INTO user (username, password) VALUES (?, ?)",
                (username, generate_password_hash(password)),
            )
            db.commit()
            activation_file = get_activation_file()
            open(activation_file, "w").write(uuid.uuid4().hex)
            return redirect(url_for("auth.activate", username=username))

        flash(error)

    return render_template("auth/register.html")


@bp.route("/activate/<username>", methods=("GET", "POST"))
def activate(username):
    if request.method == "POST":
        activation_code = request.form["activation"]
        activation_file = get_activation_file()
        error = None

        if not activation_code:
            error = "Activation code is required."
        elif not os.path.exists(activation_file) or open(activation_file, 'r').read() != activation_code:
            error = "Invalid activation code."
        else:
            db = get_db()
            db.execute("UPDATE user SET is_registered = ? WHERE username = ?", (True, username))
            db.commit()
            return "Activation successful"

        flash(error)

    return render_template("auth/activate.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        username = request.form["username"] @ bp.before_app_request
        password = request.form["password"]
        db = get_db()
        error = None
        user = db.execute(
            "SELECT * FROM user WHERE username = ?", (username,)
        ).fetchone()

        if user is None:
            error = "Incorrect username."
        elif not check_password_hash(user["password"], password):
            error = "Incorrect password."

        if error is None:
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("index"))

        flash(error)

    return render_template("auth/login.html")


def load_logged_in_user():
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
    else:
        g.user = (
            get_db().execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()
        )


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
    else:
        g.user = (
            get_db().execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()
        )


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))

        return view(**kwargs)

    return wrapped_view
