import unittest
from datetime import datetime, timezone

import pandas as pd

from app.rules.rule_loader import RuleLoader


class RuleLoaderGetActionTest(unittest.TestCase):

    def setUp(self):
        self.loader = RuleLoader()

    def load_runbook(self, hosts, actions):
        self.loader.cache["client"] = {
            "hosts": pd.DataFrame(hosts),
            "actions": pd.DataFrame(actions),
        }

    def test_legacy_exact_host_and_trigger_group(self):
        self.load_runbook(
            hosts=[{"host": "server01"}],
            actions=[{
                "host": "server01",
                "trigger_group": "availability",
                "action": "email,calls",
                "target": "guardia_msp",
            }],
        )

        action = self.loader.get_action("client", "server01", "availability")

        self.assertEqual(action["target"], "guardia_msp")
        self.assertEqual(action["action"], ["email", "calls"])

    def test_legacy_host_wildcard_trigger_group(self):
        self.load_runbook(
            hosts=[{"host": "server01"}],
            actions=[{
                "host": "server01",
                "trigger_group": "*",
                "action": "email",
                "target": "baseline",
            }],
        )

        action = self.loader.get_action("client", "server01", "high_cpu")

        self.assertEqual(action["target"], "baseline")
        self.assertEqual(action["action"], ["email"])

    def test_new_format_host_exact_wins_over_group(self):
        self.load_runbook(
            hosts=[{"host": "server01", "host_group": "grupo_llamada"}],
            actions=[
                {
                    "scope_type": "group",
                    "scope_value": "grupo_llamada",
                    "trigger_group": "availability",
                    "action": "email",
                    "target": "grupo",
                },
                {
                    "scope_type": "host",
                    "scope_value": "server01",
                    "trigger_group": "availability",
                    "action": "calls,email",
                    "target": "host",
                },
            ],
        )

        action = self.loader.get_action("client", "server01", "availability")

        self.assertEqual(action["target"], "host")
        self.assertEqual(action["action"], ["calls", "email"])

    def test_new_format_host_wildcard_trigger(self):
        self.load_runbook(
            hosts=[{"host": "server01", "host_group": "grupo_llamada"}],
            actions=[{
                "scope_type": "host",
                "scope_value": "server01",
                "trigger_group": "*",
                "action": "email",
                "target": "host_wildcard",
            }],
        )

        action = self.loader.get_action("client", "server01", "availability")

        self.assertEqual(action["target"], "host_wildcard")

    def test_new_format_group_exact_wins_over_all(self):
        self.load_runbook(
            hosts=[{"host": "server01", "host_group": "grupo_llamada"}],
            actions=[
                {
                    "scope_type": "all",
                    "scope_value": "*",
                    "trigger_group": "availability",
                    "action": "email",
                    "target": "global",
                },
                {
                    "scope_type": "group",
                    "scope_value": "grupo_llamada",
                    "trigger_group": "availability",
                    "action": "calls",
                    "target": "grupo",
                },
            ],
        )

        action = self.loader.get_action("client", "server01", "availability")

        self.assertEqual(action["target"], "grupo")

    def test_new_format_group_wildcard_trigger(self):
        self.load_runbook(
            hosts=[{"host": "server01", "host_group": "grupo_llamada"}],
            actions=[{
                "scope_type": "group",
                "scope_value": "grupo_llamada",
                "trigger_group": "*",
                "action": "email",
                "target": "grupo_wildcard",
            }],
        )

        action = self.loader.get_action("client", "server01", "availability")

        self.assertEqual(action["target"], "grupo_wildcard")

    def test_new_format_all_exact_trigger_wins_over_all_wildcard(self):
        self.load_runbook(
            hosts=[{"host": "server01", "host_group": "grupo_mail"}],
            actions=[
                {
                    "scope_type": "all",
                    "scope_value": "*",
                    "trigger_group": "*",
                    "action": "email",
                    "target": "global_wildcard",
                },
                {
                    "scope_type": "all",
                    "scope_value": "*",
                    "trigger_group": "high_cpu",
                    "action": "jira,email",
                    "target": "global_exact",
                },
            ],
        )

        action = self.loader.get_action("client", "server01", "high_cpu")

        self.assertEqual(action["target"], "global_exact")
        self.assertEqual(action["action"], ["jira", "email"])

    def test_new_format_all_wildcard_trigger(self):
        self.load_runbook(
            hosts=[{"host": "server01", "host_group": "grupo_mail"}],
            actions=[{
                "scope_type": "all",
                "scope_value": "*",
                "trigger_group": "*",
                "action": "email",
                "target": "global_wildcard",
            }],
        )

        action = self.loader.get_action("client", "server01", "availability")

        self.assertEqual(action["target"], "global_wildcard")

    def test_no_match_returns_none(self):
        self.load_runbook(
            hosts=[{"host": "server01", "host_group": "grupo_mail"}],
            actions=[{
                "scope_type": "host",
                "scope_value": "server02",
                "trigger_group": "availability",
                "action": "email",
                "target": "baseline",
            }],
        )

        self.assertIsNone(self.loader.get_action("client", "server01", "high_cpu"))

    def test_values_are_stripped_and_nan_host_group_is_ignored(self):
        self.load_runbook(
            hosts=[{"host": " server01 ", "host_group": float("nan")}],
            actions=[{
                "scope_type": " host ",
                "scope_value": " server01 ",
                "trigger_group": " availability ",
                "action": " email, calls ",
                "target": "guardia_msp",
            }],
        )

        action = self.loader.get_action("client", "server01", "availability")

        self.assertEqual(action["action"], ["email", "calls"])

    def test_actions_are_normalized_from_aliases_and_mixed_case(self):
        self.load_runbook(
            hosts=[{"host": "server01"}],
            actions=[{
                "host": "server01",
                "trigger_group": "availability",
                "action": "JIRA, Calls, mail, tg, msteams",
                "target": "guardia_msp",
            }],
        )

        action = self.loader.get_action("client", "server01", "availability")

        self.assertEqual(
            action["action"],
            ["jira", "calls", "email", "telegram", "teams"],
        )
        self.assertEqual(action["invalid_actions"], [])

    def test_actions_support_semicolon_and_pipe_separators(self):
        self.load_runbook(
            hosts=[{"host": "server01"}],
            actions=[{
                "host": "server01",
                "trigger_group": "availability",
                "action": "ticket;llamada|correo",
                "target": "guardia_msp",
            }],
        )

        action = self.loader.get_action("client", "server01", "availability")

        self.assertEqual(action["action"], ["jira", "calls", "email"])

    def test_actions_remove_duplicates_preserving_order(self):
        self.load_runbook(
            hosts=[{"host": "server01"}],
            actions=[{
                "host": "server01",
                "trigger_group": "availability",
                "action": "calls,CALLS,call,jira,ticket",
                "target": "guardia_msp",
            }],
        )

        action = self.loader.get_action("client", "server01", "availability")

        self.assertEqual(action["action"], ["calls", "jira"])

    def test_optional_approval_columns_are_normalized(self):
        self.load_runbook(
            hosts=[{"host": "server01"}],
            actions=[{
                "host": "server01",
                "trigger_group": "availability",
                "action": "calls,email",
                "target": "guardia_msp",
                "approval_when": "no-oncall",
                "pre_actions": "telegram;teams",
                "pre_target": "noc",
            }],
        )

        action = self.loader.get_action("client", "server01", "availability")

        self.assertEqual(action["approval_when"], "no_oncall")
        self.assertEqual(action["pre_actions"], ["telegram", "teams"])
        self.assertEqual(action["pre_target"], "noc")

    def test_missing_approval_columns_keep_legacy_defaults(self):
        self.load_runbook(
            hosts=[{"host": "server01"}],
            actions=[{
                "host": "server01",
                "trigger_group": "availability",
                "action": "email",
                "target": "baseline",
            }],
        )

        action = self.loader.get_action("client", "server01", "availability")

        self.assertEqual(action["approval_when"], "never")
        self.assertEqual(action["pre_actions"], [])
        self.assertIsNone(action["pre_target"])

    def test_actions_skip_unknown_values_and_track_invalid_actions(self):
        self.load_runbook(
            hosts=[{"host": "server01"}],
            actions=[{
                "host": "server01",
                "trigger_group": "availability",
                "action": "jira,calll,sms",
                "target": "guardia_msp",
            }],
        )

        action = self.loader.get_action("client", "server01", "availability")

        self.assertEqual(action["action"], ["jira"])
        self.assertEqual(action["invalid_actions"], ["calll", "sms"])

    def test_normalize_actions_handles_empty_values(self):
        cases = [
            None,
            float("nan"),
            "",
            " ",
        ]

        for value in cases:
            with self.subTest(value=value):
                actions, invalid_actions = self.loader.normalize_actions(value)
                self.assertEqual(actions, [])
                self.assertEqual(invalid_actions, [])

    def test_delay_minutes_is_parsed_from_action_row(self):
        self.load_runbook(
            hosts=[{"host": "server01"}],
            actions=[{
                "host": "server01",
                "trigger_group": "availability",
                "action": "email,jira,calls",
                "target": "guardia_msp",
                "delay_minutes": "15",
            }],
        )

        action = self.loader.get_action("client", "server01", "availability")

        self.assertEqual(action["delay_minutes"], 15)

    def test_missing_delay_minutes_defaults_to_zero(self):
        self.load_runbook(
            hosts=[{"host": "server01"}],
            actions=[{
                "host": "server01",
                "trigger_group": "availability",
                "action": "email",
                "target": "baseline",
            }],
        )

        action = self.loader.get_action("client", "server01", "availability")

        self.assertEqual(action["delay_minutes"], 0)

    def test_parse_delay_minutes_handles_invalid_values(self):
        cases = [
            (None, 0),
            (float("nan"), 0),
            ("", 0),
            (" ", 0),
            ("15", 15),
            (15.0, 15),
            (-1, 0),
            ("abc", 0),
        ]

        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(
                    self.loader.parse_delay_minutes(value),
                    expected,
                )


