import json
import unittest
from unittest.mock import patch

import httpx

from ai_agent.config import settings
from ai_agent.data_lake import GoogleDriveDataLake, data_lake_configuration_status


class GoogleDriveDataLakeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original = {
            "DATA_LAKE_ENABLED": settings.DATA_LAKE_ENABLED,
            "DATA_LAKE_PROVIDER": settings.DATA_LAKE_PROVIDER,
            "GOOGLE_DRIVE_CLIENT_ID": settings.GOOGLE_DRIVE_CLIENT_ID,
            "GOOGLE_DRIVE_CLIENT_SECRET": settings.GOOGLE_DRIVE_CLIENT_SECRET,
            "GOOGLE_DRIVE_REFRESH_TOKEN": settings.GOOGLE_DRIVE_REFRESH_TOKEN,
            "GOOGLE_DRIVE_FOLDER_ID": settings.GOOGLE_DRIVE_FOLDER_ID,
        }
        settings.DATA_LAKE_ENABLED = True
        settings.DATA_LAKE_PROVIDER = "google_drive"
        settings.GOOGLE_DRIVE_CLIENT_ID = "client-id"
        settings.GOOGLE_DRIVE_CLIENT_SECRET = "client-secret"
        settings.GOOGLE_DRIVE_REFRESH_TOKEN = "refresh-token"
        settings.GOOGLE_DRIVE_FOLDER_ID = "folder-id"

    def tearDown(self) -> None:
        for name, value in self.original.items():
            setattr(settings, name, value)

    def test_reports_configuration_state(self) -> None:
        self.assertEqual(data_lake_configuration_status(), "configured")
        settings.GOOGLE_DRIVE_FOLDER_ID = ""
        self.assertEqual(data_lake_configuration_status(), "configured")
        settings.GOOGLE_DRIVE_REFRESH_TOKEN = ""
        self.assertEqual(data_lake_configuration_status(), "misconfigured")

    def test_refreshes_token_and_uploads_multipart_json(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if request.url.host == "oauth2.googleapis.com":
                return httpx.Response(200, json={"access_token": "access-token"})
            self.assertEqual(request.headers["authorization"], "Bearer access-token")
            body = request.content.decode("utf-8")
            self.assertIn("folder-id", body)
            self.assertIn("Câu hỏi đã duyệt", body)
            return httpx.Response(
                200,
                json={
                    "id": "drive-file-id",
                    "webViewLink": "https://drive.google.com/file/d/drive-file-id/view",
                },
            )

        lake = GoogleDriveDataLake(transport=httpx.MockTransport(handler))
        result = lake.upload_json(
            "approved.json",
            {"title": "Câu hỏi đã duyệt"},
            {"artifact_type": "approved"},
        )

        self.assertEqual(len(requests), 2)
        self.assertEqual(result.external_file_id, "drive-file-id")
        self.assertEqual(result.size_bytes, len(json.dumps(
            {"title": "Câu hỏi đã duyệt"},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")))
        self.assertEqual(len(result.checksum_sha256), 64)

    def test_creates_its_own_drive_folder_when_id_is_not_configured(self) -> None:
        settings.GOOGLE_DRIVE_FOLDER_ID = ""
        calls: list[tuple[str, str]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append((request.method, request.url.path))
            if request.url.host == "oauth2.googleapis.com":
                return httpx.Response(200, json={"access_token": "access-token"})
            if request.method == "GET":
                return httpx.Response(200, json={"files": []})
            if request.url.path == "/drive/v3/files":
                return httpx.Response(200, json={"id": "created-folder-id"})
            self.assertIn("created-folder-id", request.content.decode("utf-8"))
            return httpx.Response(200, json={"id": "drive-file-id"})

        result = GoogleDriveDataLake(
            transport=httpx.MockTransport(handler)
        ).upload_json("generated.json", {"questions": []}, {})

        self.assertEqual(result.external_file_id, "drive-file-id")
        self.assertEqual(len(calls), 4)


if __name__ == "__main__":
    unittest.main()
