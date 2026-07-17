import time
import unittest

from app.services.ai_agent_security import build_ai_agent_signature, verify_ai_agent_signature


class AIAgentSecurityTests(unittest.TestCase):
    def test_accepts_valid_signature(self) -> None:
        body = b'{"status":"completed"}'
        timestamp = str(int(time.time()))
        signature = build_ai_agent_signature("shared-secret", timestamp, body)

        self.assertTrue(
            verify_ai_agent_signature(
                "shared-secret",
                timestamp,
                body,
                signature,
                300,
            )
        )

    def test_rejects_tampered_or_expired_signature(self) -> None:
        timestamp = str(int(time.time()) - 600)
        signature = build_ai_agent_signature("shared-secret", timestamp, b"original")

        self.assertFalse(
            verify_ai_agent_signature(
                "shared-secret",
                timestamp,
                b"changed",
                signature,
                300,
            )
        )


if __name__ == "__main__":
    unittest.main()
