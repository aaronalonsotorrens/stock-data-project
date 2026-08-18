import yfinance as yf

from app.database import get_connection


def fetch_stock_data(ticker="AAPL"):
    """
    Fetch the last month of daily stock data from Yahoo Finance.

    I've made ticker an argument rather than hardcoding Apple everywhere.
    We're only using AAPL for this task, but this makes it easy to support
    another stock later without changing the function.
    """

    stock = yf.Ticker(ticker)

    # One month is plenty of data for this demo and keeps the project small.
    data = stock.history(
        period="1mo",
        interval="1d",
        auto_adjust=False,
    )

    return data


def store_stock_data(data, ticker="AAPL"):
    """
    Save the stock data we've fetched into SQLite.

    If we already have a row for the same ticker and date, we update
    that row rather than creating a duplicate.

    I also keep track of how many rows were stored and how many
    had to be skipped.
    """

    connection = get_connection()
    cursor = connection.cursor()

    rows_stored = 0
    rows_skipped = 0

    # yfinance gives us a pandas DataFrame, so we go through each daily row.
    for date, row in data.iterrows():

        # Sometimes the API can return an incomplete row.
        # I'd rather skip that row than store incomplete stock data.
        if row[["Open", "High", "Low", "Close", "Volume"]].isna().any():
            print(
                f"Skipping incomplete data for "
                f"{date.strftime('%Y-%m-%d')}."
            )

            rows_skipped += 1
            continue

        cursor.execute(
            """
            INSERT INTO stock_prices (
                ticker,
                date,
                open,
                high,
                low,
                close,
                volume
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(ticker, date)
            DO UPDATE SET
                open = excluded.open,
                high = excluded.high,
                low = excluded.low,
                close = excluded.close,
                volume = excluded.volume
            """,
            (
                ticker.upper(),
                date.strftime("%Y-%m-%d"),
                float(row["Open"]),
                float(row["High"]),
                float(row["Low"]),
                float(row["Close"]),
                int(row["Volume"]),
            ),
        )

        rows_stored += 1

    connection.commit()
    connection.close()

    return rows_stored, rows_skipped


def ingest_stock_data(ticker="AAPL"):
    """
    Run the full ingestion process and return a small summary
    of what happened.
    """

    print(f"Fetching stock data for {ticker}...")

    try:
        data = fetch_stock_data(ticker)

        # If Yahoo gives us an empty result, stop here rather than
        # trying to insert nothing into the database.
        if data.empty:
            print(f"No stock data was returned for {ticker}.")

            return {
                "ticker": ticker.upper(),
                "rows_fetched": 0,
                "rows_stored": 0,
                "rows_skipped": 0,
            }

        rows_fetched = len(data)

        print(f"Fetched {rows_fetched} rows.")

        rows_stored, rows_skipped = store_stock_data(
            data,
            ticker,
        )

        print(
            f"Stored {rows_stored} rows. "
            f"Skipped {rows_skipped} rows."
        )

        return {
            "ticker": ticker.upper(),
            "rows_fetched": rows_fetched,
            "rows_stored": rows_stored,
            "rows_skipped": rows_skipped,
        }

    except Exception as error:
        # For this small project a simple error message is enough.
        # With more time I'd replace this with proper application logging.
        print(f"Something went wrong during ingestion: {error}")

        return {
            "ticker": ticker.upper(),
            "rows_fetched": 0,
            "rows_stored": 0,
            "rows_skipped": 0,
        }