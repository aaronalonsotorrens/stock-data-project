import pandas as pd

from app import database
from app.database import initialise_database
from app.ingestion import store_stock_data


def test_incomplete_row_is_skipped(tmp_path, monkeypatch):
    """
    Check that a stock row with a missing required value
    is skipped rather than written to the database.
    """

    # Use a temporary database so this test doesn't touch
    # the real local stocks.db file.
    test_db = tmp_path / "test_stocks.db"
    monkeypatch.setattr(database, "DB_PATH", test_db)

    initialise_database()

    # Create one example Yahoo-style row with a missing close price.
    data = pd.DataFrame(
        {
            "Open": [200.0],
            "High": [205.0],
            "Low": [198.0],
            "Close": [None],
            "Volume": [1000000],
        },
        index=pd.to_datetime(["2026-08-18"]),
    )

    rows_stored, rows_skipped = store_stock_data(data, "AAPL")

    assert rows_stored == 0
    assert rows_skipped == 1

    # Also check that nothing was actually added to the database.
    connection = database.get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM stock_prices")
    row_count = cursor.fetchone()[0]

    connection.close()

    assert row_count == 0


def test_duplicate_ticker_and_date_does_not_create_second_row(
    tmp_path,
    monkeypatch,
):
    """
    Check that ingesting the same ticker and date twice
    updates the existing record rather than creating a duplicate.
    """

    test_db = tmp_path / "test_stocks.db"
    monkeypatch.setattr(database, "DB_PATH", test_db)

    initialise_database()

    data = pd.DataFrame(
        {
            "Open": [200.0],
            "High": [205.0],
            "Low": [198.0],
            "Close": [203.0],
            "Volume": [1000000],
        },
        index=pd.to_datetime(["2026-08-18"]),
    )

    # Store exactly the same ticker/date twice.
    store_stock_data(data, "AAPL")
    store_stock_data(data, "AAPL")

    connection = database.get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM stock_prices
        WHERE ticker = ? AND date = ?
        """,
        ("AAPL", "2026-08-18"),
    )

    row_count = cursor.fetchone()[0]

    connection.close()

    assert row_count == 1