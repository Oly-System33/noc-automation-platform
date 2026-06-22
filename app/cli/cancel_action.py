import argparse

from app.services.persistence_service import persistence_service


def main():

    parser = argparse.ArgumentParser(description="Cancel a pending approval action")
    parser.add_argument("scheduled_action_id", type=int)
    parser.add_argument("--reason", default="manual_cancelled")
    args = parser.parse_args()

    cancelled = persistence_service.cancel_scheduled_action(
        args.scheduled_action_id,
        reason=args.reason,
    )

    if cancelled:
        print(f"Cancelled scheduled_action_id={args.scheduled_action_id}")
        return

    print(f"Cancel failed scheduled_action_id={args.scheduled_action_id}")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
