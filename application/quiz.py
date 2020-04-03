import random
import datetime

from collections import namedtuple
from functools import partial

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


def rating_options(rating: str, num: int = 3):
    """
        rating: answer rating passed to avoid duplication of correct answer
        num: number of random options to return
    """
    options = []
    while True:
        r = '%.1f' % (random.uniform(0.5, 0.94) * 10)
        if r != rating:
            options.append(r)
        if len(options) == num:
            break
    return options


def released_date_options(released_date: str, num: int = 3):
    db = get_db()
    released_dates = db.execute(
        F"SELECT released_date FROM movie WHERE released_date != ? RANDOM LIMIT {num}", (released_date,)).fetchall()
    return [i['released_date'] for i in released_dates]


def randomly_group_items(items, answers, tot_grps=3, max_per_grp=3):
    assert tot_grps * max_per_grp <= len(items)
    groups = []
    indx = 0
    while True:
        pick_no_items = random.randint(1, max_per_grp)
        group = items[indx:pick_no_items]
        if group not in groups and group != answers:
            groups.append(items[indx:pick_no_items])
            if len(groups) == tot_grps:
                break
        indx += pick_no_items

    return groups


def movie_detail_options(field, *answers: str):
    db = get_db()
    items = db.execute("SELECT * FROM movie_detail WHERE key = ?", (field,)).fetchall()
    return randomly_group_items(items, answers, tot_grps=3, max_per_grp=1)


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
        get_option=rating_options
    ),
    QuestionTemplate(
        question_template='What best describes the movie {name} ?',
        field='description',
        table='movie',
        get_option=rating_options
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
        question_template='Who wrote the movie {name}?',
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

FILTERED_QUESTION_TEMPLATES = lambda *exclude: tuple(filter(lambda x: x.field not in exclude, QUESTION_TEMPLATES))


def generate_random_question(quiz_id, question_no):
    """
        - from same movie only allow 3 questions at max.
    """
    db = get_db()
    movie = db.execute("SELECT * FROM movie RANDOM").fetchone()
    if question_no > 1:
        exclude_fields = [i['fields'] for i in
                          db.execute("SELECT field FROM quiz_questions WHERE quiz_id = ? AND movie_id = ?",
                                     (quiz_id, movie['id'])).fetchall()]
        question_templates = FILTERED_QUESTION_TEMPLATES(*exclude_fields)
    else:
        question_templates = FILTERED_QUESTION_TEMPLATES()
    random_no = random.randint(0, len(question_templates) - 1)
    template = question_templates[random_no]
    if template.table == 'movie_detail':
        movie_details = db.execute(F'''SELECT * FROM movie
                                       INNER JOIN movie_detail
                                       WHERE movie_id = ? AND key = ?''', (movie['id'], template.field,)).fetchall()
        answers = [i['value'] for i in movie_details]
    else:
        answers = [movie[template.field]]
    ques = template.question_template.format(**movie, verb='are')
    return ques, answers


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
        ques = generate_random_question(quiz_id=quiz_id, question_no=1)
        context['question_no'] = 1
        context['question'] = ques
        # generate question
        pass
    else:
        context['question_no'] = ques['question_no']
        context['question'] = ques['question']

    return render_template('quiz/question.html', **context)


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
