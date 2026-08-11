import importlib
import pkgutil
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models as models_pkg
from app.database import Base
from app.models.admin_invitation import AdminInvitation
from app.models.oauth_account import OAuthAccount
from app.models.role import Role
from app.models.user import User
from app.models.user_session import UserSession
from app.services.auth_service import handle_google_admin_callback

for module in pkgutil.iter_modules(models_pkg.__path__):
    importlib.import_module(f"app.models.{module.name}")


class AdminGoogleRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.TestingSessionLocal = sessionmaker(bind=self.engine)
        self.db = self.TestingSessionLocal()

        self.admin_role = Role(name="admin")
        self.pending_role = Role(name="pending")
        self.db.add_all([self.admin_role, self.pending_role])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _google_user_info(self, email: str, sub: str = "google-user-1"):
        return {
            "sub": sub,
            "email": email,
            "name": "Google Admin",
            "picture": "https://example.test/avatar.png",
        }

    def _google_token(self):
        return {
            "access_token": "google-access-token",
            "refresh_token": "google-refresh-token",
            "expires_at": datetime.now(timezone.utc).timestamp() + 3600,
        }

    def test_existing_active_admin_google_registration_reports_email_exists(self):
        admin = User(
            role_id=self.admin_role.id,
            full_name="Existing Admin",
            username="existing_admin",
            email="admin@example.com",
            auth_type="local",
            email_verified=True,
            status="active",
        )
        self.db.add(admin)
        self.db.commit()

        result = handle_google_admin_callback(
            self.db,
            self._google_token(),
            self._google_user_info("admin@example.com"),
            "127.0.0.1",
            "test-agent",
        )

        self.assertEqual(result["status"], "admin_email_exists")
        self.assertEqual(result["email"], "admin@example.com")
        self.assertEqual(self.db.query(AdminInvitation).count(), 0)
        self.assertEqual(self.db.query(UserSession).count(), 0)
        self.assertEqual(self.db.query(OAuthAccount).count(), 0)

    def test_new_google_admin_registration_creates_invitation(self):
        with patch("app.services.auth_service._send_admin_oauth_invitation_email") as send_email:
            result = handle_google_admin_callback(
                self.db,
                self._google_token(),
                self._google_user_info("new-admin@example.com", sub="google-user-2"),
                "127.0.0.1",
                "test-agent",
            )

        self.assertEqual(result["status"], "verification_email_sent")
        self.assertEqual(result["email"], "new-admin@example.com")
        invitation = self.db.query(AdminInvitation).one()
        self.assertEqual(invitation.email, "new-admin@example.com")
        self.assertEqual(invitation.status, "otp_pending")
        self.assertEqual(self.db.query(UserSession).count(), 0)
        self.assertEqual(self.db.query(OAuthAccount).count(), 1)
        send_email.assert_called_once()


if __name__ == "__main__":
    unittest.main()