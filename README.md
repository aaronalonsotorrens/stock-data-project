# Stock Data Project

## Project Overview

This project was built as part of a Data Engineer final interview task.

The aim was to build a small end-to-end application that can fetch Apple stock data, store it in a database, and make that data available through a simple interface.

I tried to keep the project fairly small and understandable rather than adding technology that was not really needed for the task.

The application currently:

- Fetches Apple stock data from Yahoo Finance using `yfinance`.
- Validates the returned data before storing it.
- Stores daily stock prices in SQLite.
- Prevents duplicate ticker/date records.
- Makes the stored data available through FastAPI.
- Provides a small HTML/Jinja2 frontend.
- Runs locally or through Docker.
- Uses a Docker volume so the SQLite database persists between containers.
- Includes automated tests using pytest.
- Uses GitHub Actions to automatically run the tests after code changes.

The main stock used and tested throughout the project is:

```text
AAPL
```

---

## Architecture

The main application flow is:

```text
Yahoo Finance
      ↓
   yfinance
      ↓
Python ingestion
      ↓
Data validation
      ↓
   SQLite
      ↓
   FastAPI
    ↙     ↘
HTML       API
Frontend   /docs
```

When Docker is used, the SQLite database is stored separately from the container using a Docker volume:

```text
Docker Container
      ↓
   /app/data
      ↓
 Docker Volume
      ↓
   stocks.db
```

The project also has a small CI workflow:

```text
Push to GitHub
      ↓
GitHub Actions
      ↓
Install dependencies
      ↓
Run pytest
      ↓
Pass / Fail
```

---

## Project Structure

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

The main responsibilities are split between:

- `database.py` – database setup and connections.
- `ingestion.py` – fetching, validating and storing stock data.
- `main.py` – FastAPI endpoints and frontend route.
- `index.html` – small user-facing frontend.
- `test_api.py` – automated API/frontend tests.

---

# 1. Data Ingestion

## Yahoo Finance

Stock data is fetched using the `yfinance` Python package.

For this task, the application retrieves roughly one month of daily Apple stock data.

The values stored are:

```text
Date
Ticker
Open
High
Low
Close
Volume
```

Although Apple is the main stock used for the project, the ticker is passed into the ingestion functions rather than being hardcoded everywhere.

For example:

```python
fetch_stock_data("AAPL")
```

---

## Data Validation

One of the first issues I found was that Yahoo Finance did not always return completely clean data.

During one ingestion run, 21 rows were returned but one contained a missing stock price value.

Because the database fields are required, this caused:

```text
NOT NULL constraint failed: stock_prices.close
```

Rather than allowing incomplete values in the database, I added validation before each row is stored:

```python
if row[["Open", "High", "Low", "Close", "Volume"]].isna().any():
    print(f"Skipping incomplete data for {date.strftime('%Y-%m-%d')}.")
    continue
```

This allows valid rows to continue being stored while incomplete records are skipped.

---

## Ingestion Statistics

The ingestion process returns a small summary:

```json
{
    "ticker": "AAPL",
    "rows_fetched": 21,
    "rows_stored": 20,
    "rows_skipped": 1
}
```

This makes it easier to see what actually happened during an ingestion run rather than just returning one general processed-row count.

---

# 2. Data Storage

## SQLite

I chose SQLite because the amount of data and the scope of the task are both small.

It keeps the project easy to run because there is no separate database server to install or configure.

For a larger application with significantly more data, users or concurrent processes, I would probably move the storage layer to something like PostgreSQL.

---

## Database Schema

The project uses one main table:

```text
stock_prices
```

with the following structure:

```text
id       INTEGER PRIMARY KEY
ticker   TEXT
date     TEXT
open     REAL
high     REAL
low      REAL
close    REAL
volume   INTEGER
```

Each row represents one trading day for one ticker.

The table also contains:

```sql
UNIQUE(ticker, date)
```

This prevents multiple records being created for the same stock and date.

If that ticker/date already exists, ingestion uses:

```sql
ON CONFLICT(ticker, date)
DO UPDATE
```

so the existing record is updated instead.

This means the ingestion can safely be run more than once.

---

# 3. Display Layer

The application originally only used FastAPI's Swagger interface.

Although that worked for testing the API, I felt it was not particularly friendly for somebody opening the project for the first time.

