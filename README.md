# Article Rating Service

A REST API where users rate articles from 0 to 5. Ratings are accepted immediately and folded into each
article's average **asynchronously in batches**, so a burst of votes doesn't turn into a burst of writes
on the hot `Article` row.

**Stack:** Python · Django REST Framework · Celery · Redis · PostgreSQL (SQLite for local dev) · Docker Compose

## How it works

```
POST /articles/<id>/rate/ ──► PendingRating (one row per user+article) ──► 202 Accepted
                                     │
                     Celery task (scheduled with a 20 s countdown)
                                     │
                  aggregate pending ratings per article (one GROUP BY)
                                     │
         SELECT … FOR UPDATE on the article → apply delta to the running average
                                     │
                    upsert into Rating, clear PendingRating
```

- **Write buffering:** submissions go to a `PendingRating` table (`unique_together` on user+article), so
  re-rating before the batch runs just overwrites the pending vote.
- **Re-rates are deltas, not new votes:** the user's previous rating is stored as `last_rate`, so the
  batch adjusts the average by `(new − old)` and only increments `num_ratings` for first-time voters.
- **Concurrency safety:** the batch runs in a single transaction and locks each article with
  `select_for_update()`, so concurrent workers can't lose updates to the running average.
- **Rating-burst threshold:** `THRESHOLD` in `articles/tasks.py` gates when a pending batch is applied.

## API

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/signup/` | – | Create a user (`username`, `password`) |
| POST | `/api/login/` | – | Returns a token |
| GET | `/api/articles/` | Token | Articles with `num_ratings`, `avg_rating` and the caller's own rating |
| POST | `/articles/<id>/rate/` | Token | Submit `{"rating": 0..5}` → `202 Accepted` |

Authenticate with `Authorization: Token <token>`.

## Run with Docker

```bash
docker compose up --build
```

This starts the API on `localhost:8000`, a Celery worker, PostgreSQL and Redis.

```bash
docker compose exec web python manage.py createsuperuser   # add articles via /admin
```

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
redis-server &                                   # broker
celery -A article_rating worker --loglevel=info &
python manage.py runserver
```

Without `POSTGRES_DB` set, the app uses SQLite.

## Configuration

| Variable | Default |
|---|---|
| `DJANGO_SECRET_KEY` | insecure dev key |
| `DJANGO_DEBUG` | `1` |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` |
| `POSTGRES_DB` / `_USER` / `_PASSWORD` / `_HOST` / `_PORT` | unset → SQLite |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` |

## Tests

```bash
python manage.py test
```
