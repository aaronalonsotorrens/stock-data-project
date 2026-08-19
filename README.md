# Stock Data Project

## Project Overview

This project was built as part of a Data Engineer final interview task.

The aim was to build a small end-to-end application that can fetch Apple stock data, store it in a database, and make that stored data available through a simple display layer.

The task was not really about building a perfect production-ready application. The main focus was more on showing how I approach a problem, how I design something from scratch, how I learn new concepts, and what I do when I run into problems.

For that reason, I tried to keep the project fairly simple while still separating the main responsibilities clearly.

The project currently:

- Fetches Apple stock data from Yahoo Finance.
- Stores the data in SQLite.
- Checks the returned data before storing it.
- Tracks how many rows were fetched, stored and skipped during ingestion.
- Makes the stored data available through FastAPI.
- Provides a small HTML frontend so the data is easier to view without needing to understand Swagger.
- Keeps FastAPI's Swagger interface available for directly testing the API.
- Runs locally or through Docker.
- Uses a Docker volume so the SQLite database can persist if the container is removed.
- Includes automated API tests using pytest.
- Uses GitHub Actions to automatically run the tests whenever changes are pushed to the main branch.
- Uses pinned dependency versions so the project is more repeatable.

The main stock used throughout the project is Apple:

```text
AAPL
```

---

## Architecture

I kept the architecture quite small because the amount of data and the scope of the task are both fairly limited.

The main flow is:

```text
Yahoo Finance
      ↓
   yfinance
      ↓
Python ingestion
      ↓
   SQLite
      ↓
   FastAPI
    ↙     ↘
HTML       API
Frontend   /docs
```

When the application is running through Docker, the setup looks like this:

```text
                 Yahoo Finance
                       ↓
                    yfinance
                       ↓
               Python ingestion
                       ↓
                    SQLite
                       ↓
                    FastAPI
                  ↙         ↘
          HTML frontend    API / Swagger
                       ↓
                Docker Container
                       ↓
                /app/data folder
                       ↓
                 Docker Volume
```

GitHub Actions sits alongside the application rather than being part of the runtime data flow:

```text
Push to GitHub
      ↓
GitHub Actions
      ↓
Install dependencies
      ↓
Run pytest
      ↓
Pass ✅ / Fail ❌
```

I wanted to keep the main responsibilities separate rather than putting everything into one large script.

The main areas are:

```text
Getting the data
      ↓
Validating the data
      ↓
Storing the data
      ↓
Retrieving the data
      ↓
Displaying the data
```

This also means individual parts could be changed later without needing to completely rebuild the application.

For example, Yahoo Finance could be replaced with another stock API without needing to completely rewrite the FastAPI or frontend layers.

---

## Data Flow

The current data flow works like this:

1. The application requests stock data from Yahoo Finance using `yfinance`.
2. Yahoo Finance returns roughly one month of daily stock information.
3. The returned data is checked before being stored.
4. Any incomplete rows are skipped.
5. Valid daily records are written into SQLite.
6. FastAPI reads the stored data from SQLite.
7. The API can return the data as JSON.
8. Jinja2 is used to pass the stored stock data into the HTML frontend.
9. The HTML frontend displays the stored data in a more user-friendly way.
10. FastAPI's `/docs` page remains available for directly testing the API.

The ingestion process can also be triggered through the API.

For example:

```text
POST /stocks/AAPL/ingest
```

This runs the following flow:

```text
API request
      ↓
Yahoo Finance
      ↓
Data validation
      ↓
SQLite
```

The stored data can then be retrieved using:

```text
GET /stocks/AAPL
```

or viewed through:

```text
http://localhost:8000
```

---

## Project Structure

The project is currently structured like this:

```text
stock-data-project/
│
├── .github/
│   └── workflows/
│       └── tests.yml
│
├── app/
│   ├── templates/
│   │   └── index.html
│   ├── __init__.py
│   ├── database.py
│   ├── ingestion.py
│   └── main.py
│
├── data/
│   └── .gitkeep
│
├── tests/
│   └── test_api.py
│
├── .dockerignore
├── .gitignore
├── Dockerfile
├── README.md
├── requirements.txt
└── run.py
```

### `app/database.py`

This handles:

