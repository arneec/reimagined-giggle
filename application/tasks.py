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
MOVIE_URL_REGEX = r'title/.{5,15}$'


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
def _populate_movie(movie_data):
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


def _scrape_movies_list(link='/'):
    """
        link: default to IMDB home page url
    """
    response = get_response('%s%s' % (IMDB_URL, link))
    soup = BeautifulSoup(response.text, features='html.parser')
    movies = soup.find_all('a', {'href': re.compile(MOVIE_URL_REGEX)})
    return [i.get('href') for i in movies]


@exception_handler
def _scrape_movie_data(link):
    response = get_response(r'%s/%s' % (IMDB_URL, link))
    soup = BeautifulSoup(response.text, features='html.parser')
    soup = soup.find('script', {'type': 'application/ld+json'})
    assert soup is not None, "Failed to scrap %s" % link
    data = json.loads(soup.text)
    if data['@type'] != 'Movie':
        pprint("Skipping %s as it is not a movie." % link)
        return None
    description = re.sub(data['name'], '', data['description'], flags=re.I)
    movie_data = {
        'general': {
            'name': data['name'],
            'description': description,
            'rating': '%.1f' % float(data['aggregateRating']['ratingValue']),
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
@click.option('--populate', is_flag=True)
@with_appcontext
def scrape_movie_command(link, populate):
    """
        scrapes & displays the movie data for given movie link.
        **check example below for movie link(url) format to pass on**

        $ flask scrape-movie <link>

        eg.
        $ flask scrape-movie 'title/tt2398149/?ref_=ttls_li_tt'

        _To populate db add --populate flag_
        $ flask scrape-movie 'title/tt2398149/?ref_=ttls_li_tt' --populate

    """
    movie_data = _scrape_movie_data(link)
    if populate and movie_data is not None:
        _populate_movie(movie_data)
    pprint(movie_data)


@click.command("scrape-home-movies")
@click.option('--link', default=None, help='IMDB link to crawl and scrape movies list from')
@click.option('--populate', is_flag=True)
@with_appcontext
def scrape_home_movies_command(link, populate):
    """
        crawl movie links and scrape those movies data

        _To populate db with some popular movies_
        $ flask scrape-home-movies --link '/search/title/?groups=top_250&sort=user_rating' --populate
    """
    if link is None:
        links = _scrape_movies_list()
    else:
        links = _scrape_movies_list(link)
    for _ in links:
        print("\nScrapping %s" % _)
        movie_data = _scrape_movie_data(_)
        if populate and movie_data is not None:
            _populate_movie(movie_data)
        pprint(movie_data)
