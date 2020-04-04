## Running the application

### Installing the required packages

```$ pip install -r requirements.txt```


### Initializing the db

```$ flask init-db```

### Configuring the application

copy .env.sample to .env file

```$ cp .env.sample .env```

change configuration inside .env file

then run the application

```$ flask run```


### Application logs
application logs are configured to be stored in app.logs file in root project directory

### Populating the database for quick first run
scraping home page of imdb and populating the database for crawled movie links

```$ flask scrape-home-movies --populate```

scraping specified link of the imdb site and populating the database for crawled movie links

_eg. populate db with some popular movies_

```$ flask scrape-home-movies --link '/search/title/?groups=top_250&sort=user_rating' --populate```


scraping specified imdb movie link and populating the database

_eg. populate db with some popular movies_

```$ flask scrape-movie 'title/tt2398149/?ref_=ttls_li_tt' --populate```


###Database and tables
tables definitions for the database are in ```/appliation/schema.sql```


### User register and login
register user @ ```/auth/register``` url with username and password ( a new activation code generated at location ```application/storage/activation-code.txt``` file )

enter the activation code on ```/auth/activate/<username>``` to activate the user with given username in the url

once activated user can get access to the system through login @ ```/auth/login```

