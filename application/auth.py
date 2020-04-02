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
        password = request.form["password"]
        db = get_db()
        error = None

        if not username:
            error = "Username is required."
        elif not password:
            error = "Password is required."
        elif len(password) < 6:
            error = "Password length should be > 6."
        elif (
                db.execute("SELECT id FROM user WHERE username = ?", (username,)).fetchone()
                is not None
        ):
            error = "User {} is already registered.".format(username)

        if error is None:
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
            return redirect(url_for("auth.login"))

        flash(error)

    return render_template("auth/activate.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if g.user is not None:
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form["username"]
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
            return redirect(url_for("home"))

        flash(error)

    return render_template("auth/login.html")


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))

        return view(**kwargs)

    return wrapped_view
