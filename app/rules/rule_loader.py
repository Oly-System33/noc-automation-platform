from pathlib import Path
from datetime import datetime, time
from zoneinfo import ZoneInfo
import pandas as pd


RUNBOOKS_PATH = Path("data/runbooks")


class RuleLoader:
    """
    Carga y gestiona reglas desde Excel por cliente.
    Cada cliente tiene su propio archivo runbooks/<cliente>.xlsx
    """

    def __init__(self):
        self.cache = {}

    def _load_client_runbook(self, client: str):

        if client in self.cache:
            return self.cache[client]

        file_path = RUNBOOKS_PATH / f"{client}.xlsx"

        if not file_path.exists():
            raise FileNotFoundError(
                f"No se encontró runbook para cliente: {client}"
            )

        data = {
            "hosts": pd.read_excel(file_path, sheet_name="hosts"),
            "actions": pd.read_excel(file_path, sheet_name="actions"),
            "contacts": pd.read_excel(file_path, sheet_name="contacts"),
            "suppressions": pd.read_excel(file_path, sheet_name="suppressions"),
            "trigger_groups": pd.read_excel(file_path, sheet_name="trigger_groups"),
            "severity_map": pd.read_excel(file_path, sheet_name="severity_map"),
        }

        try:
            data["oncall"] = pd.read_excel(file_path, sheet_name="oncall")
        except ValueError:
            data["oncall"] = None

        self.cache[client] = data

        return data

    def extract_client_and_host(self, full_host: str):

        client, host = full_host.split("/", 1)

        return client.strip(), host.strip()

    def is_host_monitored(self, client: str, host: str):

        data = self._load_client_runbook(client)

        hosts_df = data["hosts"]

        return host in hosts_df["host"].values

    def get_trigger_group(self, client: str, trigger: str):

        data = self._load_client_runbook(client)

        trigger_groups_df = data["trigger_groups"]

        trigger_lower = trigger.lower()

        for _, row in trigger_groups_df.iterrows():

            keyword = str(row["keyword"]).lower()

            if keyword in trigger_lower:
                return row["group"]

        return None

    def is_suppressed(self, client, host, trigger_group):

        data = self._load_client_runbook(client)

        suppressions_df = data["suppressions"]

        now = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))

        current_day = now.strftime("%A").lower()
        current_time = now.time()

        for _, row in suppressions_df.iterrows():

            if row["host"] not in (host, "*"):
                continue

            if row["trigger_group"] not in (trigger_group, "*"):
                continue

            day = str(row["day"]).lower()

            if day != "*" and day != current_day:
                continue

            start = row["start"]
            end = row["end"]

            # Convertir start/end si vienen como string
            if isinstance(start, str):
                start = datetime.strptime(start, "%H:%M:%S").time()

            if isinstance(end, str):
                end = datetime.strptime(end, "%H:%M:%S").time()

            # ventana normal (ej: 09:00 → 18:00)
            if start <= end:
                if start <= current_time <= end:
                    return True

            # ventana overnight (ej: 22:00 → 02:00)
            else:
                if current_time >= start or current_time <= end:
                    return True

        return False

    def get_action(self, client, host, trigger_group):

        data = self._load_client_runbook(client)

        actions_df = data["actions"]

        specific = actions_df[
            (actions_df["host"] == host)
            & (actions_df["trigger_group"] == trigger_group)
        ]

        if not specific.empty:

            action_row = specific.iloc[0].to_dict()

            action_row["action"] = [
                a.strip()
                for a in action_row["action"].split(",")
            ]

            return action_row

        wildcard = actions_df[
            (actions_df["host"] == host)
            & (actions_df["trigger_group"] == "*")
        ]

        if not wildcard.empty:

            action_row = wildcard.iloc[0].to_dict()

            action_row["action"] = [
                a.strip()
                for a in action_row["action"].split(",")
            ]

            return action_row

        return None

    def get_contact(self, client, team):

        data = self._load_client_runbook(client)

        contacts_df = data["contacts"]

        match = contacts_df[contacts_df["team"] == team]

        if match.empty:
            return None

        return match.iloc[0].to_dict()

    def get_oncall_contact(self, client, team):

        data = self._load_client_runbook(client)

        oncall_df = data.get("oncall")

        if oncall_df is None or oncall_df.empty:
            return None

        required_columns = {
            "team",
            "start_date",
            "end_date",
            "start_time",
            "end_time",
        }

        if "day" in oncall_df.columns and not required_columns.issubset(oncall_df.columns):
            print("[ONCALL] legacy day-based format detected")
            return None

        if not required_columns.issubset(oncall_df.columns):
            return None

        now = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))
        current_date = now.date()
        current_time = now.time()

        priorities = [team, "*"]

        for team_match in priorities:

            matches = oncall_df[
                (oncall_df["team"].astype(str).str.strip() == team_match)
            ]

            for _, row in matches.iterrows():

                start_date = self._parse_date(row.get("start_date"))
                end_date = self._parse_date(row.get("end_date"))
                start_time = self._parse_time(row.get("start_time"))
                end_time = self._parse_time(row.get("end_time"))

                if not start_date or not end_date or not start_time or not end_time:
                    continue

                if not start_date <= current_date <= end_date:
                    continue

                if self._is_time_active(current_time, start_time, end_time):
                    return {
                        "team": row.get("team"),
                        "user": row.get("user"),
                        "phone": row.get("phone"),
                        "email": row.get("email"),
                        "telegram": row.get("telegram"),
                        "teams": row.get("teams"),
                    }

        return None

    def _parse_date(self, value):

        if pd.isna(value):
            return None

        if isinstance(value, datetime):
            return value.date()

        value = str(value).strip()

        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None

    def _parse_time(self, value):

        if pd.isna(value):
            return None

        if isinstance(value, time):
            return value

        if isinstance(value, datetime):
            return value.time()

        value = str(value).strip()

        for time_format in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(value, time_format).time()
            except ValueError:
                continue

        return None

    def _is_time_active(self, current_time, start, end):

        if start <= end:
            return start <= current_time <= end

        return current_time >= start or current_time <= end

    def get_jira_priority(self, client, severity):

        data = self._load_client_runbook(client)

        severity_df = data["severity_map"]

        severity_lower = str(severity).lower()

        match = severity_df[
            severity_df["zabbix_severity"].str.lower() == severity_lower
        ]

        if match.empty:
            return "Medium"

        return match.iloc[0]["jira_priority"]


rule_loader = RuleLoader()
