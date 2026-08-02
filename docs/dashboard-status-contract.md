# Dashboard Status Contract

## Internal And Visible States

The automation engine persists detailed internal states for incidents, processed
events, scheduled actions, and call flows. The dashboard exposes a smaller,
stable set of visible states so clients do not need to reproduce workflow rules.

The visible states are:

```text
active
scheduled
paused
pending_approval
executing
waiting_confirmation
retry_scheduled
manual_required
stuck
failed
cancelled
closed
```

## Precedence

When more than one internal state applies to an incident, the resolver uses
this order:

```text
closed
stuck
failed
pending_approval
manual_required
waiting_confirmation
retry_scheduled
executing
paused
scheduled
cancelled
active
```

A processing event or scheduled action is `stuck` when its
`processing_started_at` is equal to or earlier than the configured timeout
cutoff. The exact timeout boundary is therefore considered stuck.

## Scheduled Versus Paused

`scheduled` means a scheduled action is in the internal `pending` state and is
waiting for automatic execution. A future `scheduled_at` does not make an
action paused.

`paused` means an operator explicitly changed the internal action state to
`paused`. It is never inferred from time. The existing resume operation uses
the direct transition:

```text
paused -> processing
```

It does not return the action to `pending`.

## Resolver Scope

`resolve_dashboard_status` is a side-effect-free state-resolution function. It
does not query PostgreSQL, import SQLAlchemy, read environment variables, or
call an external service. Callers provide the relevant internal states and
timestamps. If `now` is omitted, the resolver uses the current UTC time. All
datetime comparisons are normalized to UTC.

## Read-Only Query Service

`DashboardQueryService` builds dashboard response models from these tables:

```text
incidents
events
processed_events
scheduled_actions
call_flows
actions
```

`IncidentRecord.event_id` is the anchor. Related rows are loaded with grouped
`event_id IN (...)` queries and organized in memory. The service never executes
a related query inside the incident loop, so the number of queries does not
grow with the number of returned incidents.

The representative scheduled action is selected by operational precedence:

```text
stuck processing
failed
pending_approval
processing
paused
pending
cancelled
executed
```

Equal states are resolved by their best state-specific timestamp and then by
the highest record ID. All scheduled states are still passed to
`resolve_dashboard_status`, so selecting one representative row does not hide
a higher-priority operation.

The service is read-only. It does not commit, update workflow state, execute an
integration, or expose contact payloads and phone numbers. Database failures
raise a controlled internal exception instead of returning an empty dashboard.

The dashboard HTTP API exposes summary, incident, operation, and approval
queries through this service. Workflow mutations such as pause, resume, and
approval reuse the existing scheduled action business services.
