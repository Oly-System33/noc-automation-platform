from app.services.persistence_service import persistence_service


def main():

    actions = persistence_service.list_pending_approval_actions()

    if not actions:
        print("No pending approval actions found")
        return

    for action in actions:
        print(
            " | ".join([
                f"id={action.get('id')}",
                f"event_id={action.get('event_id')}",
                f"client={action.get('client')}",
                f"host={action.get('host')}",
                f"target={action.get('target')}",
                f"pre_target={action.get('pre_target')}",
                f"actions={','.join(action.get('actions') or [])}",
                f"created_at={action.get('created_at')}",
            ])
        )


if __name__ == "__main__":
    main()
