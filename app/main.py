import sqlite3

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import get_connection, initialise_database
from app.ingestion import ingest_stock_data


# Create the FastAPI app.
# FastAPI also gives us an interactive /docs page, which is handy
# for testing the API directly.
app = FastAPI(
    title="Stock Data API",
    description="A small API for storing and retrieving Apple stock data.",
    version="1.0.0",
)


# Serve the small static files used by the frontend.
# At the moment this is mainly the CSS stylesheet.
app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static",
)


# Tell FastAPI where the HTML template for the frontend lives.
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
def startup():
    """
    Make sure the database and stock_prices table exist
    whenever the API starts up.
    """

    initialise_database()


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """
    Show a simple frontend with the Apple stock data.

    I wanted something easier to use than just the Swagger page,
    while still keeping the frontend small and focused.
    """

    connection = get_connection()
    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
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
        ("AAPL",),
    )

    rows = cursor.fetchall()

    connection.close()

    # Turn the SQLite rows into normal dictionaries so they're
    # easier to use inside the HTML template.
    stock_data = [dict(row) for row in rows]

    # Because the data is ordered newest first, the first row
    # is the latest record if we have any data stored.
    latest = stock_data[0] if stock_data else None

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "stock_data": stock_data,
            "latest": latest,
        },
    )


@app.get("/health")
def health():
    """
    Basic health check endpoint.

    This is useful if I just want to confirm the service itself is alive.
    """

    return {"status": "healthy"}


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

    The response also gives a small summary of what happened
    during the ingestion.
    """

    result = ingest_stock_data(ticker.upper())

    # If nothing was fetched at all, something probably went wrong
    # with the external data request.
    if result["rows_fetched"] == 0:
        raise HTTPException(
            status_code=500,
            detail=f"No data could be ingested for {ticker.upper()}",
        )

    return result