- The SQLite database location.
- Opening database connections.
- Creating the `stock_prices` table.

### `app/ingestion.py`

This handles:

- Fetching stock data from Yahoo Finance.
- Checking for incomplete rows.
- Saving valid data into SQLite.
- Updating existing records if the same ticker and date are ingested again.
- Tracking how many rows were fetched, stored and skipped.

### `app/main.py`

This contains:

- The FastAPI application.
- API endpoints.
- The health check.
- API-triggered stock ingestion.
- The route used to serve the HTML frontend.

### `app/templates/index.html`

This contains the small HTML frontend.

Jinja2 is used to insert the stock data returned from SQLite into the HTML page.

### `tests/test_api.py`

This contains the basic automated tests for the FastAPI application.

### `.github/workflows/tests.yml`

This contains the GitHub Actions workflow that automatically installs the dependencies and runs the tests whenever code is pushed to `main` or a pull request is opened.

### `run.py`

This gives a simple way to:

- Initialise the database.
- Fetch Apple stock data.
- Store it in SQLite.

---

# 1. Data Ingestion

## Yahoo Finance

I decided to use Yahoo Finance through the `yfinance` Python package.

For this task, the application retrieves roughly one month of daily Apple stock data.

The main values being stored are:

```text
Date
Ticker
Open
High
Low
Close
Volume
```

Although Apple is the stock being used for the task, I kept the ticker as an argument in the ingestion functions rather than hardcoding `AAPL` throughout the application.

For example:

```python
fetch_stock_data("AAPL")
```

The same setup could therefore potentially be used with another ticker later.

Apple is the ticker I have actually tested properly as part of this project.

---

## Data Validation

One thing I found quite early was that the external data source does not always return completely clean data.

On one of the first ingestion runs, Yahoo Finance returned 21 rows but one of those rows had a missing value.

This caused the database insert to fail because the stock price fields were set as required.

Rather than changing the database to allow incomplete records, I added a check before storing each row:

```python
if row[["Open", "High", "Low", "Close", "Volume"]].isna().any():
    print(f"Skipping incomplete data for {date.strftime('%Y-%m-%d')}.")
    continue
```

This means an incomplete daily record is skipped while the rest of the ingestion can still continue.

I preferred this approach because a daily stock record without its main price values is not particularly useful for this project.

Interestingly, when the ingestion was run again later, Yahoo Finance returned a complete version of that day's data and it was stored successfully.

---

## Ingestion Statistics

I originally returned a single value called:

```text
rows_processed
```

The problem with that was that it did not clearly explain what had happened if Yahoo Finance returned an incomplete row.

I changed the ingestion response so it now separates:

- `rows_fetched` – how many rows came back from Yahoo Finance.
- `rows_stored` – how many valid rows were successfully written to the database.
- `rows_skipped` – how many rows were ignored because required values were missing.

The current response looks like:

```json
{
    "ticker": "AAPL",
    "rows_fetched": 21,
    "rows_stored": 21,
    "rows_skipped": 0
}
```

If one row was incomplete, it could instead look like:

```json
{
    "ticker": "AAPL",
    "rows_fetched": 21,
    "rows_stored": 20,
    "rows_skipped": 1
}
```

This gives a much clearer picture of what actually happened during an ingestion run.

---

# 2. Data Storage

## SQLite

I chose SQLite as the database for this project.

The amount of data being stored is pretty small, so setting up something like PostgreSQL felt like extra complexity that was not really needed for this version.

SQLite also makes the application easier to run because there is no separate database server that needs to be installed or configured.

If this became a larger system with more data, lots of users, or multiple ingestion processes, I would probably move the storage layer to something like PostgreSQL.

---

## Database Schema

The project currently uses one main table:

```text
stock_prices
```

The schema is:

```text
id              INTEGER PRIMARY KEY
ticker          TEXT
date            TEXT
open            REAL
high            REAL
low             REAL
close           REAL
volume          INTEGER
```

Each row represents one day's stock data for one ticker.

I also added a unique constraint on:

```text
ticker + date
```

Using:

```sql
UNIQUE(ticker, date)
```

The reason for this is that ingestion may be run more than once.

I did not want the database to end up with multiple records for Apple on the same date.

When a ticker and date already exist, the ingestion uses:

