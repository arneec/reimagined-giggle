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


def is_game_alive(date_time: str) -> bool:
    now = datetime.datetime.now()
    return datetime.datetime.strptime(date_time, current_app.config['DATETIME_FORMAT']) + datetime.timedelta(
        minutes=30) > now


@bp.route("/<quiz_id>/question", methods=("GET", "POST"))
@login_required
def question(quiz_id):
    """
        - check if quiz_id for the current user exists or not

        - if quiz_id exists and is locked or is expired return the quiz summary

        - Assumptions:
            - question number increment and previous question number lock happens in same transaction in atomic state
            - last question number (10) lock and quiz lock happens in same transaction in atomic state
    """
    db = get_db()
    quiz_state = db.execute("SELECT * FROM quiz_state WHERE id = ? AND user_id = ?",
                            (quiz_id, g.user['id'])).fetchone()

    if quiz_state is None:
        return render_template('404.html'), 404

    if quiz_state['locked']:
        # get game summary and return
        return render_template('404.html'), 404

    if not is_game_alive(quiz_state['created_at']):
        db.execute("UPDATE quiz_state SET locked = 1 WHERE id = ? AND locked = 0", (quiz_id,))
        # get game summary and return
        return render_template('404.html'), 404

    context = {'question': None}
    ques = db.execute("SELECT * FROM quiz_question WHERE quiz_id = ? AND locked = 0", (quiz_id,)).fetchone()
    if ques is None:
        # generate question
        # start with question 1
        pass
    else:
        context['question'] = ques

    return render_template('quiz/question.html', context=context)


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
        if is_game_alive(quiz_states[-1]['created_at']):
            return redirect(url_for('quiz.question', quiz_id=quiz_states[-1]['id']))

        else:
            db.execute("UPDATE quiz_state SET locked = 1 WHERE user_id = ? AND locked = 0", (g.user['id'],))

    cursor = db.execute(
        "INSERT INTO quiz_state (user_id, created_at) VALUES (?, ?)",
        (g.user['id'], datetime.datetime.now().strftime(current_app.config['DATETIME_FORMAT']))
    )
    db.commit()

    return redirect(url_for('quiz.question', quiz_id=cursor.lastrowid))
