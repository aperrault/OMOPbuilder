"""Live smoke tests that hit the real Gemini API.
Requires GOOGLE_API_KEY to be set in the environment.
"""
import os
import sys
import unittest

# Skip entire module if no API key
if not os.environ.get("GOOGLE_API_KEY"):
    print("GOOGLE_API_KEY not set — skipping live tests")
    sys.exit(0)

from core import agent_loop
import core


class TestLiveAgentLoop(unittest.TestCase):
    """Smoke tests that run real queries against Gemini."""

    def test_simple_query_returns_sql(self):
        """A basic query should return valid SQL containing SELECT."""
        result = agent_loop("Find all patients with Type 2 Diabetes.", max_turns=5)
        self.assertIn("SELECT", result.upper(), "Agent should return SQL with a SELECT statement")
        self.assertNotIn("ERROR", result.upper().split("SELECT")[0],
                         "Agent should not return an error before the SQL")

    def test_continuation_preserves_context(self):
        """After an initial query, a continuation should build on it."""
        initial = agent_loop("Find all female patients over 50.", max_turns=5)
        self.assertIn("SELECT", initial.upper())

        # History should be saved
        self.assertTrue(len(core.last_history) > 0, "History should be preserved")

        revised = agent_loop("Also filter to only those with hypertension.", max_turns=5, is_continuation=True)
        self.assertIn("SELECT", revised.upper(), "Continuation should return SQL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
