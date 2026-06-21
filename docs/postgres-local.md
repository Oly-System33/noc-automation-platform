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
SELECT * FROM processed_events ORDER BY created_at DESC;
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

## 10. Run Scheduled Actions Worker

For local testing, the worker can run automatically inside FastAPI.

Set these values in `.env`:

```text
SCHEDULED_ACTION_WORKER_ENABLED=true
SCHEDULED_ACTION_POLL_INTERVAL_SECONDS=5
SCHEDULED_ACTION_BATCH_SIZE=20
SCHEDULED_ACTION_PROCESSING_TIMEOUT_MINUTES=10
SCHEDULED_ACTION_MAX_ATTEMPTS=3
```

Then start the app normally:

```bash
DATABASE_URL=postgresql://noc_engine:noc_engine@localhost:5432/noc_engine \
  .venv/bin/uvicorn app.main:app --reload
```

With that setup, a PROBLEM with `delay_minutes > 0` is scheduled and the same app process polls and executes it after `scheduled_at`.

The worker uses `pending -> processing` before execution to avoid duplicate execution if more than one process sees the same row.
If the app stops while a scheduled action is `processing`, the next startup/worker cycle recovers stale rows:

- `attempt_count < SCHEDULED_ACTION_MAX_ATTEMPTS`: `processing -> pending`
- `attempt_count >= SCHEDULED_ACTION_MAX_ATTEMPTS`: `processing -> failed`

Webhook deduplication is handled by PostgreSQL in `processed_events`. The `events` table still stores every raw webhook received, including duplicates.

For debugging, you can still run the worker manually in another terminal by setting `SCHEDULED_ACTION_WORKER_ENABLED=false` for the app and using:

```bash
DATABASE_URL=postgresql://noc_engine:noc_engine@localhost:5432/noc_engine \
SCHEDULED_ACTION_POLL_INTERVAL_SECONDS=5 \
  .venv/bin/python -m app.services.scheduled_action_worker
```

The worker polls `scheduled_actions` for rows where:

```sql
state = 'pending'
AND scheduled_at <= now()
```

It claims each row as `processing`, checks that the incident is still `open`, and then executes the saved action plan.

When using `uvicorn --reload`, reloads can restart the background worker. The `processing` claim protects execution, but if you are debugging worker behavior, the manual command is easier to observe.

### Delayed Action Without Recovery

1. Set `delay_minutes = 1` in the matching runbook action.
2. Send a matching PROBLEM event.
3. Confirm it is pending:

```sql
SELECT event_id, state, scheduled_at
FROM scheduled_actions
ORDER BY created_at DESC;
```

4. Wait for the worker to process it.
5. Confirm execution:

```sql
SELECT event_id, state, executed_at, error_message
FROM scheduled_actions
ORDER BY created_at DESC;

SELECT event_id, action_type, status, created_at
FROM actions
ORDER BY created_at DESC;
```

### Delayed Action With Recovery Before Execution

1. Send a matching PROBLEM event with `delay_minutes = 1`.
2. Send RECOVERY before the minute expires.
3. Confirm cancellation:

```sql
SELECT event_id, state, cancelled_at, cancel_reason
FROM scheduled_actions
ORDER BY created_at DESC;
```

Expected:

```text
state = cancelled
cancel_reason = recovery_received
```

### Worker Audit Logs

```sql
SELECT level, component, message, details
FROM audit_logs
ORDER BY created_at DESC;
```

## 11. Verify Persistent Deduplication

Send the same PROBLEM webhook twice with the same `event_id`.

Expected:

- `events` has multiple rows for the same `event_id`;
- `processed_events` has one `PROBLEM` row with `received_count > 1`;
- actions or scheduled actions are not duplicated.

Queries:

```sql
SELECT event_id, status, created_at
FROM events
WHERE event_id = 'manual-dedupe-1'
ORDER BY created_at;

SELECT event_id, zabbix_status, state, received_count, first_seen_at, last_seen_at
FROM processed_events
WHERE event_id = 'manual-dedupe-1'
ORDER BY zabbix_status;

SELECT event_id, action_type, status, created_at
FROM actions
WHERE event_id = 'manual-dedupe-1'
ORDER BY created_at;

SELECT event_id, state, dedupe_key, created_at
FROM scheduled_actions
WHERE event_id = 'manual-dedupe-1'
ORDER BY created_at;
```

Send PROBLEM and RECOVERY with the same `event_id`.

Expected:

- `processed_events` has one `PROBLEM` row and one `RECOVERY` row;
- the incident is closed;
- pending scheduled actions are cancelled.

## 12. Docker Compose

The compose file includes a `postgres` service and `postgres_data` volume. To run the full stack:

```bash
docker compose up -d --build
```

To initialize tables inside the app container:

```bash
docker compose exec noc-bot python -m app.db.init_db
```
