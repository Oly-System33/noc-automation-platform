# AGENTS.md

## Project context

This is a Python/FastAPI NOC Automation Platform.

The project uses Python 3.13.11.

A local virtual environment already exists in the repository as:

.venv

Do not create a new virtual environment.

Use the existing environment and install only the minimum required dependencies.

Current pipeline:

Zabbix webhook
→ ZabbixEvent
→ EventProcessor
→ RuleEngine
→ RuleLoader using Excel runbooks
→ ActionDispatcher
→ channel handlers: email, telegram, teams, jira, calls

The "calls" action currently exists as a placeholder in ActionDispatcher and must be implemented using Twilio Voice.

This is an automation project for NOC incident handling.

## Architecture style

Prefer composition over inheritance.

Keep classes small and explicit.

Use service/integration classes, consistent with the current project style.

Do not introduce unnecessary abstractions.

Do not introduce a framework, plugin system, dependency injection container, repository pattern, or async redesign.

Use simple Python code.

## Critical constraints

Do not refactor unrelated code.

Do not rename existing files, classes, methods, folders, or public interfaces unless explicitly requested.

Do not change the existing RuleEngine flow unless strictly necessary.

Do not change Jira, Email, Telegram, Teams, Zabbix, or Excel parsing logic except where required to wire the Twilio calls action.

Do not modify the runbook structure.

Do not implement dynamic on-call scheduling yet.

Do not add a new Excel sheet yet.

Do not hardcode the destination phone number.

Do not read the destination phone number from .env.

The destination phone number must come from the existing runbook contact dictionary:

contact["phone"]

The user will manually place the test phone number in the existing runbook contacts sheet.

Make the smallest safe production-grade change.

## Implementation goal

Implement real Twilio Voice calls for the existing "calls" action.

Current expected behavior:

When the RuleEngine dispatches action "calls", ActionDispatcher._action_calls(event, contact) must:

1. Resolve the phone number from contact["phone"].
2. Build a voice alert message from the event.
3. Trigger an outbound Twilio call to that phone.
4. The call must play the alert message.
5. The call must offer IVR:
   - Press 1 to confirm receipt.
   - Press 2 to repeat the message.

## Runtime/environment

Use these environment variables:

TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN
TWILIO_FROM_NUMBER
PUBLIC_BASE_URL

Do not hardcode secrets.

Do not use TWILIO_TEST_PHONE_NUMBER in the real project integration.

The called phone number must come from the runbook contact.

PUBLIC_BASE_URL must be the public HTTPS URL used by Twilio to reach FastAPI callbacks.

## Dependencies

Use the official Twilio Python SDK.

If missing, install only:

twilio
python-multipart

Do not modify unrelated dependencies.

If requirements.txt exists, update it only as needed.

## Preferred file layout

Add new files only if needed:

app/integrations/twilio_voice.py
app/services/call_service.py
app/api/twilio_webhook.py

Modify existing files only if needed:

app/main.py
app/services/action_dispatcher.py

## Twilio requirements

Use TwiML with:

VoiceResponse
Gather
Redirect

Required endpoints:

GET or POST /twilio/voice
POST /twilio/ivr

/twilio/voice must return application/xml.

/twilio/ivr must receive Digits from form data.

Store active call events in memory for now, keyed by event_id.

This in-memory store is acceptable for the current demo.

## Testing requirements

Do not create a large test framework unless requested.

The app must still start with:

uvicorn app.main:app --reload

Manual test must be possible by sending a fake Zabbix PROBLEM event to:

POST /zabbix/webhook

The fake event should trigger the normal existing pipeline.

The runbook must determine the action "calls" and the target contact.

The target contact must contain a phone field.

## Output requirements

Before editing, explain the planned file changes.

After editing, show:

1. files changed
2. commands to install dependencies
3. environment variables needed
4. commands to run
5. curl/manual test through /zabbix/webhook
6. git status
7. proposed git add command
8. proposed git commit command

Do not commit automatically.