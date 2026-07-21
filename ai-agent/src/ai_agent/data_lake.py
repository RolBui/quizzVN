import hashlib
import json
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import httpx

from ai_agent.config import settings


TOKEN_URL = "https://oauth2.googleapis.com/token"
DRIVE_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"


class DataLakeError(RuntimeError):
    pass


class DataLakeConfigurationError(DataLakeError):
    pass


@dataclass(frozen=True)
class UploadResult:
    external_file_id: str
    web_view_link: str
    checksum_sha256: str
    size_bytes: int


def data_lake_configuration_status() -> str:
    if not settings.DATA_LAKE_ENABLED:
        return "disabled"
    if settings.DATA_LAKE_PROVIDER != "google_drive":
        return "unsupported_provider"
    required = (
        settings.GOOGLE_DRIVE_CLIENT_ID,
        settings.GOOGLE_DRIVE_CLIENT_SECRET,
        settings.GOOGLE_DRIVE_REFRESH_TOKEN,
    )
    return "configured" if all(required) else "misconfigured"


class GoogleDriveDataLake:
    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        if data_lake_configuration_status() != "configured":
            raise DataLakeConfigurationError("Google Drive data lake is not fully configured")
        self.transport = transport

    def upload_json(
        self,
        object_name: str,
        payload: dict[str, Any],
        metadata: dict[str, Any],
    ) -> UploadResult:
        content = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        checksum = hashlib.sha256(content).hexdigest()
        access_token = self._refresh_access_token()
        folder_id = self._resolve_folder_id(access_token)
        boundary = f"quizzvn_{uuid4().hex}"
        file_metadata = {
            "name": object_name,
            "mimeType": "application/json",
            "parents": [folder_id],
            "appProperties": {
                key: str(value)[:124]
                for key, value in metadata.items()
                if value is not None
            },
        }
        body = _multipart_related_body(boundary, file_metadata, content)
        with httpx.Client(
            timeout=settings.DATA_LAKE_TIMEOUT_SECONDS,
            transport=self.transport,
        ) as client:
            response = client.post(
                DRIVE_UPLOAD_URL,
                params={
                    "uploadType": "multipart",
                    "fields": "id,name,size,md5Checksum,webViewLink",
                },
                content=body,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": f"multipart/related; boundary={boundary}",
                },
            )
        try:
            response.raise_for_status()
            response_data = response.json()
            file_id = str(response_data["id"])
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise DataLakeError(f"Google Drive upload failed: {_response_error(response)}") from exc
        return UploadResult(
            external_file_id=file_id,
            web_view_link=str(response_data.get("webViewLink") or ""),
            checksum_sha256=checksum,
            size_bytes=len(content),
        )

    def _resolve_folder_id(self, access_token: str) -> str:
        if settings.GOOGLE_DRIVE_FOLDER_ID:
            return settings.GOOGLE_DRIVE_FOLDER_ID

        escaped_name = settings.GOOGLE_DRIVE_FOLDER_NAME.replace("'", "\\'")
        headers = {"Authorization": f"Bearer {access_token}"}
        with httpx.Client(
            timeout=settings.DATA_LAKE_TIMEOUT_SECONDS,
            transport=self.transport,
        ) as client:
            response = client.get(
                DRIVE_FILES_URL,
                params={
                    "q": (
                        f"name = '{escaped_name}' and "
                        "mimeType = 'application/vnd.google-apps.folder' and trashed = false"
                    ),
                    "fields": "files(id,name)",
                    "pageSize": 1,
                },
                headers=headers,
            )
            try:
                response.raise_for_status()
                files = response.json().get("files") or []
            except (httpx.HTTPError, AttributeError, ValueError) as exc:
                raise DataLakeError(
                    f"Unable to find Google Drive data folder: {_response_error(response)}"
                ) from exc
            if files:
                return str(files[0]["id"])

            response = client.post(
                DRIVE_FILES_URL,
                json={
                    "name": settings.GOOGLE_DRIVE_FOLDER_NAME,
                    "mimeType": "application/vnd.google-apps.folder",
                },
                params={"fields": "id,name"},
                headers=headers,
            )
        try:
            response.raise_for_status()
            return str(response.json()["id"])
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise DataLakeError(
                f"Unable to create Google Drive data folder: {_response_error(response)}"
            ) from exc

    def _refresh_access_token(self) -> str:
        with httpx.Client(
            timeout=settings.DATA_LAKE_TIMEOUT_SECONDS,
            transport=self.transport,
        ) as client:
            response = client.post(
                TOKEN_URL,
                data={
                    "client_id": settings.GOOGLE_DRIVE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_DRIVE_CLIENT_SECRET,
                    "refresh_token": settings.GOOGLE_DRIVE_REFRESH_TOKEN,
                    "grant_type": "refresh_token",
                },
            )
        try:
            response.raise_for_status()
            access_token = str(response.json()["access_token"])
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise DataLakeError(f"Google OAuth token refresh failed: {_response_error(response)}") from exc
        if not access_token:
            raise DataLakeError("Google OAuth returned an empty access token")
        return access_token


def get_data_lake() -> GoogleDriveDataLake:
    if settings.DATA_LAKE_PROVIDER != "google_drive":
        raise DataLakeConfigurationError(
            f"Unsupported data lake provider: {settings.DATA_LAKE_PROVIDER}"
        )
    return GoogleDriveDataLake()


def _multipart_related_body(
    boundary: str,
    metadata: dict[str, Any],
    content: bytes,
) -> bytes:
    metadata_json = json.dumps(metadata, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return b"".join(
        (
            f"--{boundary}\r\n".encode("ascii"),
            b"Content-Type: application/json; charset=UTF-8\r\n\r\n",
            metadata_json,
            b"\r\n",
            f"--{boundary}\r\n".encode("ascii"),
            b"Content-Type: application/json\r\n\r\n",
            content,
            b"\r\n",
            f"--{boundary}--\r\n".encode("ascii"),
        )
    )


def _response_error(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return f"HTTP {response.status_code}"
    error = data.get("error") if isinstance(data, dict) else None
    if isinstance(error, dict):
        return str(error.get("message") or f"HTTP {response.status_code}")[:500]
    return str(error or f"HTTP {response.status_code}")[:500]
