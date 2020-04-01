import json
import re
import logging
from collections import OrderedDict
from pprint import pprint

import click
import requests
import functools

from bs4 import BeautifulSoup

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
        'name': data['name'],
        'description': data['description'],
        'rating': data['aggregateRating']['ratingValue'],
        'released_date': data['datePublished'],
        'movie_details': {('genre', i) for i in data['genre']} if isinstance(data['genre'], list) else {
            ('genre', data['genre'])
        }
    }

    for d in ('actor', 'director', 'creator'):
        if isinstance(data[d], list):
            movie_data['movie_details'] |= {(d, i['name']) for i in data[d] if i.get('name', False)}
        else:
            movie_data['movie_details'] |= {(d, data[d]['name'])}

    return movie_data


@click.command("scrape-movie")
@click.argument("link")
def scrape_movie_command(link):
    """
        $ flask scrape-movie <link>

        eg.
        $ flask scrape-movie 'title/tt2398149/?ref_=ttls_li_tt'

    """
    movie_data = scrape_movie_data(link)
    pprint(movie_data)
