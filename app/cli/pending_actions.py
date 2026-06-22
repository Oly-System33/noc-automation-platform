from app.services.persistence_service import persistence_service
from app.services.console import console


def main():

    actions = persistence_service.list_pending_approval_actions()

    if not actions:
        print(f"[{console.cyan('INFO')}] No pending approval actions found")
        return

    for action in actions:
        action_id = action.get("id")
        approve_command = f".venv/bin/python -m app.cli.approve_action {action_id}"
        cancel_command = f".venv/bin/python -m app.cli.cancel_action {action_id}"
        print(
            f"[{console.yellow('PENDING_APPROVAL')}] "
            + " | ".join([
                console.orange(f"id={action_id}"),
                f"event_id={console.cyan(action.get('event_id'))}",
                f"client={action.get('client')}",
                f"host={action.get('host')}",
                f"target={action.get('target')}",
                f"pre_target={action.get('pre_target')}",
                f"actions={','.join(action.get('actions') or [])}",
                f"created_at={action.get('created_at')}",
            ])
        )
        print(f"  Approve: {console.orange(approve_command)}")
        print(f"  Cancel pending action only: {console.orange(cancel_command)}")


if __name__ == "__main__":
    main()
