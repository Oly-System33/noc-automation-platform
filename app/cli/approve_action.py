import argparse

from app.services.scheduled_action_worker import ScheduledActionWorker


def main():

    parser = argparse.ArgumentParser(description="Approve and execute a pending action")
    parser.add_argument("scheduled_action_id", type=int)
    args = parser.parse_args()

    result = ScheduledActionWorker().approve_scheduled_action(args.scheduled_action_id)

    if result.get("success"):
        print(f"Approved scheduled_action_id={args.scheduled_action_id}")
        return

    print(
        f"Approval failed scheduled_action_id={args.scheduled_action_id} "
        f"error={result.get('error')}"
    )
    raise SystemExit(1)


if __name__ == "__main__":
    main()