```sql
ON CONFLICT(ticker, date)
DO UPDATE
```

So instead of creating another record, the existing one is updated.

This makes the ingestion safer to run repeatedly.

---

# 3. Display Layer

I originally used FastAPI's Swagger interface as the display layer because the brief allowed a simple API endpoint.

That worked technically, but I felt it was a bit confusing for somebody opening the project for the first time who might not be familiar with Swagger.

I therefore added a small HTML frontend using Jinja2.

The frontend is available at:

```text
http://localhost:8000
```

It shows:

- The latest stored Apple stock price.
- The date of the latest stored record.
- A table containing the stored daily stock data.
- A button to fetch fresh Apple stock data.
- A short explanation of where the data comes from and how the project works.
- A link to the FastAPI `/docs` page for anybody who wants to interact with the API directly.

I deliberately kept the frontend small because the main focus of the task is the data flow and architecture rather than UI design.

The Swagger interface is still available at:

```text
http://localhost:8000/docs
```

This means there are now two ways to interact with the project:

```text
Normal user
     ↓
HTML frontend

Technical/API user
     ↓
FastAPI /docs
```

---

## Jinja2

Jinja2 is used as the template engine for the frontend.

In simple terms, it lets FastAPI take data from Python and put it into the HTML page.

For example:

```html
{{ latest.close }}
```

can display the latest stored closing price.

It also lets the page loop through all stored stock records:

```html
{% for row in stock_data %}
```

So the flow is:

```text
SQLite data
    ↓
FastAPI
    ↓
Jinja2
    ↓
HTML page
```

I used this instead of adding a bigger frontend framework because it kept the display layer simple and easier to understand.

---

## API Endpoints

### Health Check

```text
GET /health
```

Example response:

```json
{
    "status": "healthy"
}
```

This is a basic endpoint to quickly check that the service itself is alive.

---

### Get Stored Stock Data

```text
GET /stocks/{ticker}
```

Example:

```text
GET /stocks/AAPL
```

This returns all of the stored records for the selected ticker.

The newest records are returned first.

Example:

```json
[
    {
        "id": 21,
        "ticker": "AAPL",
        "date": "2026-08-18",
        "open": 307.5299987792969,
        "high": 309.95001220703125,
        "low": 305.739990234375,
        "close": 309.8800048828125,
        "volume": 9208233
    }
]
```

---

### Get Latest Stock Record

```text
GET /stocks/{ticker}/latest
```

Example:

```text
GET /stocks/AAPL/latest
```

This returns only the most recent record currently stored for that ticker.

---

### Run Stock Ingestion

```text
POST /stocks/{ticker}/ingest
```

Example:

```text
POST /stocks/AAPL/ingest
```

This fetches fresh stock data from Yahoo Finance and stores it in SQLite.

Example response:

```json
{
    "ticker": "AAPL",
    "rows_fetched": 21,
    "rows_stored": 21,
    "rows_skipped": 0
}
```

---

# 4. Deployment

## Why Docker?

I chose Docker as the deployment option for this project.

The main reason was that it gives a repeatable setup without needing to add a full cloud deployment just for the sake of it.

It means someone reviewing the project should be able to:

```text
Clone the repo
      ↓
Build the Docker image
      ↓
Run the container
      ↓
Use the application
```

without manually recreating my exact Python environment.

Docker was also something I wanted to get more practical experience with, so this felt like a useful opportunity to use it as part of the project.

---

## Dockerfile

The Docker image:

1. Starts from a lightweight Python image.
2. Creates a working directory inside the container.
3. Copies `requirements.txt`.
4. Installs the project dependencies.
5. Copies the application into the container.
6. Creates the data directory.
7. Exposes port `8000`.
8. Starts the FastAPI application using Uvicorn.

The final command used by the container is:

