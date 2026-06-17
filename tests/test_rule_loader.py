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


if __name__ == "__main__":
    unittest.main()
