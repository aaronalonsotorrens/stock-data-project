from app.database import initialise_database
from app.ingestion import ingest_stock_data


def main():
    """
    Set up the database and load the latest Apple stock data.

    I've kept this as a separate script so I can run the ingestion
    without needing to start the API.
    """

    print("Setting up the database...")
    initialise_database()

    print("Starting stock ingestion...")
    ingest_stock_data("AAPL")


if __name__ == "__main__":
    main()