```text
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Docker Build

From the root of the project:

```powershell
docker build -t stock-data-api .
```

For a completely fresh rebuild:

```powershell
docker build --no-cache -t stock-data-api .
```

This creates the Docker image:

```text
stock-data-api
```

---

## Docker Volume

The project uses a Docker volume for the SQLite database.

Create it with:

```powershell
docker volume create stock-data
```

This creates persistent Docker-managed storage called:

```text
stock-data
```

---

## Running the Container

The application can then be started using:

```powershell
docker run --name stock-data-container -p 8000:8000 -v stock-data:/app/data stock-data-api
```

The frontend is then available at:

```text
http://localhost:8000
```

and the Swagger interface is available at:

```text
http://localhost:8000/docs
```

---

## Docker Data Persistence

My first Docker setup stored the SQLite database directly inside the container.

The problem with this is that removing the container would also remove the database.

To fix this, I mounted the application's data directory to a Docker volume:

```text
-v stock-data:/app/data
```

The setup therefore becomes:

```text
Docker Container
      ↓
   /app/data
      ↓
 Docker Volume
      ↓
   stocks.db
```

I tested this by:

1. Starting the Docker container.
2. Running the Apple stock ingestion.
3. Confirming the data was available.
4. Stopping the container.
5. Removing the container.
6. Creating a new container using the same Docker volume.
7. Opening the frontend without running ingestion again.

The Apple stock data was still available.

This confirmed that the database was being persisted separately from the container itself.

---

# Technologies Used

- **Python 3** – Main programming language used throughout the application.
- **yfinance** – Used to retrieve Apple stock data from Yahoo Finance.
- **Pandas** – Used to work with the stock data returned by `yfinance`.
- **SQLite** – Used to store the stock data.
- **FastAPI** – Used to create the API and expose the stored data.
- **Uvicorn** – Used to run the FastAPI application.
- **Jinja2** – Used to render stock data inside the HTML frontend.
- **HTML/CSS/JavaScript** – Used for the small user-facing display layer and refresh button.
- **pytest** – Used for automated testing.
- **httpx / FastAPI TestClient** – Used to call the application during automated tests.
- **Docker** – Used to make the application repeatable and portable.
- **Docker Volumes** – Used to keep the SQLite database persistent between containers.
- **GitHub Actions** – Used to automatically run the test suite after code changes.
- **Git** – Used for version control.
- **GitHub** – Used to host the project repository.

---

# Running the Project Locally

## Clone the Repository

Clone the repository:

```bash
git clone <repository-url>
```

Move into the project:

```bash
cd stock-data-project
```

---

## Create a Virtual Environment

On Windows:

```powershell
python -m venv venv
```

Activate the environment:

```powershell
venv\Scripts\activate
```

---

## Install Dependencies

Install the required Python packages using:

```powershell
python -m pip install -r requirements.txt
```

---

## Initialise the Database and Fetch Apple Data

Run:

```powershell
python run.py
```

This runs:

```text
Create database
      ↓
Fetch AAPL data
      ↓
Validate records
      ↓
Store data in SQLite
```

Example output:

```text
Setting up the database...
Starting stock ingestion...
Fetching stock data for AAPL...
Fetched 21 rows.
Stored 21 rows. Skipped 0 rows.
```

---

## Start the API

Run:

```powershell
python -m uvicorn app.main:app --reload
```

The frontend can then be accessed at:

```text
http://localhost:8000
```

The Swagger documentation can be opened at:

```text
http://localhost:8000/docs
```

---

# Testing

I tested the application throughout development rather than building everything first and trying to debug the whole project at the end.

The main manual checks completed are:

| Test | Result |
| --- | --- |
| Yahoo Finance returns AAPL data | ✅ Pass |
| SQLite database is created | ✅ Pass |
| AAPL data is written into SQLite | ✅ Pass |
| Incomplete stock rows are skipped | ✅ Pass |
| Re-running ingestion does not create duplicate dates | ✅ Pass |
| Existing records can be updated | ✅ Pass |
| `GET /stocks/AAPL` returns stored data | ✅ Pass |
| `GET /stocks/AAPL/latest` returns the latest record | ✅ Pass |
| `POST /stocks/AAPL/ingest` triggers ingestion | ✅ Pass |
| `/health` endpoint responds | ✅ Pass |
| HTML frontend loads | ✅ Pass |
| Frontend refresh button triggers ingestion | ✅ Pass |
| FastAPI runs locally | ✅ Pass |
| Docker image builds successfully | ✅ Pass |
| Frontend and FastAPI run inside Docker | ✅ Pass |
| Yahoo Finance ingestion works inside Docker | ✅ Pass |
| SQLite data persists through a Docker volume | ✅ Pass |
| Automated tests run locally | ✅ Pass |
| GitHub Actions automatically runs the tests | ✅ Pass |

---

## Automated Testing

I added a small automated test suite using `pytest` and FastAPI's `TestClient`.

The current tests check that:

- The `/health` endpoint returns a successful response.
- An unknown ticker returns a clear `404`.
- The HTML homepage loads successfully.

The tests can be run locally using:

```powershell
python -m pytest
```

Current result:

```text
3 passed
```

I deliberately kept the initial test suite small and focused on a few important behaviours rather than trying to test every line of the project.

With more time, I would add more tests around ingestion and database behaviour.

---

# GitHub Actions / CI

I added a small GitHub Actions workflow as the automation part of the project.

The workflow runs automatically whenever:

- Code is pushed to the `main` branch.
- A pull request is opened against `main`.

The workflow:

```text
Push code to GitHub
        ↓
