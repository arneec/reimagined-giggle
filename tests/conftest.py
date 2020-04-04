import os
import pytest
import tempfile

from application import create_app
from application.db import get_db, init_db

with open(os.path.join(os.path.dirname(__file__), 'data.sql'), 'rb') as f:
    _data_sql = f.read().decode('utf8')


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()

    app = create_app({
        'TESTING': True,
        'DATABASE': db_path,
        'SECRET_KEY': 'test1234',
        'ACTIVATION_FILE': 'test_activation_code.txt',
        'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
        'QUESTION_TIMEOUT_SECONDS': 900,
        'QUIZ_TIMEOUT_SECONDS': 3600,
        'PAGE_SIZE': 5
    })

    with app.app_context():
        init_db()
        get_db().executescript(_data_sql)

    activation_file_path = 'application/storage/test_activation_code.txt'
    open(activation_file_path, 'w').write('testcode')

    yield app

    os.close(db_fd)
    os.unlink(db_path)
    if os.path.exists(activation_file_path):
        os.unlink(activation_file_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


class AuthActions(object):
    def __init__(self, client):
        self._client = client

    def login(self, username='test', password='test'):
        return self._client.post(
            '/auth/login',
            data={'username': username, 'password': password}
        )

    def logout(self):
        return self._client.get('/auth/logout')

    def activate(self, username='test'):
        return self._client.post(
            '/auth/activate',
            data={'username': username}
        )

    def activate_username(self, username='other'):
        return self._client.post(
            '/auth/activate/%s' % username,
            data={'activation': 'testcode'}
        )


@pytest.fixture
def auth(client):
    return AuthActions(client)
