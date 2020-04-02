import re
import json
import click
import logging
import requests
import functools

from pprint import pprint
from bs4 import BeautifulSoup
from flask.cli import with_appcontext

from application.db import get_db

logger = logging.getLogger(__name__)
logging.basicConfig()

IMDB_URL = r'https://www.imdb.com'
MOVIE_URL_REGEX = r'title/.{5,15}/?ref_=.+$'


def exception_handler(f):
    functools.wraps(f)

    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as err:
            logger.exception("Exception raised. Error: %s." % err)
        return None

    return wrapper


def get_response(url, method='get'):
    try:
        if method == 'get':
            response = requests.get(url)
        elif method == 'post':
            response = requests.post(url)
        else:
            raise Exception("Method %s not allowed." % method)
        response.raise_for_status()
    except Exception as err:
        raise Exception("Error connecting %s url" % url)
    return response


@exception_handler
def scrape_movies_list():
    response = get_response(IMDB_URL)
    soup = BeautifulSoup(response.text, features='html.parser')
    movies = soup.find_all('a', {'href': re.compile(MOVIE_URL_REGEX)})
    return [i.get('href') for i in movies]


@exception_handler
def scrape_movie_data(link):
    response = get_response(r'%s/%s' % (IMDB_URL, link))
    soup = BeautifulSoup(response.text, features='html.parser')
    soup = soup.find('script', {'type': 'application/ld+json'})
    assert soup is not None, "Failed to scrap %s" % link
    data = json.loads(soup.text)
    movie_data = {
        'general': {
            'name': data['name'],
            'description': data['description'],
            'rating': data['aggregateRating']['ratingValue'],
            'released_date': data['datePublished'],
        },
        'movie_detail': [('genre', i) for i in data['genre']] if isinstance(data['genre'], list) else [
            ('genre', data['genre'])
        ]
    }

    for d in ('actor', 'director', 'creator'):
        if isinstance(data[d], list):
            movie_data['movie_detail'] += [(d, i['name']) for i in data[d] if i.get('name', False)]
        else:
            movie_data['movie_detail'].append((d, data[d]['name']))

    movie_data['movie_detail'] = sorted(set(movie_data['movie_detail']), key=lambda x: x[0])

    return movie_data


@click.command("scrape-movie")
@click.argument("link")
def scrape_movie_data_command(link):
    """
        scrapes & displays the movie data for given movie link.
        **check example below for movie link(url) format to pass on**

        $ flask scrape-movie <link>

        eg.
        $ flask scrape-movie 'title/tt2398149/?ref_=ttls_li_tt'

    """
    movie_data = scrape_movie_data(link)
    pprint(movie_data)


@click.command("scrape-populate-movie")
@click.argument("link")
@with_appcontext
def scrape_populate_movie_command(link):
    """
        scrapes & populates the database for given movie link
        **check example below for movie link(url) format to pass on**

        $ flask scrape-populate-movie <link>

        eg.
        $ flask scrape-populate-movie 'title/tt2398149/?ref_=ttls_li_tt'

    """
    movie_data = scrape_movie_data(link)
    db = get_db()
    cursor = db.execute(
        "INSERT INTO movie (name, description, rating, released_date) VALUES (?, ?, ?, ?)",
        (movie_data['general']['name'], movie_data['general']['description'], movie_data['general']['rating'],
         movie_data['general']['released_date'])
    )
    movie_id = cursor.lastrowid
    db.executemany(
        "INSERT INTO movie_detail (movie_id, key, value) VALUES (?, ?, ?)",
        [(movie_id, *key_value) for key_value in movie_data['movie_detail']]
    )
    db.commit()
    pprint(movie_data)