Create a fresh environment
        ↓
Set up Python
        ↓
Install requirements
        ↓
Run pytest
        ↓
Pass ✅ / Fail ❌
```

The main reason I added this was to make sure the project does not only work on my own machine.

GitHub Actions runs the tests in a fresh environment, which actually helped expose an issue that my local setup had hidden.

---

# What Works

The following parts of the project are currently working:

- Apple stock data can be fetched from Yahoo Finance.
- Roughly one month of daily historical data can be retrieved.
- Stock data is stored in a separate SQLite database.
- The database is automatically created if it does not already exist.
- Incomplete stock records are detected and skipped.
- Duplicate ticker/date combinations are prevented.
- Existing records can be updated when ingestion runs again.
- Ingestion reports rows fetched, stored and skipped.
- Stored stock data can be retrieved through FastAPI.
- The latest stored stock record can be retrieved separately.
- Stock ingestion can be triggered through the API.
- A simple HTML frontend displays the stored Apple stock data.
- The frontend can trigger fresh stock ingestion.
- FastAPI's Swagger interface remains available for direct API testing.
- The application can run locally.
- The application can run inside Docker.
- SQLite data can persist between Docker containers through a Docker volume.
- Automated API tests run successfully using pytest.
- GitHub Actions automatically runs the tests after pushes to `main`.
- The application can create its own database in a clean environment.
- Package versions are pinned in `requirements.txt`.

---

# What Doesn't Work / Current Limitations

This is deliberately a small project, so there are still several things I would not consider production-ready.

## Ingestion Is Not Automatic

At the moment, ingestion needs to be triggered manually.

This can be done using:

```powershell
python run.py
```

or through:

```text
POST /stocks/{ticker}/ingest
```

There is currently no scheduled ingestion job.

---

## Apple Is the Main Tested Ticker

The functions accept another ticker value, but Apple is the one I have actually tested properly as part of this task.

---

## Error Handling Is Still Quite Basic

The project handles some obvious issues, such as incomplete stock records, but the error handling could go much further.

For example, I would add:

- Better handling of network failures.
- Retry logic for temporary API problems.
- More useful error responses.
- Structured logging.

---

## SQLite Has Limitations

SQLite works well for this project because the amount of data is small and the application is simple.

I probably would not use it for a larger application with:

- Lots of users.
- Large amounts of data.
- Multiple application instances.
- Multiple ingestion processes.

In that situation I would probably move to PostgreSQL.

---

## No Authentication

There is currently no authentication on the API.

Anyone with access to the application could call the endpoints.

That is fine for this small task but would need to be considered for a real application.

---

## No Pagination

The following endpoint:

```text
GET /stocks/{ticker}
```

currently returns all stored rows for the ticker.

That is fine when storing roughly a month of data, but it would become inefficient if the database contained years of historical prices.

---

# Problems I Hit and How I Solved Them

One thing I found useful while building the project was seeing where my original assumptions stopped working once I actually started running the code.

Rather than hiding those issues, I have included some of the main ones below.

---

## Missing Yahoo Finance Data

On my first ingestion run, Yahoo Finance successfully returned 21 rows.

However, one of those rows contained incomplete stock data.

This caused SQLite to return:

```text
NOT NULL constraint failed: stock_prices.close
```

One option would have been to change the database and allow null values.

I decided against that because I did not think a daily stock record without its main price values was particularly useful.

Instead, I kept the database constraint and added validation in the ingestion layer.

The application now checks:

```python
if row[["Open", "High", "Low", "Close", "Volume"]].isna().any():
    print(f"Skipping incomplete data for {date.strftime('%Y-%m-%d')}.")
    continue