class RuleLoaderOncallCalendarTest(unittest.TestCase):

    def setUp(self):
        self.loader = RuleLoader()

    def load_oncall(self, oncall_rows=None, holiday_rows=None):
        self.loader.cache["client"] = {
            "oncall": pd.DataFrame(oncall_rows or []),
            "holidays": None if holiday_rows is None else pd.DataFrame(holiday_rows),
        }

    def default_oncall_row(self):
        return {
            "team": "noc",
            "start_date": "2026-06-01",
            "end_date": "2026-06-30",
            "start_time": "21:00",
            "end_time": "09:00",
            "user": "Juan",
            "phone": "5491111111111",
            "email": "guardia@example.com",
        }

    def david_row(self):
        return {
            "team": "msp",
            "start_date": "2026-06-17",
            "end_date": "2026-06-24",
            "start_time": "21:00",
            "end_time": "09:00",
            "user": "David Silva",
            "phone": "5491111111111",
            "email": "david@example.com",
        }

    def diego_row(self):
        return {
            "team": "msp",
            "start_date": "2026-06-24",
            "end_date": "2026-07-01",
            "start_time": "21:00",
            "end_time": "09:00",
            "user": "Diego Greppi",
            "phone": "5492222222222",
            "email": "diego@example.com",
        }

    def test_business_day_inside_time_window_returns_contact(self):
        self.load_oncall([self.default_oncall_row()], [])

        contact = self.loader.get_oncall_contact(
            "client",
            "noc",
            now=datetime(2026, 6, 1, 22, 0),
        )

        self.assertIsNotNone(contact)
        self.assertEqual(contact["oncall_reason"], "business_day_time_window")

    def test_business_day_outside_time_window_returns_none(self):
        self.load_oncall([self.default_oncall_row()], [])

        contact = self.loader.get_oncall_contact(
            "client",
            "noc",
            now=datetime(2026, 6, 1, 10, 0),
        )

        self.assertIsNone(contact)

    def test_overnight_window_matches_early_morning(self):
        self.load_oncall([self.default_oncall_row()], [])

        contact = self.loader.get_oncall_contact(
            "client",
            "noc",
            now=datetime(2026, 6, 2, 3, 0),
        )

        self.assertIsNotNone(contact)
        self.assertEqual(contact["oncall_reason"], "business_day_time_window")

    def test_saturday_is_covered_24h_inside_date_range(self):
        self.load_oncall([self.default_oncall_row()], [])

        contact = self.loader.get_oncall_contact(
            "client",
            "noc",
            now=datetime(2026, 6, 6, 10, 0),
        )

        self.assertIsNotNone(contact)
        self.assertEqual(contact["oncall_reason"], "weekend_24h")

    def test_sunday_is_covered_24h_inside_date_range(self):
        self.load_oncall([self.default_oncall_row()], [])

        contact = self.loader.get_oncall_contact(
            "client",
            "noc",
            now=datetime(2026, 6, 7, 15, 0),
        )

        self.assertIsNotNone(contact)
        self.assertEqual(contact["oncall_reason"], "weekend_24h")

    def test_holiday_is_covered_24h_inside_date_range(self):
        self.load_oncall(
            [self.default_oncall_row()],
            [{"date": "2026-06-17", "name": "Feriado X"}],
        )

        contact = self.loader.get_oncall_contact(
            "client",
            "noc",
            now=datetime(2026, 6, 17, 11, 0),
        )

        self.assertIsNotNone(contact)
        self.assertEqual(contact["oncall_reason"], "holiday_24h")
        self.assertEqual(contact["holiday_name"], "Feriado X")

    def test_holiday_exact_date_does_not_convert_entire_range_to_24h(self):
        self.load_oncall(
            [self.default_oncall_row()],
            [{"date": "2026-06-17", "name": "Feriado X"}],
        )

        contact = self.loader.get_oncall_contact(
            "client",
            "noc",
            now=datetime(2026, 6, 18, 11, 0),
        )

        self.assertIsNone(contact)

    def test_missing_holidays_sheet_does_not_break_oncall(self):
        self.load_oncall([self.default_oncall_row()], None)

        contact = self.loader.get_oncall_contact(
            "client",
            "noc",
            now=datetime(2026, 6, 1, 22, 0),
        )

        self.assertIsNotNone(contact)

    def test_invalid_holiday_date_is_ignored(self):
        self.load_oncall(
            [self.default_oncall_row()],
            [{"date": "invalid", "name": "Bad holiday"}],
        )

        contact = self.loader.get_oncall_contact(
            "client",
            "noc",
            now=datetime(2026, 6, 17, 11, 0),
        )

        self.assertIsNone(contact)

    def test_without_active_oncall_row_returns_none(self):
        row = self.default_oncall_row()
        row["start_date"] = "2026-07-01"
        row["end_date"] = "2026-07-31"
        self.load_oncall([row], [])

        contact = self.loader.get_oncall_contact(
            "client",
            "noc",
            now=datetime(2026, 6, 17, 22, 0),
        )

        self.assertIsNone(contact)

    def test_assignment_change_day_before_end_time_keeps_previous_user(self):
        self.load_oncall([self.david_row(), self.diego_row()], [])

        contact = self.loader.get_oncall_contact(
            "client",
            "msp",
            now=datetime(2026, 6, 24, 8, 30),
        )

        self.assertIsNotNone(contact)
        self.assertEqual(contact["user"], "David Silva")

    def test_assignment_change_day_after_end_time_has_no_oncall(self):
        self.load_oncall([self.david_row(), self.diego_row()], [])

        contact = self.loader.get_oncall_contact(
            "client",
            "msp",
            now=datetime(2026, 6, 24, 10, 0),
        )

        self.assertIsNone(contact)

    def test_assignment_start_day_before_start_time_has_no_oncall(self):
        self.load_oncall([self.david_row(), self.diego_row()], [])

        contact = self.loader.get_oncall_contact(
            "client",
            "msp",
            now=datetime(2026, 6, 24, 20, 30),
        )

        self.assertIsNone(contact)

    def test_assignment_start_day_after_start_time_uses_new_user(self):
        self.load_oncall([self.david_row(), self.diego_row()], [])

        contact = self.loader.get_oncall_contact(
            "client",
            "msp",
            now=datetime(2026, 6, 24, 21, 30),
        )

        self.assertIsNotNone(contact)
        self.assertEqual(contact["user"], "Diego Greppi")

    def test_business_day_inside_assignment_but_outside_window_has_no_oncall(self):
        self.load_oncall([self.david_row()], [])

        contact = self.loader.get_oncall_contact(
            "client",
            "msp",
            now=datetime(2026, 6, 18, 15, 0),
        )

        self.assertIsNone(contact)

    def test_weekend_inside_assignment_is_covered_24h(self):
        self.load_oncall([self.diego_row()], [])

        cases = [
            datetime(2026, 6, 27, 10, 0),
            datetime(2026, 6, 27, 15, 0),
            datetime(2026, 6, 28, 3, 0),
        ]

        for now in cases:
            with self.subTest(now=now):
                contact = self.loader.get_oncall_contact("client", "msp", now=now)
                self.assertIsNotNone(contact)
                self.assertEqual(contact["user"], "Diego Greppi")
                self.assertEqual(contact["oncall_reason"], "weekend_24h")

    def test_weekend_outside_assignment_is_not_covered(self):
        row = self.diego_row()
        row["start_date"] = "2026-06-27"
        row["start_time"] = "21:00"
        self.load_oncall([row], [])

        contact = self.loader.get_oncall_contact(
            "client",
            "msp",
            now=datetime(2026, 6, 27, 10, 0),
        )

        self.assertIsNone(contact)

    def test_overlapping_rows_use_most_recent_assignment_start(self):
        first = self.diego_row()
        first["user"] = "Older Guardia"
        first["start_date"] = "2026-06-24"
        second = self.diego_row()
        second["user"] = "Newer Guardia"
        second["start_date"] = "2026-06-25"
        self.load_oncall([first, second], [])

        contact = self.loader.get_oncall_contact(
            "client",
            "msp",
            now=datetime(2026, 6, 27, 10, 0),
        )

        self.assertIsNotNone(contact)
        self.assertEqual(contact["user"], "Newer Guardia")

    def test_timezone_aware_now_is_converted_to_local_time(self):
        self.load_oncall([self.diego_row()], [])

        contact = self.loader.get_oncall_contact(
            "client",
            "msp",
            now=datetime(2026, 6, 25, 0, 30, tzinfo=timezone.utc),
        )

        self.assertIsNotNone(contact)
        self.assertEqual(contact["user"], "Diego Greppi")

    def test_invalid_oncall_row_is_ignored_without_breaking_valid_rows(self):
        invalid = self.diego_row()
        invalid["start_date"] = "bad-date"
        invalid["user"] = "Invalid Guardia"
        valid = self.diego_row()
        self.load_oncall([invalid, valid], [])

        contact = self.loader.get_oncall_contact(
            "client",
            "msp",
            now=datetime(2026, 6, 24, 21, 30),
        )

        self.assertIsNotNone(contact)
        self.assertEqual(contact["user"], "Diego Greppi")


