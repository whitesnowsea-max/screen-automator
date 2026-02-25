"""GitHub-based auto-update module for Screen Automator."""
import json
import os
import shutil
import tempfile
import threading
import zipfile
from typing import Callable, Optional, Tuple
from urllib import request, error


class UpdateInfo:
    """Holds information about an available update."""
    __slots__ = ("version", "download_url", "release_url", "description")

    def __init__(self, version: str, download_url: str, release_url: str, description: str = ""):
        self.version = version
        self.download_url = download_url
        self.release_url = release_url
        self.description = description


def _parse_version(v: str) -> tuple:
    """Parse version string like '2.1.0' into comparable tuple (2, 1, 0)."""
    v = v.lstrip("vV")
    parts = []
    for p in v.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def check_update(
    current_version: str,
    github_repo: str,
    timeout: float = 10.0,
) -> Optional[UpdateInfo]:
    """
    Check GitHub Releases for a newer version.

    Args:
        current_version: Current app version (e.g. '2.1.0')
        github_repo: GitHub repo in 'owner/repo' format
        timeout: Request timeout in seconds

    Returns:
        UpdateInfo if a newer version exists, None otherwise.
    """
    api_url = f"https://api.github.com/repos/{github_repo}/releases/latest"
    req = request.Request(api_url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "ScreenAutomator-Updater",
    })

    try:
        with request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (error.URLError, error.HTTPError, json.JSONDecodeError, OSError):
        return None

    tag = data.get("tag_name", "")
    latest = _parse_version(tag)
    current = _parse_version(current_version)

    if latest <= current:
        return None

    # Find zip asset in release assets
    download_url = ""
    for asset in data.get("assets", []):
        name = asset.get("name", "").lower()
        if name.endswith(".zip"):
            download_url = asset.get("browser_download_url", "")
            break

    # Fallback to source zip if no asset found
    if not download_url:
        download_url = data.get("zipball_url", "")

    return UpdateInfo(
        version=tag.lstrip("vV"),
        download_url=download_url,
        release_url=data.get("html_url", ""),
        description=data.get("body", ""),
    )


def check_update_async(
    current_version: str,
    github_repo: str,
    callback: Callable[[Optional[UpdateInfo]], None],
):
    """
    Check for updates in a background thread.

    Args:
        current_version: Current version string
        github_repo: GitHub 'owner/repo'
        callback: Called with UpdateInfo or None when check completes.
                  This will be called from the background thread.
    """
    def _worker():
        result = check_update(current_version, github_repo)
        callback(result)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def download_and_apply_update(
    update_info: UpdateInfo,
    app_dir: str,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> Tuple[bool, str]:
    """
    Download a release zip and replace app files.

    Preserves:
      - config/  (user settings)
      - templates/  (user captured images)
      - venv/  (virtual environment)

    Args:
        update_info: UpdateInfo with download URL
        app_dir: Path to the current app directory
        progress_callback: Optional callback for status messages

    Returns:
        (success: bool, message: str)
    """
    def _log(msg: str):
        if progress_callback:
            progress_callback(msg)

    if not update_info.download_url:
        return False, "다운로드 URL이 없습니다."

    try:
        # 1. Download zip to temp file
        _log("📥 업데이트 다운로드 중...")
        tmp_dir = tempfile.mkdtemp(prefix="sa_update_")
        zip_path = os.path.join(tmp_dir, "update.zip")

        req = request.Request(update_info.download_url, headers={
            "User-Agent": "ScreenAutomator-Updater",
        })
        with request.urlopen(req, timeout=60) as resp:
            with open(zip_path, "wb") as f:
                f.write(resp.read())

        _log("📦 압축 해제 중...")
        # 2. Extract zip
        extract_dir = os.path.join(tmp_dir, "extracted")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        # Find the actual root directory inside the zip
        # (GitHub zips often have a single root folder)
        entries = os.listdir(extract_dir)
        if len(entries) == 1 and os.path.isdir(os.path.join(extract_dir, entries[0])):
            source_dir = os.path.join(extract_dir, entries[0])
        else:
            source_dir = extract_dir

        # 3. Preserve user data directories
        preserve_dirs = {"config", "templates", "venv", ".git"}
        preserve_files = set()

        _log("🔄 파일 교체 중...")
        # 4. Copy new files over existing ones
        for root, dirs, files in os.walk(source_dir):
            rel_root = os.path.relpath(root, source_dir)

            # Skip preserved directories
            dirs[:] = [d for d in dirs if d not in preserve_dirs]

            for fname in files:
                rel_path = os.path.join(rel_root, fname) if rel_root != "." else fname
                src_file = os.path.join(root, fname)
                dst_file = os.path.join(app_dir, rel_path)

                # Create parent directories
                dst_parent = os.path.dirname(dst_file)
                os.makedirs(dst_parent, exist_ok=True)

                # Copy file
                shutil.copy2(src_file, dst_file)

        # 5. Cleanup temp files
        shutil.rmtree(tmp_dir, ignore_errors=True)

        _log(f"✅ v{update_info.version} 업데이트 완료!")
        return True, f"v{update_info.version}으로 업데이트되었습니다.\n프로그램을 재시작해주세요."

    except Exception as e:
        return False, f"업데이트 실패: {str(e)}"


def download_and_apply_async(
    update_info: UpdateInfo,
    app_dir: str,
    callback: Callable[[bool, str], None],
    progress_callback: Optional[Callable[[str], None]] = None,
):
    """
    Download and apply update in a background thread.

    Args:
        update_info: UpdateInfo from check_update
        app_dir: Current application directory
        callback: Called with (success, message) when done
        progress_callback: Called with status messages during download
    """
    def _worker():
        success, msg = download_and_apply_update(
            update_info, app_dir, progress_callback
        )
        callback(success, msg)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
