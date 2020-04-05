from application import get_db


def test_home(client, auth):
    auth.check_login_required()

    response = client.get('/')
    assert b'Leaderboard' in response.data
    assert b'Take the movie quiz' in response.data


def test_quiz_create(client, auth):
    auth.check_login_required()

    response = client.get('/quiz/create')
    assert response.headers['Location'] == 'http://localhost/quiz/1/question'


def test_quiz_create_empty(client, auth, app):
    auth.check_login_required()

    with app.app_context():
        get_db().execute("DELETE FROM movie_detail")
        get_db().execute("DELETE FROM movie")
        get_db().commit()

    response = client.get('/quiz/create')
    assert b'Not enough questions in the database. Game could not be loaded.' in response.data


def test_quiz_question(client, auth, app):
    auth.check_login_required()

    client.get('/quiz/create')
    response = client.get('/quiz/1/question')
    assert b'Question #1' in response.data


def test_quiz_question_correct_answer(client, auth, app):
    auth.check_login_required()

    client.get('/quiz/create')
    client.get('/quiz/1/question')
    with app.app_context():
        cor_ans_id = \
            get_db().execute("SELECT id FROM question_option WHERE question_id = 1 AND is_correct = 1").fetchone()['id']
    response = client.post('/quiz/1/question', data={'answer': cor_ans_id})
    assert b'Correct answer' in response.data


def test_quiz_question_incorrect_answer(client, auth, app):
    auth.check_login_required()

    client.get('/quiz/create')
    client.get('/quiz/1/question')
    with app.app_context():
        cor_ans_id = \
            get_db().execute("SELECT id FROM question_option WHERE question_id = 1 AND is_correct = 0").fetchone()['id']
    response = client.post('/quiz/1/question', data={'answer': cor_ans_id})
    assert b'Wrong answer' in response.data
