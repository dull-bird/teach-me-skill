from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import run_onboarding_e2e as onboarding  # noqa: E402


class OnboardingE2EUnitTests(unittest.TestCase):
    def test_parse_codex_session_id(self) -> None:
        session = "019f4b8f-2d8f-7b91-a827-57e19b095c46"
        self.assertEqual(onboarding.parse_session_id("codex", f"session id: {session}"), session)

    def test_parse_kimi_session_id(self) -> None:
        output = '{"role":"meta","session_id":"session_abc","content":"resume"}'
        self.assertEqual(onboarding.parse_session_id("kimi", output), "session_abc")


if __name__ == "__main__":
    unittest.main()
