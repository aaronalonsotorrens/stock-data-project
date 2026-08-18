import sqlite3
from pathlib import Path


# Work out where the main project folder is.
# Using a path like this means the database location doesn't depend
# on which folder I happen to run the Python command from.
BASE_DIR = Path(__file__).resolve().parent.parent

# Keep the SQLite database in its own data folder.
DB_PATH = BASE_DIR / "data" / "stocks.db"


def get_connection():
    """
    Open a connection to the SQLite database.

    I've kept this in one function so I don't need to repeat the
    connection setup everywhere else in the project.
    """

    # Make sure the data folder exists before SQLite tries to create
    # or open the database file.
    DB_PATH.parent.mkdir(exist_ok=True)

    connection = sqlite3.connect(DB_PATH)

    return connection


def initialise_database():
    """
    Create the stock_prices table if it doesn't already exist.

    Each row represents the daily price data for one stock.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume INTEGER NOT NULL,
            UNIQUE(ticker, date)
        )
        """
    )

    connection.commit()
    connection.close()