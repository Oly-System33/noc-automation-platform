# AGENTS.md

## Project context

This repository is a NOC incident automation platform running on Python
3.13.11. A local virtual environment already exists at `.venv`; do not create
another one and install only the minimum required dependencies.

The current event pipeline is:

```text
Zabbix webhook
-> ZabbixEvent
-> EventProcessor
-> RuleEngine
-> RuleLoader using Excel runbooks
-> ActionDispatcher
-> email, Telegram, Teams, Jira, and Vonage Voice handlers
```

## Stack

```text
Python
FastAPI
SQLAlchemy
PostgreSQL
Pydantic
unittest
Excel runbooks
```

## Architecture

Prefer composition over inheritance. Keep services and integration classes
small, explicit, and consistent with the existing code. Do not introduce a
framework, plugin system, dependency injection container, repository pattern,
or async redesign. Make the smallest safe production-grade change and do not
refactor unrelated code.

Do not rename public interfaces or alter the RuleEngine flow unless a task
explicitly requires it. Do not change Jira, email, Telegram, Teams, Zabbix,
Vonage, or Excel parsing logic as part of unrelated work.

## Persistence

SQLAlchemy persists the operational state in PostgreSQL using these tables:

```text
events
incidents
actions
audit_logs
processed_events
scheduled_actions
call_flows
call_attempts
```

Incident, scheduled action, call flow, and call attempt state must not be
described as exclusively in-memory. Some runtime coordination may still use
process memory, but PostgreSQL is the source used by the dashboard backend.

## Scheduled actions

The persisted scheduled action states are:

```text
pending
pending_approval
paused
processing
executed
failed
cancelled
```

Manual pause and resume use direct transitions:

```text
pending -> paused
paused -> processing
```

Resume means immediate execution and must not return an action to `pending`.
The API and CLI must reuse the existing persistence, worker, and executor
services instead of duplicating worker logic.

## Dashboard backend MVP

The backend includes:

```text
DashboardQueryService
dashboard schemas and visible status resolvers
summary API
incidents API
operations API
approvals API
pause API
resume API
approval API
CORS configuration
dashboard demo data
```

Keep internal workflow states separate from dashboard-visible states. The
frontend must use the API and must never access PostgreSQL directly. Dashboard
responses must not expose secrets, contact payloads, phone numbers, or other
integration credentials.

## External integrations and runbooks

Do not hardcode secrets or destination phone numbers. A call destination must
come from the existing runbook contact dictionary as `contact["phone"]`, never
from `.env`. `PUBLIC_BASE_URL` is the public callback base URL used by Vonage.

Do not modify the runbook structure, add an Excel sheet, or implement dynamic
on-call scheduling without an explicit task. Do not modify customer runbooks as
part of application changes.

## Future modification rules

- Do not duplicate scheduled worker or execution logic.
- Reuse business services from API and CLI entry points.
- Do not allow frontend access to PostgreSQL.
- Do not expose secrets or contact details.
- Keep tests in the existing `unittest` suite.
- Do not modify runbooks without an explicit task.
- Do not add Redis without a later architectural decision.
- Keep internal states and visible dashboard states separate.
- Do not modify unrelated dependencies.

The app must continue to start with `uvicorn app.main:app --reload`, and a fake
Zabbix event must remain testable through `POST /zabbix/webhook`.

## Next stage

```text
Frontend dashboard MVP
```

No frontend stack has been selected yet.
