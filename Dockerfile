# Start from a lightweight Python image.
# This gives the container Python without bringing in loads of stuff
# that this small project doesn't need.
FROM python:3.13-slim


# Everything for the project will live inside /app in the container.
WORKDIR /app


# Copy the requirements file first.
# Keeping this separate means Docker can reuse the installed packages
# if I change my code but haven't changed the dependencies.
COPY requirements.txt .


# Install the Python packages needed to run the project.
RUN python -m pip install --no-cache-dir -r requirements.txt


# Copy the rest of the project into the container.
COPY . .


# Make sure there's somewhere for SQLite to create its database file.
RUN mkdir -p data


# The FastAPI application will be available through port 8000.
EXPOSE 8000


# Start the FastAPI server when the container runs.
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]