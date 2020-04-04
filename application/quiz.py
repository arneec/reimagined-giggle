import random
import datetime

from functools import partial
from collections import namedtuple
from flask import (
    url_for,
    Blueprint,
    render_template,
    g,
    current_app,
    request, flash)
from werkzeug.utils import redirect

from application import get_db
from application.auth import login_required
from application.helpers import render_404

bp = Blueprint("quiz", __name__, url_prefix="/quiz")


def is_game_alive(date_time: str) -> bool:
    now = datetime.datetime.now()
    return datetime.datetime.strptime(date_time, current_app.config['DATETIME_FORMAT']) + datetime.timedelta(
        seconds=current_app.config['QUIZ_TIMEOUT_SECONDS']) > now


def rating_options(rating: str, num: int = 3):
    """

        rating: answer rating passed to avoid duplication of correct answer
        num: number of random options to return
    """
    options = []
    while True:
        r = '%.1f' % (random.uniform(0.5, 0.94) * 10)
        if r not in options and r != rating:
            options.append(r)
        if len(options) == num:
            break
    return options


def general_field_options(field: str, value: str, num: int = 3):
    db = get_db()
    rows = db.execute(F"SELECT DISTINCT {field} FROM movie WHERE {field} != ? ORDER BY RANDOM()",
                      (value,)).fetchall()
    options = [rows[i][field] for i in range(num)]
    return options


def randomly_group_items(items, answers, tot_grps=3, max_per_grp=3):
    assert tot_grps * max_per_grp <= len(items)
    groups = []
    indx = 0
    while len(groups) != tot_grps:
        pick_no_items = random.randint(1, max_per_grp)
        groups.append(items[indx: indx + pick_no_items])
        indx += pick_no_items

    return groups


def movie_detail_options(field, *answers: str):
    db = get_db()
    placeholders = ", ".join("?" * len(answers))
    movie_details = db.execute(
        F"SELECT DISTINCT value FROM movie_detail WHERE key = ? AND value NOT IN ({placeholders})",
        (field, *answers)).fetchall()
    items = [i['value'] for i in movie_details]
    return randomly_group_items(items, answers, tot_grps=3, max_per_grp=3)


QuestionTemplate = namedtuple('QuestionTemplate', ('question_template', 'field', 'table', 'get_option'))

QUESTION_TEMPLATES = (
    QuestionTemplate(
        question_template='What is the rating of the movie {name} ?',
        field='rating',
        table='movie',
        get_option=rating_options
    ),
    QuestionTemplate(
        question_template='When was the movie {name} released ?',
        field='released_date',
        table='movie',
        get_option=partial(general_field_options, 'released_date')
    ),
    QuestionTemplate(
        question_template='What best describes the movie {name} ?',
        field='description',
        table='movie',
        get_option=partial(general_field_options, 'description')
    ),
    QuestionTemplate(
        question_template='Who {verb} the director(s) of the movie {name} ?',
        field='director',
        table='movie_detail',
        get_option=partial(movie_detail_options, 'director')
    ),
    QuestionTemplate(
        question_template='What genre(s) does the movie {name} belongs to ?',
        field='genre',
        table='movie_detail',
        get_option=partial(movie_detail_options, 'genre')
    ),
    QuestionTemplate(
        question_template='Who wrote the movie {name} ?',
        field='creator',
        table='movie_detail',
        get_option=partial(movie_detail_options, 'creator')
    ),
    QuestionTemplate(
        question_template='Who {verb} the actor(s) of the movie {name} ?',
        field='actor',
        table='movie_detail',
        get_option=partial(movie_detail_options, 'actor')
    ),
)


def filtered_question_templates(*excludes):
    if excludes:
        return tuple(filter(lambda x: x.field not in excludes, QUESTION_TEMPLATES))
    return QUESTION_TEMPLATES


