DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS movie;
DROP TABLE IF EXISTS movie_detail;
DROP TABLE IF EXISTS quiz_state;
DROP TABLE IF EXISTS quiz_question;
DROP TABLE IF EXISTS question_option;


CREATE TABLE user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  is_activated INTEGER NOT NULL DEFAULT 0
);


CREATE TABLE `movie` (
	`id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	`name`	TEXT UNIQUE NOT NULL,
	`description`	TEXT NOT NULL,
	`released_date` TEXT NOT NULL,
	`rating`    REAL NOT NULL
);


CREATE TABLE `movie_detail` (
	`id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	`movie_id`	INTEGER NOT NULL,
	`key`	TEXT NOT NULL,
	`value`	TEXT NOT NULL,
	FOREIGN KEY(`movie_id`) REFERENCES `movies`(`id`)
);


CREATE TABLE `quiz_state` (
    `id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	`user_id`	INTEGER NOT NULL,
	`locked` INTEGER NOT NULL DEFAULT 0,
	`created_at` TEXT NOT NULL,
	FOREIGN KEY(`user_id`) REFERENCES `user`(`id`)
);


CREATE TABLE `quiz_question` (
    `id` INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    `quiz_id` INTEGER NOT NULL,
    `movie_id` INTEGER NOT NULL,
    `field` TEXT NOT NULL,
    `question_no` INTEGER NOT NULL,
    `question` TEXT NOT NULL,
    `user_answer` TEXT,
    `locked` INTEGER NOT NULL DEFAULT 0,
    `created_at` TEXT NOT NULL,
    FOREIGN KEY(`quiz_id`) REFERENCES `quiz`(`id`),
    FOREIGN KEY(`movie_id`) REFERENCES `movie`(`id`),
    UNIQUE(`quiz_id`, `movie_id`, `field`)
);


CREATE TABLE `question_option` (
    `id` INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    `question_id` INTEGER NOT NULL,
    `option` TEXT NOT NULL,
    `is_correct` INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(`question_id`) REFERENCES `question`(`id`),
    UNIQUE(`question_id`, `option`)
);
