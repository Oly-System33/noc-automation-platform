import os
import re
import unicodedata
from pathlib import Path
from datetime import datetime, time
from zoneinfo import ZoneInfo
import pandas as pd

from app.services.console import console


RUNBOOKS_PATH = Path(os.getenv("RUNBOOKS_PATH", "data/runbooks"))


ACTION_ALIASES = {
    "jira": "jira",
    "ticket": "jira",
    "issue": "jira",
    "calls": "calls",
    "call": "calls",
    "cal": "calls",
    "llamada": "calls",
    "llamadas": "calls",
    "phone": "calls",
    "vonage": "calls",
    "email": "email",
    "mail": "email",
    "correo": "email",
    "telegram": "telegram",
    "tg": "telegram",
    "teams": "teams",
    "msteams": "teams",
    "microsoft teams": "teams",
}


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

        try:
            data["holidays"] = pd.read_excel(file_path, sheet_name="holidays")
        except ValueError:
            data["holidays"] = None
            print("[RUNBOOK] Hoja holidays no encontrada; feriados deshabilitados")

        self.cache[client] = data

        return data

    def extract_client_and_host(self, full_host: str):

        host_value = str(full_host).strip() if full_host is not None else ""

        if not host_value:
            print(
                f"[{console.level('WARNING')}] "
                "Invalid or empty host received, using unknown/unknown"
            )
            return "unknown", "unknown"

        if "/" not in host_value:
            print(
                f"[{console.level('WARNING')}] "
                "Host without client received, using client=unknown"
            )
            return "unknown", host_value or "unknown"

        client, host = host_value.split("/", 1)
        client = client.strip() or "unknown"
        host = host.strip() or "unknown"

        if client == "unknown":
            print(
                f"[{console.level('WARNING')}] "
                "Host without client received, using client=unknown"
            )

        return client, host

    def is_host_monitored(self, client: str, host: str):

        data = self._load_client_runbook(client)

        hosts_df = data["hosts"]

        host = self._clean_value(host)

        for _, row in hosts_df.iterrows():

            if self._clean_value(row.get("host")) == host:

                return True

        return False

    def get_host_group(self, client: str, host: str):

        data = self._load_client_runbook(client)

        hosts_df = data["hosts"]

        if "host_group" not in hosts_df.columns:

            return None

        host = self._clean_value(host)

        for _, row in hosts_df.iterrows():

            if self._clean_value(row.get("host")) == host:

                return self._clean_value(row.get("host_group"))

        return None

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

        host = self._clean_value(host)
        trigger_group = self._clean_value(trigger_group)
        host_group = self.get_host_group(client, host)

        priorities = [
            ("host", host, trigger_group),
            ("host", host, "*"),
        ]

        if host_group:

            priorities.extend([
                ("group", host_group, trigger_group),
                ("group", host_group, "*"),
            ])

        priorities.extend([
            ("all", "*", trigger_group),
            ("all", "*", "*"),
        ])

        for scope_type, scope_value, trigger_match in priorities:

            for _, row in actions_df.iterrows():

                if self._action_row_matches(
                    row,
                    scope_type,
                    scope_value,
                    trigger_match,
                ):

                    return self._format_action_row(row)

        return None

    def _action_row_matches(self, row, scope_type, scope_value, trigger_group):

        row_scope_type, row_scope_value = self._get_action_scope(row)

        return (
            row_scope_type == scope_type
            and row_scope_value == scope_value
            and self._clean_value(row.get("trigger_group")) == trigger_group
        )

    def _get_action_scope(self, row):

        has_new_scope = (
            "scope_type" in row.index
            and "scope_value" in row.index
            and self._clean_value(row.get("scope_type"))
            and self._clean_value(row.get("scope_value"))
        )

        if has_new_scope:

            return (
                self._clean_value(row.get("scope_type")).lower(),
                self._clean_value(row.get("scope_value")),
            )

        return "host", self._clean_value(row.get("host"))

    def _format_action_row(self, row):

        action_row = row.to_dict()
        action_row["action_raw"] = action_row.get("action")
        action_row["delay_minutes_raw"] = action_row.get("delay_minutes")
        action_row["delay_minutes_invalid"] = self.is_invalid_delay_minutes(
            action_row.get("delay_minutes")
        )
        action_row["delay_minutes"] = self.parse_delay_minutes(
            action_row.get("delay_minutes")
        )

        actions, invalid_actions = self.normalize_actions(action_row.get("action"))
        action_row["action"] = actions
        action_row["invalid_actions"] = invalid_actions

        return action_row

    def normalize_actions(self, value):

        if pd.isna(value):

            return [], []

        raw_actions = [
            action.strip()
            for action in re.split(r"[,;|]", str(value))
            if action.strip()
        ]
        actions = []
        invalid_actions = []

        for raw_action in raw_actions:

            action = self.normalize_action_name(raw_action)

            if not action:

                invalid_actions.append(raw_action)
                continue

            if action not in actions:

                actions.append(action)

        return actions, invalid_actions

    def normalize_action_name(self, value):

        if pd.isna(value):

            return None

        normalized = unicodedata.normalize("NFKD", str(value).strip().lower())
        normalized = "".join(
            char for char in normalized
            if not unicodedata.combining(char)
        )
        normalized = " ".join(normalized.split())

        if not normalized:

            return None

        return ACTION_ALIASES.get(normalized)

    def parse_delay_minutes(self, value):

        if pd.isna(value):

            return 0

        value = str(value).strip()

        if not value:

            return 0

        try:
            delay_minutes = int(float(value))
        except ValueError:
            return 0

        if delay_minutes < 0:

            return 0

        return delay_minutes

    def is_invalid_delay_minutes(self, value):

        if pd.isna(value):

            return False

        value = str(value).strip()

        if not value:

            return False

        try:
            float(value)
        except ValueError:
            return True

        return False

    def _clean_value(self, value):

        if pd.isna(value):

            return None

        return str(value).strip()

    def get_contact(self, client, team):

        data = self._load_client_runbook(client)

        contacts_df = data["contacts"]

        match = contacts_df[contacts_df["team"] == team]

        if match.empty:
            return None

        return match.iloc[0].to_dict()

    def get_oncall_contact(self, client, team, now=None):

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
            print(f"[{console.cyan('ONCALL')}] legacy day-based format detected")
            return None

        if not required_columns.issubset(oncall_df.columns):
            return None

        now = now or datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))
        current_date = now.date()
        current_time = now.time()
        holiday = self._get_holiday(client, current_date)
        is_weekend = self._is_weekend(current_date)

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

                print(
                    f"[{console.cyan('ONCALL')}] Fila activa encontrada | "
                    f"team={team_match} | date={current_date}"
                )

                if holiday:
                    print(
                        f"[{console.cyan('ONCALL')}] Guardia 24h por feriado | "
                        f"team={team_match} | date={current_date} | "
                        f"holiday={holiday.get('name')}"
                    )
                    return self._format_oncall_contact(
                        row,
                        reason="holiday_24h",
                        holiday=holiday,
                    )

                if is_weekend:
                    print(
                        f"[{console.cyan('ONCALL')}] Guardia 24h por fin de semana | "
                        f"team={team_match} | date={current_date}"
                    )
                    return self._format_oncall_contact(
                        row,
                        reason="weekend_24h",
                    )

                if self._is_time_active(current_time, start_time, end_time):
                    print(
                        f"[{console.cyan('ONCALL')}] Guardia por ventana horaria | "
                        f"team={team_match} | time={current_time.strftime('%H:%M')} | "
                        f"window={start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}"
                    )
                    return self._format_oncall_contact(
                        row,
                        reason="business_day_time_window",
                    )

        print(
            f"[{console.cyan('ONCALL')}] Sin guardia activa | "
            f"team={team} | date={current_date} | time={current_time.strftime('%H:%M')}"
        )
        return None

    def _format_oncall_contact(self, row, reason=None, holiday=None):

        return {
            "team": row.get("team"),
            "user": row.get("user"),
            "phone": row.get("phone"),
            "email": row.get("email"),
            "telegram": row.get("telegram"),
            "teams": row.get("teams"),
            "oncall_reason": reason,
            "holiday_name": holiday.get("name") if holiday else None,
        }

    def _get_holiday(self, client, current_date):

        data = self._load_client_runbook(client)
        holidays_df = data.get("holidays")

        if holidays_df is None or holidays_df.empty:

            return None

        if "date" not in holidays_df.columns:
            print("[RUNBOOK] Hoja holidays sin columna date; feriados deshabilitados")
            return None

        for _, row in holidays_df.iterrows():

            holiday_date = self._parse_date(row.get("date"))

            if not holiday_date:
                continue

            if holiday_date == current_date:
                return {
                    "date": holiday_date,
                    "name": self._clean_value(row.get("name")) if "name" in row.index else None,
                }

        return None

    def _is_weekend(self, current_date):

        return current_date.weekday() >= 5

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
