"""Download and extract convert_statistics.json from conversion result OSS zip.

The LHM conversion result is delivered as an OSS zip package referenced by
`download_url` in the conversion response. The package contains
`metadata/convert_statistics.json`, which holds the structured statistics used
to generate the result summary (see design doc §3.3 / §5).

The full zip is also extracted to <session-dir>/output/ds-cli/result/ for
persistence, where <session-dir> is the session temp directory shared with the
session config (default /tmp/lhm-sch-session-<uid>/).
"""

import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.error import URLError
from urllib.request import urlopen

from lhm_read_exec_cli import credentials as credential_file

STATISTICS_ENTRY_NAME = "metadata/convert_statistics.json"
DOWNLOAD_TIMEOUT_SECONDS = 60


def _output_result_dir() -> Path:
    """Result output directory inside the session temp dir (same root as session.json)."""
    return credential_file.session_dir_path() / "output" / "ds-cli" / "result"


class StatisticsLoadError(Exception):
    """Raised when statistics cannot be downloaded, extracted, or parsed."""


def _download_zip(download_url: str, dest_path: str) -> None:
    """Download the conversion result zip to a local path.

    Args:
        download_url: OSS download URL from conversion response.
        dest_path: Local file path to write the zip to.

    Raises:
        StatisticsLoadError: On network or IO failure.
    """
    try:
        with urlopen(download_url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
            with open(dest_path, "wb") as output_file:
                output_file.write(response.read())
    except (URLError, OSError, ValueError) as download_error:
        raise StatisticsLoadError(
            f"Failed to download conversion result: {download_error}"
        ) from download_error


def _extract_statistics(zip_path: str) -> Dict[str, Any]:
    """Extract and parse convert_statistics.json from the result zip.

    Args:
        zip_path: Local path to the downloaded zip.

    Returns:
        Parsed convert_statistics.json content.

    Raises:
        StatisticsLoadError: If entry missing or JSON malformed.
    """
    try:
        with zipfile.ZipFile(zip_path) as archive:
            entry_names = set(archive.namelist())
            if STATISTICS_ENTRY_NAME not in entry_names:
                raise StatisticsLoadError(
                    f"'{STATISTICS_ENTRY_NAME}' not found in conversion result zip"
                )
            raw_content = archive.read(STATISTICS_ENTRY_NAME)
    except zipfile.BadZipFile as zip_error:
        raise StatisticsLoadError(
            f"Conversion result is not a valid zip: {zip_error}"
        ) from zip_error

    try:
        return json.loads(raw_content)
    except (json.JSONDecodeError, TypeError) as parse_error:
        raise StatisticsLoadError(
            f"Failed to parse convert_statistics.json: {parse_error}"
        ) from parse_error


def load_convert_statistics(
    download_url: str,
    oss_download_url: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Download result zips, extract to persistent directory, and return statistics.

    Downloads the conversion result zip from OSS (and optionally the full export
    package via oss_download_url), extracts all contents to
    <session-dir>/output/ds-cli/result/, and returns the parsed
    convert_statistics.json with injected metadata fields.

    Args:
        download_url: OSS download URL for statistics zip from conversion response.
        oss_download_url: Optional OSS download URL for the full export package.
        output_dir: Deprecated, kept for API compatibility. Extraction always
            goes to <session-dir>/output/ds-cli/result/.

    Returns:
        Parsed statistics dict with `_extraction_dir` and `_oss_package_path` fields,
        or None if download_url is empty.

    Raises:
        StatisticsLoadError: On download, extraction, or parse failure.
    """
    if not download_url:
        return None

    result_dir = _output_result_dir()

    # Clean up previous results before downloading new files
    if result_dir.exists():
        shutil.rmtree(result_dir)
    result_dir.mkdir(parents=True, exist_ok=True)

    # Download statistics zip to temporary file first
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        stats_tmp_path = tmp.name

    oss_package_local_path: Optional[str] = None

    try:
        _download_zip(download_url, stats_tmp_path)

        # Extract statistics zip directly to result directory (no subdirectory)
        try:
            with zipfile.ZipFile(stats_tmp_path) as archive:
                archive.extractall(result_dir)
        except zipfile.BadZipFile as zip_error:
            raise StatisticsLoadError(
                f"Conversion result is not a valid zip: {zip_error}"
            ) from zip_error

        # Download full export package if oss_download_url is provided
        if oss_download_url:
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as oss_tmp:
                oss_tmp_path = oss_tmp.name
            try:
                _download_zip(oss_download_url, oss_tmp_path)
                # Save the full export package directly to result directory
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                oss_package_filename = f"export_package_{timestamp}.zip"
                oss_package_dest = result_dir / oss_package_filename
                os.rename(oss_tmp_path, str(oss_package_dest))
                oss_package_local_path = str(oss_package_dest.resolve())
            except StatisticsLoadError:
                # Non-fatal: log but don't fail the entire operation
                pass
            finally:
                if os.path.exists(oss_tmp_path):
                    os.unlink(oss_tmp_path)

        # Extract and parse statistics
        stats = _extract_statistics(stats_tmp_path)

        # Inject metadata into statistics for rendering
        if stats is not None:
            stats["_extraction_dir"] = str(result_dir.resolve())
            if oss_package_local_path:
                stats["_oss_package_path"] = oss_package_local_path

        return stats
    finally:
        # Clean up temporary statistics file
        if os.path.exists(stats_tmp_path):
            os.unlink(stats_tmp_path)
