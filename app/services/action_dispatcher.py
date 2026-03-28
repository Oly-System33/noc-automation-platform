class ActionDispatcher:

    def __init__(self):
        self.ACTION_MAP = {
            "email": self._action_email,
            "telegram": self._action_telegram,
            "calls": self._action_calls,
            "jira": self._action_jira,
            "teams": self._action_teams,
        }

    def dispatch(self, event, actions: list, contacts: list):

        print("\n[DISPATCHER] Starting action dispatch...")
        print(
            f"[EVENT] {event.event_id} | "
            f"{event.status} | "
            f"{event.host}"
        )

        for action in actions:

            handler = self.ACTION_MAP.get(action)

            if not handler:
                print(f"[WARNING] Unknown action type: {action}")
                continue

            try:
                self._dispatch_single_action(
                    handler,
                    event,
                    contacts
                )

            except Exception as e:
                print(
                    f"[ERROR] Failed executing action "
                    f"'{action}': {e}"
                )

    def _dispatch_single_action(self, handler, event, contacts):

        handler(event, contacts)

    # ========================
    # ACTION HANDLERS
    # ========================

    def _action_email(self, event, contacts):

        for contact in contacts:
            print(
                f"[DISPATCH][EMAIL] → {contact} | "
                f"{event.host} | "
                f"{event.trigger} | "
                f"{event.status}"
            )

    def _action_telegram(self, event, contacts):

        for contact in contacts:
            print(
                f"[DISPATCH][TELEGRAM] → {contact} | "
                f"{event.host} | "
                f"{event.trigger} | "
                f"{event.status}"
            )

    def _action_calls(self, event, contacts):

        for contact in contacts:
            print(
                f"[DISPATCH][CALL] → {contact} | "
                f"{event.host} | "
                f"{event.trigger} | "
                f"{event.status}"
            )

    def _action_jira(self, event, contacts):

        for contact in contacts:
            print(
                f"[DISPATCH][JIRA] → {contact} | "
                f"{event.host} | "
                f"{event.trigger} | "
                f"{event.status}"
            )

    def _action_teams(self, event, contacts):

        for contact in contacts:
            print(
                f"[DISPATCH][TEAMS] → {contact} | "
                f"{event.host} | "
                f"{event.trigger} | "
                f"{event.status}"
            )