def _generate_random_question(db, quiz_id, question_no):
    """
        - from same movie only allow 3 questions at max.
    """
    movie = db.execute("SELECT * FROM movie ORDER BY RANDOM()").fetchone()
    if question_no > 1:
        exclude_fields = [i['field'] for i in
                          db.execute("SELECT field FROM quiz_question WHERE quiz_id = ? AND movie_id = ?",
                                     (quiz_id, movie['id'])).fetchall()]
        question_templates = filtered_question_templates(*exclude_fields)
    else:
        question_templates = filtered_question_templates()
    random_no = random.randint(0, len(question_templates) - 1)
    template = question_templates[random_no]
    if template.table == 'movie_detail':
        movie_details = db.execute('''SELECT * FROM movie INNER JOIN movie_detail
                                      ON movie.id = movie_detail.movie_id
                                      WHERE movie.id = ? AND movie_detail.key = ?''',
                                   (movie['id'], template.field)).fetchall()
        answer = [i['value'] for i in movie_details]
        options = template.get_option(*answer)
        answer = ', '.join(answer)
    else:
        answer = movie[template.field]
        options = template.get_option(answer)
    question = template.question_template.format(**movie, verb='are')
    now = datetime.datetime.now().strftime(current_app.config['DATETIME_FORMAT'])
    quiz_question = db.execute(
        "INSERT INTO quiz_question (quiz_id, movie_id, field, question_no, question, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (quiz_id, movie['id'], template.field, question_no, question, now))
    db.execute("INSERT INTO question_option (question_id, option, is_correct) VALUES (?, ?, ?)",
               (quiz_question.lastrowid, answer, 1))
    db.executemany("INSERT INTO question_option (question_id, option) VALUES (?, ?)",
                   [(quiz_question.lastrowid, ', '.join(opt) if isinstance(opt, list) else opt) for opt in options])
    return quiz_question.lastrowid


@bp.route("/<quiz_id>/score", methods=("GET", "POST"))
@login_required
def score(quiz_id):
    db = get_db()
    quiz_state = db.execute("SELECT * FROM quiz_state WHERE id = ? AND user_id = ? AND locked = 1",
                            (quiz_id, g.user['id'])).fetchone()
    if quiz_state is None:
        return render_404()

    quiz_log = db.execute(
        "SELECT quiz_question.question_no, quiz_question.question, question_option.option, question_option.is_correct "
        "FROM quiz_state "
        "INNER JOIN quiz_question on quiz_state.id=quiz_question.quiz_id "
        "LEFT OUTER JOIN question_option on quiz_question.user_answer = question_option.id "
        "WHERE quiz_state.id = ? ORDER BY quiz_question.question_no",
        (quiz_id,)).fetchall()

    score = str(sum(i['is_correct'] for i in quiz_log if i['is_correct']))
    return render_template('quiz/score.html', quiz_log=quiz_log, score=score)


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

    def _get_context(question_id):
        db = get_db()
        quiz_ques_options = db.execute("SELECT quiz_question.id AS qid, "
                                       "question_option.id AS option_id, "
                                       "quiz_question.question, "
                                       "quiz_question.question_no, "
                                       "question_option.option "
                                       "FROM quiz_question "
                                       "INNER JOIN question_option "
                                       "ON qid = question_option.question_id "
                                       "WHERE qid = ?",
                                       (question_id,)).fetchall()
        context = {'question_no': quiz_ques_options[0]['question_no'], 'question': quiz_ques_options[0]['question'],
                   'options': [(i['option_id'], i['option']) for i in quiz_ques_options]}

        return context

    def _quiz_complete_action(db):
        db.execute("UPDATE quiz_state SET locked = 1 WHERE id = ?", (quiz_id,))
        db.commit()
        return redirect(url_for('quiz.score', quiz_id=quiz_id))

    def get():
        db = get_db()
        quiz_state = db.execute("SELECT * FROM quiz_state WHERE id = ? AND user_id = ?",
                                (quiz_id, g.user['id'])).fetchone()

        if quiz_state is None:
            return render_template('404.html'), 404

        if quiz_state['locked']:
            flash('Quiz complete.', category='info')
            return redirect(url_for('quiz.score', quiz_id=quiz_id))

        if not is_game_alive(quiz_state['created_at']):
            db.execute("UPDATE quiz_state SET locked = 1 WHERE id = ? AND locked = 0", (quiz_id,))
            flash('Quiz expired.', category='warning')
            return redirect(url_for('quiz.score', quiz_id=quiz_id))

        quiz_ques = db.execute("SELECT * FROM quiz_question WHERE quiz_id = ? AND locked = 0 ORDER BY id DESC",
                               (quiz_id,)).fetchone()
        now = datetime.datetime.now()
        if quiz_ques is None:
            question_id = _generate_random_question(db=db, quiz_id=quiz_id, question_no=1)
            db.commit()

        elif datetime.datetime.strptime(quiz_ques['created_at'],
                                        current_app.config['DATETIME_FORMAT']) + datetime.timedelta(
            seconds=current_app.config['QUESTION_TIMEOUT_SECONDS']) <= now:
            if quiz_ques['question_no'] >= 10:
                return _quiz_complete_action(db)

            flash('Question #%s expired' % quiz_ques['question_no'], category='warning')
            db.execute("UPDATE quiz_question SET locked = 1 WHERE quiz_id = ? AND locked = 0", (quiz_id,))
            question_id = _generate_random_question(db=db, quiz_id=quiz_id, question_no=quiz_ques['question_no'] + 1)
            db.commit()

        else:
            question_id = quiz_ques['id']

        context = _get_context(question_id)
        return render_template('quiz/question.html', **context), 200

    def post():
        db = get_db()
        answer = request.form.get('answer', None)
        quiz_ques = db.execute("SELECT * FROM quiz_question WHERE quiz_id = ? AND locked = 0 ORDER BY id DESC",
                               (quiz_id,)).fetchone()
        now = datetime.datetime.now()
        if quiz_ques is None:
            return render_404()
        elif datetime.datetime.strptime(
                quiz_ques['created_at'],
                current_app.config['DATETIME_FORMAT']) + datetime.timedelta(
            seconds=current_app.config['QUESTION_TIMEOUT_SECONDS']) <= now:
            db.execute("UPDATE quiz_question SET locked = 1 WHERE quiz_id = ? AND locked = 0", (quiz_id,))

            flash("Question expired.", category='warning')
            return redirect(url_for('quiz.question', quiz_id=quiz_id))

        else:
            question_id = quiz_ques['id']

        if answer is not None:
            correct_option = db.execute("SELECT question_option.id AS option_id FROM quiz_question "
                                        "INNER JOIN question_option "
                                        "ON quiz_question.id = question_option.question_id "
                                        "WHERE quiz_question.id = ? AND is_correct = 1",
                                        (question_id,)).fetchone()
            if str(correct_option['option_id']) == answer:
                flash("Correct answer", category='success')
            else:
                flash("Wrong answer", category='danger')
        else:
            flash("Skipped question #%s" % quiz_ques['question_no'], category='warning')

        db.execute("UPDATE quiz_question SET user_answer = ?, locked = 1 WHERE id = ?", (answer, question_id))
        if quiz_ques['question_no'] >= 10:
            flash('Quiz complete', category='info')
            return _quiz_complete_action(db=db)

        question_id = _generate_random_question(db=db, quiz_id=quiz_id, question_no=quiz_ques['question_no'] + 1)
        db.commit()

        context = _get_context(question_id)
        return render_template('quiz/question.html', **context), 200

    if request.method == 'GET':
        return get()
    else:
        return post()


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
            flash("You have incomplete quiz", category='info')
            return redirect(url_for('quiz.question', quiz_id=quiz_states[-1]['id']))

        else:
            db.execute("UPDATE quiz_state SET locked = 1 WHERE user_id = ? AND locked = 0", (g.user['id'],))

    cursor = db.execute(
        "INSERT INTO quiz_state (user_id, created_at) VALUES (?, ?)",
        (g.user['id'], datetime.datetime.now().strftime(current_app.config['DATETIME_FORMAT']))
    )
    db.commit()

    return redirect(url_for('quiz.question', quiz_id=cursor.lastrowid))
