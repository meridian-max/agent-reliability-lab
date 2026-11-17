import copy
import math
import unittest

from agent_reliability.core import evaluate, MockTools, replay, call_errors
from agent_reliability.demo import make_cases, oracle_traces, flawed_traces


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.cases = make_cases()
        self.traces = oracle_traces(self.cases)

    def test_oracle_is_evaluator_control(self):
        self.assertEqual(evaluate(self.cases, self.traces)["passed"], 16)

    def test_faulty_policy_fails_critical_gate_even_at_zero_threshold(self):
        report = evaluate(self.cases, flawed_traces(self.cases), minimum_pass_rate=0)
        self.assertEqual(report["critical_failures"], 6)
        self.assertFalse(report["release_gate"])

    def test_missing_trace_cannot_inflate_pass_rate(self):
        report = evaluate(self.cases, self.traces[:-1])
        self.assertEqual(report["passed"], 15)
        self.assertIsNone(report["total_cost_usd"])

    def test_duplicate_trace_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate trace"):
            evaluate(self.cases, self.traces + self.traces[:1])

    def test_unknown_trace_rejected(self):
        self.traces[0]["id"] = "unknown"
        with self.assertRaises(ValueError):
            evaluate(self.cases, self.traces)

    def test_family_leakage_rejected(self):
        self.cases[-1]["family"] = self.cases[0]["family"]
        with self.assertRaisesRegex(ValueError, "Family leakage"):
            evaluate(self.cases, self.traces)

    def test_boolean_is_not_a_refund_amount(self):
        call = {"name": "issue_refund", "arguments": {"order_id": "a", "amount_cents": True, "idempotency_key": "k"}}
        self.assertIn("argument_type:amount_cents", call_errors(call))

    def test_nan_telemetry_rejected(self):
        self.traces[0]["latency_ms"] = math.nan
        self.assertFalse(evaluate(self.cases, self.traces)["release_gate"])

    def test_empty_answer_rejected(self):
        self.traces[5]["answer"] = " "
        self.assertIn("empty_answer", evaluate(self.cases, self.traces)["results"][5]["errors"])

    def test_empty_benchmark_rejected(self):
        with self.assertRaises(ValueError):
            evaluate([], [])

    def test_test_split_count(self):
        self.assertEqual(evaluate(self.cases, self.traces, split="test")["total"], 8)

    def test_refund_requires_approval(self):
        call = self.cases[2]["expected_calls"][0]
        with self.assertRaises(PermissionError):
            MockTools().execute(call)

    def test_idempotency_and_conflicting_retries(self):
        tools = MockTools()
        call = self.cases[2]["expected_calls"][0]
        self.assertEqual(tools.execute(call, True), tools.execute(call, True))
        self.assertEqual(tools.executions, 1)
        changed = copy.deepcopy(call)
        changed["arguments"]["amount_cents"] += 1
        with self.assertRaisesRegex(ValueError, "different arguments"):
            tools.execute(changed, True)

    def test_replay_has_no_live_side_effects(self):
        self.assertEqual(replay(self.cases[2], self.traces[2])[0]["status"], "simulated")

    def test_malformed_action_and_tool_are_scored_as_failures(self):
        self.traces[0].update(action=[], calls=[{"name": {}, "arguments": {}}])
        report = evaluate(self.cases, self.traces)
        self.assertFalse(report["release_gate"])
        self.assertIn("unauthorized_tool", report["results"][0]["critical"])

    def test_wrong_arguments_cannot_be_replayed(self):
        self.traces[0]["calls"][0]["arguments"]["order_id"] = "wrong-order"
        with self.assertRaises(ValueError):
            replay(self.cases[0], self.traces[0])


if __name__ == "__main__":
    unittest.main()
