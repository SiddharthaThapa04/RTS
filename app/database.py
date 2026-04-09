"""SQLite persistence layer for movie metadata."""

import sqlite3
from textwrap import dedent

from app.config import DB_PATH


class MovieDatabase:
    """Encapsulates all database interactions for the robot."""

    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path

    def init_db(self) -> None:
        """
        Initialize the local SQLite database.

        Creates the `movies` table if it does not already exist.
        The movie title is stored as the PRIMARY KEY to ensure uniqueness.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                dedent(
                    """
                    CREATE TABLE IF NOT EXISTS movies (
                        title             TEXT PRIMARY KEY,
                        year              INTEGER,
                        tomatometer       TEXT,
                        audience_score    TEXT,
                        storyline         TEXT,
                        genre             TEXT,
                        runtime           TEXT,
                        rating            TEXT,
                        release_date      TEXT,
                        critic_1          TEXT,
                        critic_2          TEXT,
                        critic_3          TEXT,
                        critic_4          TEXT,
                        critic_5          TEXT,
                        critic_6          TEXT
                    )
                    """
                )
            )
            conn.commit()

        print(f"[DB] Initialised at: {self.db_path}")

    def save_movie(self, data: dict) -> None:
        """
        Insert or replace a movie record in the database.

        `INSERT OR REPLACE` ensures that if a movie with the same title already exists,
        the new data overwrites the previous record.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                dedent(
                    """
                    INSERT OR REPLACE INTO movies
                        (title, year, tomatometer, audience_score, storyline,
                         genre, runtime, rating, release_date,
                         critic_1, critic_2, critic_3, critic_4, critic_5, critic_6)
                    VALUES
                        (:title, :year, :tomatometer, :audience_score, :storyline,
                         :genre, :runtime, :rating, :release_date,
                         :critic_1, :critic_2, :critic_3, :critic_4, :critic_5, :critic_6)
                    """
                ),
                data,
            )
            conn.commit()

        print(f"[DB] Saved: {data['title']} ({data['year']})")