```

This allowed the remaining valid data to be stored without weakening the database structure.

When I ran ingestion again later, Yahoo Finance returned a complete version of that day's data and it was stored normally.

---

## Windows Blocking `pip.exe`

While setting up the virtual environment, Windows was blocking direct calls to:

```powershell
pip
```

with an access denied error.

Instead of getting stuck changing system permissions, I tried running pip through the active Python interpreter:

```powershell
python -m pip
```

For example:

```powershell
python -m pip install yfinance fastapi uvicorn pandas
```

This worked and allowed me to carry on with the project.

I also used `python -m pip` when installing the testing and frontend dependencies.

---

## Dockerfile Was Empty

My first Docker build failed with:

```text
the Dockerfile cannot be empty
```

The Dockerfile had been created in VS Code but I had forgotten to save the contents before running the build.

Once the file was saved, the image built successfully.

It was a simple issue, but it was a good reminder to check the basic things first when something fails.

---

## Docker Build Context Was Too Large

My first successful Docker build sent around 175 MB as the build context.

That seemed much larger than the application actually needed.

The reason was that local development files, including my Python virtual environment, were being sent to Docker.

I added a `.dockerignore` containing:

```text
venv/
.venv/
__pycache__/
*.pyc
.git/
data/*.db
.env
.vscode/
```

This keeps unnecessary local files out of the Docker build and keeps the image setup cleaner.

---

## SQLite Data Was Originally Tied to the Container

My first Docker version stored the SQLite database directly inside the container.

The issue with this was that if I removed the container, the database would disappear with it.

I changed the setup to use a Docker volume:

```powershell
-v stock-data:/app/data
```

I then tested the setup by:

1. Loading Apple stock data.
2. Removing the Docker container.
3. Creating another container using the same volume.
4. Opening the frontend without running ingestion again.

The data was still there.

That confirmed that the SQLite database was persisting separately from the container.

---

## SQLite Database Was Accidentally Being Tracked by Git

While checking the repository, I noticed that `data/stocks.db` was still being tracked by Git.

I had added a database rule to `.gitignore`, but `.gitignore` does not stop tracking a file that has already been committed.

I removed the database from Git tracking using:

```powershell
git rm --cached data/stocks.db
```

and added:

```text
data/*.db
```

to `.gitignore`.

The database still exists locally and is created normally by the application, but it is no longer stored in the GitHub repository.

I kept:

```text
data/.gitkeep
```

so that the empty `data` directory still exists when somebody clones the project.

---

## GitHub Actions Failed After Removing the Local Database

At first, my automated tests passed locally and also passed in GitHub Actions.

I later removed `data/stocks.db` from Git because it is generated application data rather than source code.

Once I did that, the next GitHub Actions run failed with:

```text
sqlite3.OperationalError: no such table: stock_prices
```

The issue was that my tests had accidentally been relying on the existing database on my own machine.

GitHub Actions starts from a completely fresh copy of the repository, so once `stocks.db` was no longer committed, there was no existing `stock_prices` table when the tests started.

This exposed a dependency on local state that I had not noticed.

I fixed this by running FastAPI's `TestClient` as a context manager:

```python
with TestClient(app) as client:
    response = client.get("/health")
```

This makes sure the FastAPI startup logic runs during the test.

The startup logic calls:

```python
initialise_database()
```

which creates the database and table if they do not already exist.

The flow now becomes:

```text
GitHub Actions starts
        ↓
Fresh copy of repository
        ↓
TestClient starts FastAPI
        ↓
Database initialisation runs
        ↓
stock_prices table is created
        ↓
Tests run
        ↓
Tests pass
```

After changing the tests, the GitHub Actions workflow passed again.

This was useful because it showed one of the main benefits of CI: it tested the project in a clean environment and exposed something that had been hidden by my own local setup.

---

# Improvements With More Time

There are still quite a few things I would look at if the project needed to go further.

## Automated Ingestion

At the moment the stock ingestion needs to be triggered manually.

I would probably schedule the ingestion to run automatically once per day, potentially after the market closes.

This could be handled by a scheduled worker or cloud scheduler depending on where the application was deployed.

---

## Retry Logic

The application relies on an external data source.

External APIs can temporarily fail, so I would add retry handling around the Yahoo Finance request rather than immediately treating the first failure as final.

I would also make sure the number of retries was limited so the application did not retry forever.

---

## Structured Logging

The current ingestion process mainly uses `print()` statements.

For a production application, I would replace these with proper structured logging.

That would make it easier to answer questions such as:

```text
When did ingestion run?
Did it succeed?
How many rows were loaded?
Why did it fail?
```

---

## PostgreSQL

If the application became bigger, I would probably move from SQLite to PostgreSQL.

That would make more sense if there were more users, significantly more data, or several processes accessing the database at once.

---

## Database Migrations

If the schema started changing over time, I would add a database migration tool such as Alembic.

This would make database changes much easier to manage and reproduce.

---

## More Automated Testing

I currently have a small automated API test suite.

With more time, I would expand it to cover:

- Database creation.
- Successful ingestion.
- Missing stock values.
- Duplicate ticker/date handling.
- Updating existing records.
- External API failures.
- Invalid ticker behaviour.
- Frontend refresh behaviour.

---

## Better FastAPI Response Models

I would add proper Pydantic response models.

This would:

- Make the expected API responses clearer.
- Add stronger validation.
- Improve the automatically generated Swagger documentation.

---

## Pagination

If the application stored a lot more historical data, I would add pagination to:

```text
GET /stocks/{ticker}
```

rather than returning every record in a single response.

---

## Cloud Deployment

Docker currently gives the project a repeatable local deployment.

If I wanted the API to be publicly accessible, I could deploy the Docker container to a cloud provider.

At that point I would also move away from a local SQLite database and use a more appropriate managed database.

---

## Monitoring

For a production version, I would want visibility into things like:

- Did today's ingestion succeed?
- How many rows were loaded?
- How long did ingestion take?
- Is the API responding?
- Are requests failing?
- Is the external stock service available?

The current `/health` endpoint is a very simple starting point, but production monitoring would need to go further.

---

# Main Design Decisions

## Keep the Architecture Small

I deliberately avoided adding technologies that did not really help solve the problem.

For example, I did not add:

- Kubernetes.
- Kafka.
- Redis.
- Airflow.
- Multiple microservices.

All of those technologies can be useful, but for a small application storing roughly one month of Apple stock data they would mostly add extra complexity.

---

## Keep Responsibilities Separate

The main parts of the project are split into separate files.

```text
database.py
      ↓
Database setup and connections

ingestion.py
      ↓
Fetching, validating and storing stock data

main.py
      ↓
API endpoints and frontend route

index.html
      ↓
Simple user-facing display
```

This makes the project easier to understand and gives each part a clearer responsibility.

---

## Keep the Schema Simple

There is currently only one main table.

I could have created separate stock and price tables, but with the scope of this task that felt unnecessary.

Keeping `ticker` on each stock price record means I can still support more than one stock later without adding much complexity.

---

## Make Ingestion Safe to Repeat

Using:

```sql
UNIQUE(ticker, date)
```

together with:

```sql
ON CONFLICT ... DO UPDATE
```

means the ingestion can be run repeatedly without filling the database with duplicate daily records.

This became particularly useful when the previously incomplete Yahoo Finance record was later returned with complete data.

---

## Keep the Display Layer Small

I initially used FastAPI's Swagger interface because the brief allowed a simple API endpoint as the display layer.

After testing it, I felt Swagger was useful for technical testing but not particularly friendly for somebody seeing the project for the first time.

I therefore added a very small HTML frontend using Jinja2.

I deliberately avoided using something larger like React because that would have introduced another framework, another build process and more complexity than this task really needed.

The final setup gives me:

```text
Simple HTML frontend
        +
FastAPI /docs
```

so the project is easy to view while still keeping direct API access available.

---

## Use Docker for Repeatability

The brief allowed Docker, cloud deployment, or documented local deployment.

I chose Docker because it gave me a repeatable environment without introducing unnecessary cloud infrastructure.

Someone reviewing the repository can build the same Python environment and run the application without needing to recreate my local setup manually.

---

## Use CI as a Safety Check

I added GitHub Actions because I wanted to check that the project worked outside my own local environment.

This became useful almost immediately because the CI run exposed that my tests had been relying on an existing local SQLite database.

That gave me a practical reason for keeping the automation rather than adding it just because it was listed as a bonus.

---

# Use of AI

The task allowed the use of AI tools, and I used AI throughout the project mainly as a pair-programming and learning tool.

I used AI to help with:

- Talking through architecture choices.
- Breaking the task into smaller steps.
- Helping structure some of the initial code.
- Explaining parts of FastAPI, Docker, Jinja2 and GitHub Actions that I was less familiar with.
- Debugging problems as they came up.
- Reviewing the project structure and documentation.

I deliberately worked through the application one stage at a time rather than generating the whole project and assuming it worked.

For example, I tested:

```text
Yahoo Finance
      ↓
SQLite
```

before adding FastAPI.

I then tested:

```text
SQLite
      ↓
FastAPI
```

before moving onto Docker.

After that, I added the frontend, automated tests and GitHub Actions separately and tested each of those as they were added.

I found this much more useful because I could understand what each part was doing and deal with problems individually as they appeared.

---

# Current Requirements

The Python dependencies are listed in:

```text
requirements.txt
```

They are pinned to the versions used while building and testing the project:

```text
yfinance==1.6.0
fastapi==0.141.1
uvicorn==0.52.3
pandas==3.0.5
Jinja2==3.1.6
pytest==9.1.1
httpx==0.28.1
```

Pinning the versions makes the setup more repeatable because the same versions are installed locally, inside Docker and in GitHub Actions.

They can be installed using:

```powershell
python -m pip install -r requirements.txt
```

---

# `.gitignore`

Local development files that should not be committed to GitHub are ignored.

This includes things such as:

```text
venv/
__pycache__/
*.pyc
.env
data/*.db
```

The SQLite database itself is therefore not stored in GitHub.

The application creates the database when it starts.

The `data/.gitkeep` file is kept so that the `data` folder still exists in a fresh clone of the repository.

---

# `.dockerignore`

Docker also ignores local files that are not needed when building the application image.

This includes:

```text
venv/
.venv/
__pycache__/
*.pyc
.git/
data/*.db
.env
.vscode/
```

This avoids sending things such as my local virtual environment into the Docker build.

---

# Current Status

The core requirements of the task are currently covered.

### Data Ingestion

- Apple stock data is retrieved from Yahoo Finance.
- Incomplete records are handled.
- The ingestion response reports rows fetched, stored and skipped.

### Data Storage

- Stock data is stored in SQLite.
- A simple schema has been defined.
- Duplicate ticker/date records are prevented.
- Existing records can be updated.

### Display Layer

- Stored data can be retrieved through FastAPI.
- A small HTML frontend displays the stored Apple stock data.
- The frontend can trigger a refresh of the stock data.
- Swagger remains available for direct API testing.

### Deployment

- The application has been containerised using Docker.
- The Docker image builds successfully.
- The frontend and API both run inside the container.
- A Docker volume is used for persistent SQLite storage.

### Testing / Automation

- Basic automated API tests have been added using pytest.
- Tests pass locally.
- GitHub Actions automatically runs the tests on pushes to `main`.
- The CI workflow has been tested successfully in a clean environment.

### GitHub / Documentation

- The project is version controlled with Git.
- The project is hosted on GitHub.
- Generated SQLite database files are excluded from source control.
- Dependencies are pinned for reproducibility.
- The README documents the architecture, setup, current functionality, limitations, issues encountered and possible improvements.

---

# Final Thoughts

The aim of this project was not to build a full stock trading platform or a production-ready financial application.

It was to build a small working data flow from scratch and show the thinking behind it.

The current application demonstrates:

```text
External data source
        ↓
Data ingestion
        ↓
Data validation
        ↓
Persistent storage
        ↓
API
        ↓
HTML frontend
        ↓
Containerised deployment

        +

Automated testing
        ↓
GitHub Actions CI
```

There are plenty of things I could add if the requirements became larger, but I deliberately tried to keep the first version understandable, repeatable and focused on the actual task.