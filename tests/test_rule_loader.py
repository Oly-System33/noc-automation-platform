import unittest

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
