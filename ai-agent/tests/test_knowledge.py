import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ai_agent.config import settings
from ai_agent.database import Base
from ai_agent.knowledge import (
    format_retrieval_context,
    index_approved_artifact,
    resolve_knowledge_scope,
)
from ai_agent.models import AgentArtifact, AgentKnowledgeItem


class KnowledgeIndexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.original_rag_enabled = settings.RAG_ENABLED
        settings.RAG_ENABLED = True

    def tearDown(self) -> None:
        settings.RAG_ENABLED = self.original_rag_enabled
        self.db.close()
        self.engine.dispose()

    def test_teacher_scope_is_always_private(self) -> None:
        scope = resolve_knowledge_scope(
            {
                "owner_type": "teacher",
                "owner_id": "42",
                "knowledge_visibility": "system",
            },
            {},
        )

        self.assertEqual(
            scope,
            {"owner_type": "teacher", "owner_id": "42", "visibility": "private"},
        )

    @patch("ai_agent.knowledge.embed_documents")
    def test_indexes_only_owned_approved_questions(self, embed_documents) -> None:
        embed_documents.return_value = [[0.01] * settings.EMBEDDING_DIMENSIONS]
        artifact = AgentArtifact(
            external_job_id="9",
            idempotency_key="approved:9",
            artifact_type="approved",
            status="queued",
            object_name="approved.json",
            payload={
                "input": {
                    "request_data": {
                        "owner_type": "teacher",
                        "owner_id": "42",
                        "subject": "Mathematics",
                        "grade": "12",
                    }
                },
                "output": {
                    "questions": [
                        {
                            "type": "short_answer",
                            "content": "What is 1 + 1?",
                            "correct_answer": ["2"],
                            "difficulty": "easy",
                            "topic": "Arithmetic",
                        }
                    ]
                },
            },
            artifact_metadata={"validation_status": "teacher_approved"},
        )
        self.db.add(artifact)
        self.db.commit()

        indexed = index_approved_artifact(self.db, artifact)
        item = self.db.query(AgentKnowledgeItem).one()

        self.assertEqual(indexed, 1)
        self.assertEqual(item.owner_type, "teacher")
        self.assertEqual(item.owner_id, "42")
        self.assertEqual(item.visibility, "private")
        self.assertEqual(item.status, "approved")

    @patch("ai_agent.knowledge.embed_documents")
    def test_skips_legacy_artifact_without_owner(self, embed_documents) -> None:
        artifact = AgentArtifact(
            external_job_id="10",
            idempotency_key="approved:10",
            artifact_type="approved",
            status="queued",
            object_name="approved.json",
            payload={
                "input": {"request_data": {"subject": "Mathematics"}},
                "output": {"questions": [{"type": "essay", "content": "Explain it"}]},
            },
        )

        self.assertEqual(index_approved_artifact(self.db, artifact), 0)
        embed_documents.assert_not_called()

    def test_formats_references_as_untrusted_context(self) -> None:
        item = AgentKnowledgeItem(
            question_type="multiple_choice",
            subject="Physics",
            grade="10",
            difficulty="medium",
            topic="Mechanics",
            content="Reference question",
            options=["A", "B"],
            correct_answer="A",
            explanation="Reference explanation",
        )

        context = format_retrieval_context([item])

        self.assertIn("APPROVED_REFERENCE_DATA", context)
        self.assertIn("untrusted examples", context)
        self.assertIn("do not copy wording", context)


if __name__ == "__main__":
    unittest.main()
