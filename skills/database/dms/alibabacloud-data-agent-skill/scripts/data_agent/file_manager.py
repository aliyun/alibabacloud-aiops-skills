"""File management for Data Agent.

Author: Tinker
Created: 2026-03-01
"""

from __future__ import annotations

import os
import asyncio
from pathlib import Path
from typing import Optional, List

import requests
import aiohttp

from data_agent.client import DataAgentClient, AsyncDataAgentClient
from data_agent.models import FileInfo
from data_agent.exceptions import FileUploadError, FileDownloadError


# Supported file types and their MIME types
SUPPORTED_FILE_TYPES = {
    ".csv": "text/csv",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".json": "application/json",
    ".txt": "text/plain",
}


class FileManager:
    """Manages file uploads and downloads for Data Agent.

    Handles uploading local files to OSS and retrieving
    generated reports from Data Agent sessions.
    """

    def __init__(self, client: DataAgentClient):
        """Initialize file manager.

        Args:
            client: DataAgentClient instance for API calls.
        """
        self._client = client

    def upload_file(
        self,
        file_path: str,
        timeout: int = 60,
    ) -> FileInfo:
        """Upload a file for analysis.

        Args:
            file_path: Path to the local file.
            timeout: Upload timeout in seconds.

        Returns:
            FileInfo with file_id and metadata.

        Raises:
            FileUploadError: If upload fails.
        """
        path = Path(file_path)

        # Validate file exists
        if not path.exists():
            raise FileUploadError(f"File not found: {file_path}", file_path=file_path)

        # Validate file type
        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_FILE_TYPES:
            raise FileUploadError(
                f"Unsupported file type: {suffix}. Supported types: {list(SUPPORTED_FILE_TYPES.keys())}",
                file_path=file_path,
            )

        filename = path.name
        file_size = path.stat().st_size

        # Get upload signature
        try:
            signature_response = self._client.get_file_upload_signature(
                filename=filename,
                file_size=file_size,
            )
        except Exception as e:
            raise FileUploadError(f"Failed to get upload signature: {e}", file_path=file_path)

        # Extract OSS direct upload parameters from data field (support both camelCase and PascalCase)
        # For API_KEY auth, the response has been processed to camelCase
        data = signature_response.get("data", signature_response.get("Data", {}))
        upload_host = data.get("uploadHost", data.get("UploadHost"))
        upload_dir = data.get("uploadDir", data.get("UploadDir"))
        policy = data.get("policy", data.get("Policy"))
        oss_signature = data.get("ossSignature", data.get("OssSignature"))
        oss_date = data.get("ossDate", data.get("OssDate"))
        oss_security_token = data.get("ossSecurityToken", data.get("OssSecurityToken"))
        oss_credential = data.get("ossCredential", data.get("OssCredential"))

        if not all([upload_host, upload_dir, policy, oss_signature]):
            raise FileUploadError(
                f"Invalid signature response: missing required OSS upload parameters",
                file_path=file_path,
            )

        # Construct file key and upload URL
        file_key = f"{upload_dir}/{filename}"
        upload_url = upload_host
        # UploadLocation is the full OSS path: UploadDir/Filename
        upload_location = file_key

        # Upload to OSS using POST form (multipart/form-data)
        content_type = SUPPORTED_FILE_TYPES[suffix]
        try:
            with open(file_path, "rb") as f:
                # OSS requires file field to be named 'file'
                files = {
                    "key": (None, file_key),
                    "policy": (None, policy),
                    "x-oss-signature": (None, oss_signature),
                    "x-oss-date": (None, oss_date),
                    "x-oss-security-token": (None, oss_security_token or ""),
                    "x-oss-credential": (None, oss_credential),
                    "x-oss-signature-version": (None, "OSS4-HMAC-SHA256"),
                    "success_action_status": (None, "200"),
                    "file": (filename, f, content_type),
                }
                response = requests.post(
                    upload_url,
                    files=files,
                    timeout=timeout,
                )
                response.raise_for_status()
        except requests.RequestException as e:
            raise FileUploadError(f"Failed to upload to OSS: {e}", file_path=file_path)

        # FileId is the UploadDir itself (the unique upload path)
        file_id = upload_dir

        # Confirm upload and get the correct FileId from response
        # Note: For API_KEY auth, FileUploadCallback may fail, so we use upload_dir as file_id
        final_file_id = file_id
        try:
            callback_resp = self._client.file_upload_callback(file_id, filename, upload_location, file_size)
            # Extract FileId from callback response - after API adapter transformation,
            # response fields become camelCase
            data_field = callback_resp.get("data", callback_resp.get("Data", {}))
            data_center_file_id = data_field.get("fileId", data_field.get("FileId"))
            if data_center_file_id:
                final_file_id = data_center_file_id
        except Exception as e:
            # If callback fails, use upload_dir as file_id (fallback)
            print(f"Warning: FileUploadCallback failed: {e}. Using upload_dir as file_id.")
            final_file_id = file_id

        return FileInfo(
            file_id=final_file_id,
            filename=filename,
            file_type=suffix.lstrip("."),
            size=file_size,
            upload_url=f"{upload_host}/{file_key}",
        )

    def list_files(self, session_id: str, file_category: Optional[str] = None) -> List[FileInfo]:
        """List files associated with a session.

        Args:
            session_id: The session ID.
            file_category: Optional filter, e.g. "WebReport" for agent-generated
                           reports, or None to list all files.

        Returns:
            List of FileInfo objects.
        """
        response = self._client.list_files(session_id, file_category=file_category)
        files = response.get("Data", response.get("Files", []))
        if not isinstance(files, list):
            files = []

        return [
            FileInfo(
                file_id=f.get("FileId", ""),
                filename=f.get("FileName", ""),
                file_type=f.get("FileType", ""),
                size=f.get("FileSize", 0),
                # API returns DownloadLink; fall back to DownloadUrl for compatibility
                download_url=f.get("DownloadLink") or f.get("DownloadUrl"),
            )
            for f in files
        ]

    def list_reports(self, session_id: str) -> List[FileInfo]:
        """List agent-generated reports (WebReport) for a session.

        Args:
            session_id: The session ID.

        Returns:
            List of FileInfo objects for WebReport files.
        """
        return self.list_files(session_id, file_category="WebReport")

    def download_from_url(
        self,
        download_url: str,
        save_path: str,
        timeout: int = 120,
    ) -> str:
        """Download a file from a URL and save locally.

        Args:
            download_url: Direct download URL.
            save_path: Local path to save the file.
            timeout: Download timeout in seconds.

        Returns:
            Absolute path to the saved file.

        Raises:
            FileDownloadError: If download fails.
        """
        save = Path(save_path)
        save.parent.mkdir(parents=True, exist_ok=True)
        try:
            response = requests.get(download_url, timeout=timeout, stream=True)
            response.raise_for_status()
            with save.open("wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return str(save.resolve())
        except requests.RequestException as e:
            raise FileDownloadError(f"Failed to download file: {e}")

    def download_file(
        self,
        file_id: str,
        save_path: str,
        timeout: int = 60,
    ) -> str:
        """Download a file by ID.

        Args:
            file_id: The file ID to download.
            save_path: Path to save the downloaded file.
            timeout: Download timeout in seconds.

        Returns:
            Path to the saved file.

        Raises:
            FileDownloadError: If download fails.
        """
        # Get file info with download URL
        # Note: This assumes the list_files API returns download URLs
        # Actual implementation may vary based on API behavior

        try:
            response = requests.get(
                f"https://dms.aliyuncs.com/files/{file_id}",  # Placeholder URL
                timeout=timeout,
                stream=True,
            )
            response.raise_for_status()

            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return save_path
        except requests.RequestException as e:
            raise FileDownloadError(f"Failed to download file: {e}")

    def delete_file(self, file_id: str) -> bool:
        """Delete an uploaded file.

        Args:
            file_id: The file ID to delete.

        Returns:
            True if deletion was successful.
        """
        try:
            self._client.delete_file(file_id)
            return True
        except Exception:
            return False

    def get_file_type(self, file_path: str) -> Optional[str]:
        """Get the file type from path.

        Args:
            file_path: Path to the file.

        Returns:
            File type string or None if unsupported.
        """
        suffix = Path(file_path).suffix.lower()
        return suffix.lstrip(".") if suffix in SUPPORTED_FILE_TYPES else None

    def is_supported_file(self, file_path: str) -> bool:
        """Check if a file type is supported.

        Args:
            file_path: Path to the file.

        Returns:
            True if file type is supported.
        """
        suffix = Path(file_path).suffix.lower()
        return suffix in SUPPORTED_FILE_TYPES


class AsyncFileManager:
    """Asynchronous file manager for Data Agent.

    Provides async/await support for file operations.
    """

    def __init__(self, client: AsyncDataAgentClient):
        """Initialize async file manager.

        Args:
            client: AsyncDataAgentClient instance for API calls.
        """
        self._client = client

    async def upload_file(
        self,
        file_path: str,
        timeout: int = 60,
    ) -> FileInfo:
        """Upload a file for analysis asynchronously.

        Args:
            file_path: Path to the local file.
            timeout: Upload timeout in seconds.

        Returns:
            FileInfo with file_id and metadata.

        Raises:
            FileUploadError: If upload fails.
        """
        path = Path(file_path)

        if not path.exists():
            raise FileUploadError(f"File not found: {file_path}", file_path=file_path)

        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_FILE_TYPES:
            raise FileUploadError(
                f"Unsupported file type: {suffix}",
                file_path=file_path,
            )

        filename = path.name
        file_size = path.stat().st_size

        # Get upload signature
        try:
            signature_response = await self._client.get_file_upload_signature(
                filename=filename,
                file_size=file_size,
            )
        except Exception as e:
            raise FileUploadError(f"Failed to get upload signature: {e}", file_path=file_path)

        # Extract OSS direct upload parameters from data field (support both camelCase and PascalCase)
        # For API_KEY auth, the response has been processed to camelCase
        data = signature_response.get("data", signature_response.get("Data", {}))
        upload_host = data.get("uploadHost", data.get("UploadHost"))
        upload_dir = data.get("uploadDir", data.get("UploadDir"))
        policy = data.get("policy", data.get("Policy"))
        oss_signature = data.get("ossSignature", data.get("OssSignature"))
        oss_date = data.get("ossDate", data.get("OssDate"))
        oss_security_token = data.get("ossSecurityToken", data.get("OssSecurityToken"))
        oss_credential = data.get("ossCredential", data.get("OssCredential"))

        if not all([upload_host, upload_dir, policy, oss_signature]):
            raise FileUploadError(
                f"Invalid signature response: missing required OSS upload parameters",
                file_path=file_path,
            )

        # Construct file key and upload URL
        file_key = f"{upload_dir}/{filename}"
        upload_url = upload_host
        # UploadLocation is the full OSS path: UploadDir/Filename
        upload_location = file_key

        # Upload to OSS using POST form with aiohttp
        content_type = SUPPORTED_FILE_TYPES[suffix]
        try:
            async with aiohttp.ClientSession() as session:
                with open(file_path, "rb") as f:
                    file_content = f.read()

                form_data = aiohttp.FormData()
                form_data.add_field("key", file_key)
                form_data.add_field("policy", policy)
                form_data.add_field("x-oss-signature", oss_signature)
                form_data.add_field("x-oss-date", oss_date)
                form_data.add_field("x-oss-security-token", oss_security_token)
                form_data.add_field("x-oss-credential", oss_credential)
                form_data.add_field("x-oss-signature-version", "OSS4-HMAC-SHA256")
                form_data.add_field("success_action_status", "200")
                form_data.add_field("file", file_content, filename=filename, content_type=content_type)

                async with session.post(
                    upload_url,
                    data=form_data,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as response:
                    response.raise_for_status()
        except aiohttp.ClientError as e:
            raise FileUploadError(f"Failed to upload to OSS: {e}", file_path=file_path)

        # FileId is the UploadDir itself (the unique upload path)
        file_id = upload_dir

        # Confirm upload and get the correct FileId from response
        # Note: For API_KEY auth, FileUploadCallback may fail, so we use upload_dir as file_id
        final_file_id = file_id
        try:
            callback_resp = await self._client.file_upload_callback(file_id, filename, upload_location, file_size)
            # Extract FileId from callback response - after API adapter transformation,
            # response fields become camelCase
            data_field = callback_resp.get("data", callback_resp.get("Data", {}))
            data_center_file_id = data_field.get("fileId", data_field.get("FileId"))
            if data_center_file_id:
                final_file_id = data_center_file_id
        except Exception as e:
            # If callback fails, use upload_dir as file_id (fallback)
            print(f"Warning: FileUploadCallback failed: {e}. Using upload_dir as file_id.")
            final_file_id = file_id

        return FileInfo(
            file_id=final_file_id,
            filename=filename,
            file_type=suffix.lstrip("."),
            size=file_size,
            upload_url=upload_location,
        )

    async def list_files(self, session_id: str) -> List[FileInfo]:
        """List files associated with a session asynchronously.

        Args:
            session_id: The session ID.

        Returns:
            List of FileInfo objects.
        """
        response = await self._client.list_files(session_id)
        files = response.get("Files", [])

        return [
            FileInfo(
                file_id=f.get("FileId", ""),
                filename=f.get("FileName", ""),
                file_type=f.get("FileType", ""),
                size=f.get("FileSize", 0),
                download_url=f.get("DownloadUrl"),
            )
            for f in files
        ]

    async def download_file(
        self,
        download_url: str,
        save_path: str,
        timeout: int = 60,
    ) -> str:
        """Download a file from URL asynchronously.

        Args:
            download_url: URL to download from.
            save_path: Path to save the downloaded file.
            timeout: Download timeout in seconds.

        Returns:
            Path to the saved file.

        Raises:
            FileDownloadError: If download fails.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    download_url,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as response:
                    response.raise_for_status()
                    content = await response.read()

                    with open(save_path, "wb") as f:
                        f.write(content)

            return save_path
        except aiohttp.ClientError as e:
            raise FileDownloadError(f"Failed to download file: {e}")

    async def delete_file(self, file_id: str) -> bool:
        """Delete an uploaded file asynchronously.

        Args:
            file_id: The file ID to delete.

        Returns:
            True if deletion was successful.
        """
        try:
            await self._client.delete_file(file_id)
            return True
        except Exception:
            return False