class RuleLoaderHostParsingTest(unittest.TestCase):

    def setUp(self):
        self.loader = RuleLoader()

    def test_extract_client_and_host_valid_formats(self):
        cases = [
            ("Cliente/Host", ("Cliente", "Host")),
            ("Cliente / Host", ("Cliente", "Host")),
            ("Banco X/test-noc", ("Banco X", "test-noc")),
            ("Banco X / test-noc", ("Banco X", "test-noc")),
            ("OTEK/SERVERCBA", ("OTEK", "SERVERCBA")),
        ]

        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(
                    self.loader.extract_client_and_host(value),
                    expected,
                )

    def test_extract_client_and_host_invalid_or_partial_formats(self):
        cases = [
            ("Host sin cliente", ("unknown", "Host sin cliente")),
            (None, ("unknown", "unknown")),
            ("", ("unknown", "unknown")),
            ("   ", ("unknown", "unknown")),
            ("/Host", ("unknown", "Host")),
            ("Cliente/", ("Cliente", "unknown")),
        ]

        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(
                    self.loader.extract_client_and_host(value),
                    expected,
                )

    def test_extract_client_and_host_splits_only_first_slash(self):
        cases = [
            ("Cliente/Subgrupo/Host", ("Cliente", "Subgrupo/Host")),
            ("Cliente / Subgrupo / Host", ("Cliente", "Subgrupo / Host")),
            ("Cliente/Subgrupo/Host/Extra", ("Cliente", "Subgrupo/Host/Extra")),
        ]

        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(
                    self.loader.extract_client_and_host(value),
                    expected,
                )

    def test_extract_client_and_host_accepts_non_string_values(self):
        cases = [
            (123, ("unknown", "123")),
            ({"host": "server"}, ("unknown", "{'host': 'server'}")),
        ]

        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(
                    self.loader.extract_client_and_host(value),
                    expected,
                )


if __name__ == "__main__":
    unittest.main()
