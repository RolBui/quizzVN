import unittest
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ai_agent.config import settings
from ai_agent.database import Base
from ai_agent.model_registry import (
    approve_model,
    deploy_model,
    retire_model,
    select_model_route,
    submit_evaluation,
)
from ai_agent.models import AgentModelVersion


class ModelRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database_path = Path.cwd() / f".model-routing-{uuid4().hex}.db"
        self.engine = create_engine(f"sqlite:///{self.database_path.as_posix()}")
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        self.original = {
            "MODEL_ROUTING_ENABLED": settings.MODEL_ROUTING_ENABLED,
            "LOCAL_INFERENCE_URL": settings.LOCAL_INFERENCE_URL,
            "AI_PROVIDER": settings.AI_PROVIDER,
            "AI_MODEL": settings.AI_MODEL,
        }
        settings.MODEL_ROUTING_ENABLED = True
        settings.LOCAL_INFERENCE_URL = "http://model-server.local/v1/chat/completions"
        settings.AI_PROVIDER = "gemini"
        settings.AI_MODEL = "gemini-test"

    def tearDown(self) -> None:
        for key, value in self.original.items():
            setattr(settings, key, value)
        self.engine.dispose()
        self.database_path.unlink(missing_ok=True)

    def _model(self, db, version: str) -> AgentModelVersion:
        model = AgentModelVersion(
            idempotency_key=f"model-routing-{version}-000000000000",
            name="question-model",
            version=version,
            provider="local_openai",
            base_model="Qwen/Qwen2.5-3B-Instruct",
            serving_model=f"question-model:{version}",
            status="approved",
            evaluation_score=0.95,
            evaluation_threshold=0.9,
        )
        db.add(model)
        db.commit()
        db.refresh(model)
        return model

    def test_active_model_and_shadow_candidate_can_coexist(self) -> None:
        db = self.session_factory()
        try:
            active = self._model(db, "1.0.0")
            shadow = self._model(db, "1.1.0")
            deploy_model(db, active, "active", "reviewer", "production baseline")
            deploy_model(db, shadow, "shadow", "reviewer", "compare candidate")

            db.refresh(active)
            db.refresh(shadow)
            route = select_model_route(db, "dispatch-0000000000000001")

            self.assertEqual(active.status, "active")
            self.assertEqual(shadow.status, "shadow")
            self.assertEqual(route.model_version_id, active.id)
            self.assertEqual(route.shadow_model_version_id, shadow.id)
        finally:
            db.close()

    def test_canary_routes_only_a_stable_fraction_to_local_model(self) -> None:
        db = self.session_factory()
        try:
            canary = self._model(db, "2.0.0")
            deploy_model(db, canary, "canary", "reviewer", "controlled rollout", 25)
            local_count = sum(
                select_model_route(db, f"dispatch-{index:08d}").model_version_id
                == canary.id
                for index in range(400)
            )
            self.assertGreater(local_count, 60)
            self.assertLess(local_count, 140)
        finally:
            db.close()

    def test_failed_evaluation_cannot_be_approved_or_deployed(self) -> None:
        db = self.session_factory()
        try:
            model = self._model(db, "3.0.0")
            model.status = "registered"
            db.commit()

            submit_evaluation(
                db,
                model,
                {"structural_accuracy": 0.89},
                "evaluation-pipeline",
            )

            self.assertEqual(model.status, "evaluation_failed")
            with self.assertRaises(ValueError):
                approve_model(db, model, "reviewer", "below threshold")
            with self.assertRaises(ValueError):
                deploy_model(db, model, "shadow", "reviewer", "must not deploy")
        finally:
            db.close()

    def test_retired_active_model_returns_routing_to_default_provider(self) -> None:
        db = self.session_factory()
        try:
            model = self._model(db, "4.0.0")
            deploy_model(db, model, "active", "reviewer", "activate")
            retire_model(db, model, "reviewer", "rollback")

            route = select_model_route(db, "dispatch-retired-model")

            self.assertEqual(model.status, "retired")
            self.assertIsNone(route.model_version_id)
            self.assertEqual(route.provider, "gemini")
            self.assertEqual(route.model, "gemini-test")
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
