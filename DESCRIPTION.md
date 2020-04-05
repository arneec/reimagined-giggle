## Movie Quiz

Movie Quiz is an quiz game where 10 random dynamically generated questions are asked to a user with some time constraints where each question carries 1 point on correctly answered and does not carries any negative marking.


### Technical approcah description


#### DB table & fields description

- user : to store users
    - username : username of user | unique
    - password : encrypted password
    - is_activated : flag to represent if user is activated (1) or not (0)

    > By default user is not activated. Activation code is under ``application/storage`` folder inside the file name defined in ``.env`` file's ``ACTIVATION_FILE`` variable.

- movie : to store movie general details
    - name : movie's name
    - description : movie's summary
    - released_date : movie's released date
    - rating : rating of movie in imdb

- movie_detail : to store movie's detail that has more than one value like actor(s), director(s), genre(s)
    - movie_id : FK to movie's id
    - key : name of the detail of the movie like ``actor/director/genre/creator``
    - value : the value of the detail described by the key field

- quiz_state : to store the state of quiz that was created
    - user_id : FK of user's id, who generated the quiz
    - locked : locked state of the quiz. when created is 0 and after completed or expired becomes 1. the quiz expiration time is fetched from ``.env`` file's ``QUIZ_TIMEOUT_SECONDS`` 's value in seconds.
    - created_at : the datetime of quiz creation format determined by ``DATETIME_FORMAT`` in ``.env`` file. it is used to check if quiz expired or not.


- quiz_question: represents each question asked in the quiz
    - field : the field of question asked. currently supported fields are ``description/released_date/rating/actor/director/genre/creator``
    - question_no : the number of question while it was asked in ``quiz_id``
    - question : the actual question text asked
    - user_answer : user's answer from option (id)
    - locked : to represent if question has expired or not. timeout is determine by ``QUESTION_TIMEOUT_SECONDS`` 's value in ``.env`` file.
    - created_at : to check if question expired.


- question_option : represents each option for question asked
    - question_id : the question to which this option belongs to
    - option : the option text given in the question
    - is_correct : flag to represent if this option is the correct one or not

