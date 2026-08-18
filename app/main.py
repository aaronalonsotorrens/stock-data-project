import sqlite3

from fastapi import FastAPI, HTTPException

from app.database import get_connection, initialise_database
from app.ingestion import ingest_stock_data


# Create the FastAPI app.
# FastAPI also gives us an interactive /docs page, which is handy
# for testing the project without needing to build a full frontend.
app = FastAPI(
    title="Stock Data API",
    description="A small API for storing and retrieving Apple stock data.",
    version="1.0.0",
)


@app.on_event("startup")
def startup():
    """
    Make sure the database and stock_prices table exist
    whenever the API starts up.
    """

    initialise_database()


@app.get("/")
def root():
    """
    Simple route so I can quickly check that the API is running.
    """

    return {
        "message": "Stock Data API is running"
    }


@app.get("/health")
def health():
    """
    Basic health check endpoint.

    This is useful if I just want to confirm the service itself is alive.
    """

    return {
        "status": "healthy"
    }


@app.get("/stocks/{ticker}")
def get_stock_data(ticker: str):
    """
    Get all the stock data we've stored for a ticker.

    The newest dates are returned first.
    """

    connection = get_connection()

    # This lets SQLite return rows using their column names,
    # which makes them easy to turn into dictionaries for the API response.
    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            ticker,
            date,
            open,
            high,
            low,
            close,
            volume
        FROM stock_prices
        WHERE ticker = ?
        ORDER BY date DESC
        """,
        (ticker.upper(),),
    )

    rows = cursor.fetchall()

    connection.close()

    # Return a 404 rather than just giving back an empty list
    # if we don't have any data for that ticker.
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No stored data found for {ticker.upper()}",
        )

    return [dict(row) for row in rows]


@app.get("/stocks/{ticker}/latest")
def get_latest_stock_price(ticker: str):
    """
    Get the most recent stock record we've stored for a ticker.
    """

    connection = get_connection()
    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            ticker,
            date,
            open,
            high,
            low,
            close,
            volume
        FROM stock_prices
        WHERE ticker = ?
        ORDER BY date DESC
        LIMIT 1
        """,
        (ticker.upper(),),
    )

    row = cursor.fetchone()

    connection.close()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"No stored data found for {ticker.upper()}",
        )

    return dict(row)


@app.post("/stocks/{ticker}/ingest")
def ingest(ticker: str):
    """
    Fetch fresh stock data and save it into the database.

    We're mainly using AAPL for this task, but keeping ticker as an
    argument means the same setup can work for another stock later.
    """

    rows_processed = ingest_stock_data(ticker.upper())

    if rows_processed == 0:
        raise HTTPException(
            status_code=500,
            detail=f"No data could be ingested for {ticker.upper()}",
        )

    return {
        "message": f"Stock data ingested for {ticker.upper()}",
        "rows_processed": rows_processed,
    }