I therefore added a small HTML frontend using Jinja2.

The frontend is available at:

```text
http://localhost:8000
```

It shows:

- The latest stored Apple stock price.
- The latest stored date.
- A table of the stored daily stock data.
- A button to fetch fresh stock data.
- A short explanation of the project.

FastAPI's Swagger interface is still available at:

```text
http://localhost:8000/docs
```

I deliberately kept the frontend small rather than adding something like React because the main focus of the task is the data pipeline rather than frontend development.

---

## API Endpoints

### Health Check

```text
GET /health
```

Returns:

```json
{
    "status": "healthy"
}
```

### Get Stored Stock Data

```text
GET /stocks/{ticker}
```

Example:

```text
GET /stocks/AAPL
```

Returns all stored records for the ticker, newest first.

### Get Latest Stock Record

```text
GET /stocks/{ticker}/latest
```

Returns only the most recent stored record.

### Run Stock Ingestion

```text
POST /stocks/{ticker}/ingest
```

Example:

```text
POST /stocks/AAPL/ingest
```

Returns an ingestion summary such as:

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

## Docker

I chose Docker because it gives the project a repeatable environment without needing to add unnecessary cloud infrastructure.

The basic flow is:

```text
Clone repository
      ↓
Build Docker image
      ↓
Run container
      ↓
Use application
```

Build the image using:

```powershell
docker build -t stock-data-api .
```

Create the persistent database volume:

```powershell
docker volume create stock-data
```

Run the application:

```powershell
docker run --name stock-data-container -p 8000:8000 -v stock-data:/app/data stock-data-api
```

The frontend is then available at:

```text
http://localhost:8000
```

and Swagger at:

```text
http://localhost:8000/docs
```

---

## Docker Data Persistence

Initially, the SQLite database existed only inside the Docker container.

That meant removing the container would also remove the stored data.

I changed the setup to mount:

```text
/app/data
```

to the Docker volume:

```text
stock-data
```

I tested this by loading the Apple data, deleting the container, creating another container using the same volume and checking the application without running ingestion again.

The data was still available, confirming that the database persisted independently of the container.

---

# Testing

I tested the application throughout development rather than building everything first and debugging it at the end.

Some of the main checks completed were:

| Test | Result |
| --- | --- |
| Yahoo Finance returns AAPL data | ✅ Pass |
| SQLite database is created | ✅ Pass |
| Stock data is stored | ✅ Pass |
| Incomplete records are skipped | ✅ Pass |
| Duplicate dates are prevented | ✅ Pass |
| API returns stored data | ✅ Pass |
| Latest stock endpoint works | ✅ Pass |
| API ingestion works | ✅ Pass |
| HTML frontend loads | ✅ Pass |
| Docker image builds and runs | ✅ Pass |
| SQLite persists through Docker volume | ✅ Pass |
| Automated tests run locally | ✅ Pass |
| GitHub Actions tests pass | ✅ Pass |

---

## Automated Tests

I added a small pytest test suite using FastAPI's `TestClient`.

The current tests check that:

- `/health` returns a successful response.
- An unknown ticker returns `404`.
- The HTML homepage loads successfully.

The tests can be run using:

```powershell
python -m pytest
```

Current result:

```text
3 passed
```

I kept the initial suite small rather than trying to test every line of the project.

With more time, I would add tests specifically around incomplete ingestion rows and duplicate ticker/date handling.

---

# GitHub Actions / CI

I added GitHub Actions so the project is also tested outside my local environment.

The workflow runs when code is pushed to `main` or a pull request is opened.

It:

```text
Checks out repository
        ↓
Sets up Python
        ↓
Installs requirements
        ↓
Runs pytest
```

This became particularly useful because CI exposed a hidden problem with my tests relying on my local database.

---

# Problems I Hit and How I Solved Them

## Missing Yahoo Finance Data

Yahoo Finance returned an incomplete row, which caused the SQLite `NOT NULL` constraint to fail.

I kept the database constraint and added validation in the ingestion layer so incomplete rows are skipped instead.

---

## Windows Blocking `pip.exe`

Windows was blocking direct calls to `pip.exe` with an access denied error.

Using:

```powershell
python -m pip
```

worked correctly, so I used that for installing project dependencies.

---

## Docker Build Context Was Too Large

My first Docker build sent around 175 MB as the build context because local files such as the virtual environment were being included.

