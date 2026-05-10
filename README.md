# NOC Automation Engine

FastAPI-based NOC Automation Platform for Zabbix events, runbook-based routing, Telegram, Vonage Voice, Jira, email and Teams notifications.

## EC2 Docker Compose Deployment

Target public URL for the current demo EC2 instance:

```text
http://3.89.189.230:8000
```

Expected host structure:

```text
/opt/noc-engine/
├── .env
├── docker-compose.yml
├── private.key
└── runbooks/
    └── Banco X.xlsx
```

The `.env`, Vonage private key and Excel runbooks are mounted from the host. They are not embedded in the Docker image, so they can be changed without rebuilding the image.

## Required Environment

Create `/opt/noc-engine/.env` from `.env.example` and set at least:

```text
PUBLIC_BASE_URL=http://3.89.189.230:8000
RUNBOOKS_PATH=/app/runbooks
TELEGRAM_BOT_TOKEN_JIRA=replace-me
TELEGRAM_BOT_TOKEN_NOC=replace-me
VONAGE_APPLICATION_ID=replace-me
VONAGE_PRIVATE_KEY_PATH=/app/private.key
VONAGE_FROM_NUMBER=replace-me
VONAGE_API_BASE_URL=https://api.nexmo.com/v1/calls
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USER=replace-me
SMTP_PASSWORD=replace-me
JIRA_URL=https://example.atlassian.net
JIRA_EMAIL=replace-me
JIRA_API_TOKEN=replace-me
JIRA_ISSUE_TYPE=Task
```

## First Deployment

```bash
sudo mkdir -p /opt/noc-engine/runbooks
cd /opt/noc-engine
docker compose up -d --build
```

## Restart After Config Changes

Use this after editing `.env`, replacing `private.key`, or changing runbooks:

```bash
cd /opt/noc-engine
docker compose restart
```

## Update Application Code

```bash
cd /opt/noc-engine
git pull
docker compose up -d --build
```

## Logs

```bash
cd /opt/noc-engine
docker compose logs -f noc-bot
```

## Runbooks Without Rebuild

Place or replace Excel files directly in the host runbooks directory:

```bash
cp "Banco X.xlsx" /opt/noc-engine/runbooks/
cd /opt/noc-engine
docker compose restart
```

Inside the container the runbooks are available at `/app/runbooks` through the `RUNBOOKS_PATH` environment variable.

For local development, if `RUNBOOKS_PATH` is not set, the app still uses `data/runbooks`.

## Public Webhooks

Configure external systems with these URLs:

```text
Zabbix:   http://3.89.189.230:8000/zabbix/webhook
Telegram: http://3.89.189.230:8000/bot/webhook
Vonage answer URL: http://3.89.189.230:8000/vonage/answer
Vonage input URL:  http://3.89.189.230:8000/vonage/input
Vonage event URL:  http://3.89.189.230:8000/vonage/event
```

Vonage call creation uses `PUBLIC_BASE_URL` dynamically to generate callback URLs.

## Manual Checks

```bash
curl http://3.89.189.230:8000/docs
```

```bash
curl -X POST http://3.89.189.230:8000/zabbix/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "host": "Banco X/server01",
    "trigger": "CPU high",
    "severity": "High",
    "status": 1,
    "event_id": "demo-001",
    "timestamp": "2026-05-10T12:00:00Z"
  }'
```

## Local Development

```bash
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
