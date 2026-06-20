# PostgreSQL Local Setup

This project can run the Python/FastAPI app locally while PostgreSQL runs in Docker.

## 1. Start PostgreSQL Locally

```bash
docker run --name noc-postgres \
  -e POSTGRES_DB=noc_engine \
  -e POSTGRES_USER=noc_engine \
  -e POSTGRES_PASSWORD=noc_engine \
  -p 5432:5432 \
  -d postgres:16
```

If the container already exists:

```bash
docker start noc-postgres
```

## 2. Local App Database URL

Use this when the app runs locally with `uvicorn` and PostgreSQL runs in Docker:

```text
DATABASE_URL=postgresql://noc_engine:noc_engine@localhost:5432/noc_engine
```

## 3. Docker Compose Database URL

Use this when the app and PostgreSQL both run inside Docker Compose:

```text
DATABASE_URL=postgresql://noc_engine:noc_engine@postgres:5432/noc_engine
```

`DATABASE_URL` has priority. If it is not set, the app builds the connection from:

```text
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=noc_engine
POSTGRES_USER=noc_engine
POSTGRES_PASSWORD=noc_engine
```

## 4. Install Dependencies

```bash
.venv/bin/pip install -r requirements.txt
```

## 5. Create Tables

```bash
DATABASE_URL=postgresql://noc_engine:noc_engine@localhost:5432/noc_engine \
  .venv/bin/python -m app.db.init_db
```

## 6. Run The App Locally

```bash
DATABASE_URL=postgresql://noc_engine:noc_engine@localhost:5432/noc_engine \
  .venv/bin/uvicorn app.main:app --reload
```

## 7. Open psql

```bash
docker exec -it noc-postgres psql -U noc_engine -d noc_engine
```

## 8. Verify Data

```sql
SELECT * FROM events ORDER BY created_at DESC;
SELECT * FROM incidents ORDER BY created_at DESC;
SELECT * FROM actions ORDER BY created_at DESC;
SELECT * FROM audit_logs ORDER BY created_at DESC;
SELECT * FROM scheduled_actions ORDER BY created_at DESC;
```

## 9. Test Delayed Actions

In the runbook `actions` sheet, add or update the optional column:

```text
delay_minutes
```

Use `1` for a local scheduling test.

Then send a PROBLEM event that matches that action rule. Expected result:

- no email, Jira, calls, Telegram or Teams action runs immediately;
- one row is inserted into `scheduled_actions`;
- `state` is `pending`;
- `scheduled_at` is approximately `created_at + 1 minute`;
- `events`, `incidents` and `audit_logs` are still updated.

Verify with:

```sql
SELECT event_id, actions, target, state, scheduled_at, created_at
FROM scheduled_actions
ORDER BY created_at DESC;

SELECT event_id, current_status, opened_at
FROM incidents
ORDER BY created_at DESC;

SELECT level, component, message, details
FROM audit_logs
ORDER BY created_at DESC;
```

Set `delay_minutes` to `0` or leave it empty to execute actions immediately as before.

## 10. Docker Compose

The compose file includes a `postgres` service and `postgres_data` volume. To run the full stack:

```bash
docker compose up -d --build
```

To initialize tables inside the app container:

```bash
docker compose exec noc-bot python -m app.db.init_db
```
