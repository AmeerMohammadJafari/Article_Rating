# Article Rating Project

## Overview

This project provides an article rating system, where users can rate articles, and various tasks related to rating are processed asynchronously using Celery with Redis as the message broker.

## Prerequisites

Make sure you have the following installed:

- **Python** (preferably version 3.x)
- **Django** (installed via `pip install django`)
- **Redis** (used as a message broker for Celery)
- **Celery** (installed via `pip install celery`)

## Setting up the Environment

1. **Install dependencies**:
   First, clone the project and install the required Python packages.
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the Redis server**:
   Make sure the Redis server is running on the default port (`6379`).
   You can start it using:
   ```bash
   redis-server
   ```

3. **Run the Django application**:
   Start the Django development server:
   ```bash
   python manage.py runserver
   ```
   This will start the application on the default port (`8000`).

## Running Celery

To run Celery with the Django app, execute the following command:

```bash
celery -A article_rating worker --loglevel=debug -P solo
```

### Explanation:
- **`-A article_rating`**: Specifies the name of the Django project (replace `article_rating` with your actual project name if it's different).
- **`worker`**: Starts the Celery worker to process tasks.
- **`--loglevel=debug`**: Sets the logging level to `debug` for detailed logs.
- **`-P solo`**: Uses the `solo` pool for Celery, which is typically used for debugging or when running in a single process (for development purposes).

## Database Setup

Before starting the application, make sure to run migrations to set up the database:

```bash
python manage.py migrate
```