I added a `.dockerignore` containing entries such as:

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

This stopped unnecessary development files being sent to Docker.

---

## SQLite Database Was Being Tracked by Git

I noticed that `data/stocks.db` was still being tracked by Git.

Because the database is generated application data, I removed it from source control using:

```powershell
git rm --cached data/stocks.db
```

and added:

```text
data/*.db
```

to `.gitignore`.

The application now creates the database itself when needed.

---

## GitHub Actions Exposed a Hidden Database Dependency

After removing `stocks.db` from Git, GitHub Actions failed with:

```text
sqlite3.OperationalError: no such table: stock_prices
```

The tests had been working locally because my machine already had a database and table.

GitHub Actions uses a fresh environment, which exposed this hidden dependency.

I fixed it by using FastAPI's `TestClient` as a context manager:

```python
with TestClient(app) as client:
    response = client.get("/health")
```

This makes sure FastAPI's startup logic runs during the tests.

The startup process calls:

```python
initialise_database()
```

so a fresh environment now creates the database and table before the tests run.

After that change, the GitHub Actions workflow passed again.

This was probably one of the more useful issues I hit because CI caught something that my own local environment had hidden.

---

# Technologies Used

- **Python 3**
- **yfinance**
- **Pandas**
- **SQLite**
- **FastAPI**
- **Uvicorn**
- **Jinja2**
- **HTML / CSS / JavaScript**
- **pytest**
- **FastAPI TestClient / httpx**
- **Docker**
- **Docker Volumes**
- **GitHub Actions**
- **Git**
- **GitHub**

---

# Running the Project Locally

Clone the repository:

```bash
git clone <repository-url>
cd stock-data-project
```

Create and activate a virtual environment:

```powershell
python -m venv venv
venv\Scripts\activate
```

Install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

Initialise the database and load Apple stock data:

```powershell
python run.py
```

Start the application:

```powershell
python -m uvicorn app.main:app --reload
```

Open:

```text
http://localhost:8000
```

or the Swagger interface:

```text
http://localhost:8000/docs
```

---

# Requirements

The direct Python dependencies are pinned in `requirements.txt`:

```text
yfinance==1.6.0
fastapi==0.141.1
uvicorn==0.52.3
pandas==3.0.5
Jinja2==3.1.6
pytest==9.1.1
httpx==0.28.1
```

Pinning the versions makes the project more repeatable across local development, Docker and GitHub Actions.

---

# Current Limitations / Improvements

This is deliberately a small project and there are still several things I would improve if it needed to go further.

Some of the main ones would be:

- Schedule ingestion automatically rather than triggering it manually.
- Add retry handling for temporary Yahoo Finance failures.
- Replace `print()` statements with proper application logging.
- Add more automated tests around ingestion and database behaviour.
- Add Pydantic response models to make the API contracts clearer.
- Move FastAPI's startup logic to the newer lifespan approach.
- Add pagination if significantly more historical data was stored.
- Move from SQLite to PostgreSQL for a larger multi-user application.
- Add authentication if the API was publicly accessible.
- Deploy the Docker application to a cloud environment if public access was required.

I deliberately did not add things such as Kubernetes, Kafka, Airflow or multiple services because they would add more complexity than this small application needs.

---

# Use of AI

The task allowed AI tools, and I used AI mainly as a pair-programming and learning tool.

I used it to help:

- Talk through architecture choices.
- Break the task into smaller steps.
- Explain unfamiliar parts of FastAPI, Docker, Jinja2 and GitHub Actions.
- Debug issues as they appeared.
- Review the project structure and documentation.

I worked through the application one part at a time and tested each stage rather than generating the whole project and assuming it worked.

That was particularly useful because several of the final design decisions came directly from problems I found while actually running the application.

---

# Final Thoughts

The aim of this project was not to build a production-ready stock trading platform.

It was to create a small working data pipeline and show the thinking behind it.

The final project covers:

```text
External data source
        ↓
Data ingestion
        ↓
Data validation
        ↓
SQLite storage
        ↓
FastAPI
        ↓
HTML frontend
        ↓
Docker deployment

        +

Automated tests
        ↓
GitHub Actions CI
```

There are plenty of ways the project could be extended, but I deliberately tried to keep this version understandable, repeatable and focused on the actual requirements.