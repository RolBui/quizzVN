import importlib
import pkgutil
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models
from app.database import Base
from app.models.billing import PaymentOrder, SubscriptionPlan
from app.models.role import Role
from app.models.user import User
from app.services.analytics_service import get_payment_analytics_overview


for module in pkgutil.iter_modules(app.models.__path__):
    importlib.import_module(f"app.models.{module.name}")


class AdminPaymentAnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        role = Role(name="teacher")
        self.db.add(role)
        self.db.flush()
        self.teacher = User(
            role_id=role.id,
            full_name="Teacher Analytics",
            username="teacher-analytics",
            email="analytics@example.com",
        )
        self.plan = SubscriptionPlan(
            code="silver",
            name="Bạc",
            price_vnd=69_000,
            qc_amount=500,
            duration_days=30,
            is_active=True,
        )
        self.db.add_all([self.teacher, self.plan])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _add_order(
        self,
        transfer_code: str,
        amount: int,
        status: str,
        paid_at: datetime | None,
    ) -> None:
        self.db.add(
            PaymentOrder(
                teacher_id=self.teacher.id,
                plan_id=self.plan.id,
                transfer_code=transfer_code,
                amount_vnd=amount,
                qc_amount=500,
                duration_days=30,
                quantity=1,
                unit_price_vnd=amount,
                subtotal_vnd=amount,
                status=status,
                expires_at=(paid_at or self.now) + timedelta(minutes=15),
                paid_at=paid_at,
            )
        )

    def test_overview_counts_only_paid_orders_in_selected_period(self):
        self.now = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)
        self._add_order("CURRENT-1", 69_000, "paid", self.now - timedelta(hours=2))
        self._add_order("CURRENT-2", 129_000, "paid", self.now - timedelta(days=2))
        self._add_order("PREVIOUS", 49_000, "paid", self.now - timedelta(days=8))
        self._add_order("PENDING", 999_000, "pending", None)
        self._add_order("OLD", 500_000, "paid", self.now - timedelta(days=30))
        self.db.commit()

        with patch("app.services.analytics_service.utc_now", return_value=self.now):
            result = get_payment_analytics_overview(self.db, "7d")

        metrics = {metric["key"]: metric for metric in result["metrics"]}
        self.assertEqual(result["paid_orders"], 2)
        self.assertEqual(metrics["revenue"]["value"], 198_000)
        self.assertEqual(metrics["average_order_value"]["value"], 99_000)
        self.assertEqual(sum(point["current"] for point in result["cash_flow"]), 198_000)
        self.assertEqual(sum(point["last"] for point in result["cash_flow"]), 49_000)
        self.assertEqual(sum(point["paid_orders"] for point in result["cash_flow"]), 2)

    def test_year_overview_groups_paid_orders_by_month(self):
        self.now = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)
        self._add_order("JULY-2026", 129_000, "paid", self.now - timedelta(days=2))
        self._add_order(
            "JULY-2025",
            69_000,
            "paid",
            datetime(2025, 7, 20, 8, 0, tzinfo=timezone.utc),
        )
        self.db.commit()

        with patch("app.services.analytics_service.utc_now", return_value=self.now):
            result = get_payment_analytics_overview(self.db, "year")

        july = result["cash_flow"][6]
        self.assertEqual(july["name"], "T7")
        self.assertEqual(july["current"], 129_000)
        self.assertEqual(july["last"], 69_000)
        self.assertEqual(july["paid_orders"], 1)


if __name__ == "__main__":
    unittest.main()
