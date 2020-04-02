import datetime

from flask import (
    url_for,
    Blueprint,
    render_template,
    g,
    current_app
)
from werkzeug.utils import redirect

from application import get_db
from application.auth import login_required

bp = Blueprint("quiz", __name__, url_prefix="/quiz")


@bp.route("/<quiz_id>/question", methods=("GET", "POST"))
@login_required
def question(quiz_id):
    return render_template('quiz/question.html')


@bp.route("/create", methods=("GET",))
@login_required
def create_quiz():
    """
        - create a quiz game if no any game is alive else return the alive quiz game

        - lock all the unlocked games if new game is being created
    """
    db = get_db()
    quiz_states = db.execute("SELECT * FROM quiz_state WHERE user_id = ? AND locked = 0", (g.user['id'],)).fetchall()
    if quiz_states:
        now = datetime.datetime.now()
        game_alive = datetime.datetime.strptime(
            quiz_states[-1]['created_at'], current_app.config['DATETIME_FORMAT']) + datetime.timedelta(minutes=10) > now

        if game_alive:
            return redirect(url_for('quiz.question', quiz_id=quiz_states[-1]['id']))

        else:
            db.execute("UPDATE quiz_state SET locked = 1 WHERE user_id = ? AND locked = 0", (g.user['id'],)).fetchall()

    cursor = db.execute(
        "INSERT INTO quiz_state (user_id, created_at) VALUES (?, ?)",
        (g.user['id'], datetime.datetime.now().strftime(current_app.config['DATETIME_FORMAT']))
    )
    db.commit()

    return redirect(url_for('quiz.question', quiz_id=cursor.lastrowid))
