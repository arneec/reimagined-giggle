from flask import session, g

from application import get_db


def test_register(client, app):
    assert client.get('/auth/register').status_code == 200
    response = client.post(
        '/auth/register', data={'username': 'a', 'password': 'abcdef'}
    )
    assert 'http://localhost/auth/activate/a' == response.headers['Location']

    with app.app_context():
        assert get_db().execute(
            "select * from user where username = 'a'",
        ).fetchone() is not None


def test_login(client, auth):
    assert client.get('/auth/login').status_code == 200
    response = auth.login()
    assert response.headers['Location'] == 'http://localhost/'

    with client:
        client.get('/')
        assert session['user_id'] == 1
        assert g.user['username'] == 'test'


def test_login_inactivated(client, auth):
    assert client.get('/auth/login').status_code == 200
    response = auth.login(username='other', password='test')

    with client:
        client.get('/')
        assert 'user_id' not in session


def test_logout(client, auth):
    auth.login()

    with client:
        auth.logout()
        assert 'user_id' not in session


def test_activate(client, auth):
    assert client.get('/auth/activate').status_code == 200
    response = auth.activate(username='other')
    assert response.headers['Location'] == 'http://localhost/auth/activate/other'


def test_activate_username(client, auth, app):
    assert client.get('/auth/activate/other').status_code == 200

    response = auth.activate_username()
    assert response.headers['Location'] == 'http://localhost/auth/login'

    with app.app_context():
        assert get_db().execute(
            "select * from user where username = 'other'",
        ).fetchone()['is_activated']
