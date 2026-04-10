from __future__ import annotations

import os
import shutil
import sqlite3
import time
from tempfile import gettempdir
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Environment variables
LOCAL_DATA = os.getenv('LOCALAPPDATA')
ROAMING = os.getenv('APPDATA')

# Chromium profile base folders (User Data only, profile selected later)
CHROMIUM_PROFILE_BASES = {
    'chrome': Path(LOCAL_DATA, 'Google', 'Chrome', 'User Data'),
    'edge': Path(LOCAL_DATA, 'Microsoft', 'Edge', 'User Data'),
    'brave': Path(LOCAL_DATA, 'BraveSoftware', 'Brave-Browser', 'User Data'),
    'brave nightly': Path(LOCAL_DATA, 'BraveSoftware', 'Brave-Browser-Nightly', 'User Data'),
    'vivaldi': Path(LOCAL_DATA, 'Vivaldi', 'User Data'),
    'arc': Path(LOCAL_DATA, 'Packages', 'TheBrowserCompany.Arc_ttt1ap7aakyb4', 'LocalCache', 'Local', 'Arc', 'User Data'),
    'thorium': Path(LOCAL_DATA, 'Thorium', 'User Data'),
    'helium': Path(LOCAL_DATA, 'imput', 'Helium', 'User Data')
}

# Single fixed path browsers
FIXED_PATHS = {
    'opera': Path(ROAMING, 'Opera Software', 'Opera Stable', 'Default', 'History')
}

FIREFOX_BASES = {
    'firefox': Path(ROAMING, 'Mozilla', 'Firefox', 'Profiles'),
    'firefox nightly': Path(ROAMING, 'Mozilla', 'Firefox', 'Profiles'),
    'zen': Path(ROAMING, 'zen', 'Profiles'),
    'floorp': Path(ROAMING, 'Floorp', 'Profiles'),
    'waterfox': Path(ROAMING, 'Waterfox', 'Profiles')
}

CHROMIUM_QUERY = 'SELECT url, title, last_visit_time FROM urls ORDER BY last_visit_time DESC'
FIREFOX_QUERY = 'SELECT url, title, visit_date FROM moz_places INNER JOIN moz_historyvisits ON moz_historyvisits.place_id = moz_places.id ORDER BY visit_date DESC'

CHROMIUM_EPOCH_OFFSET = 11644473600

class Browser:
    """Represents a single browser profile history database."""

    def __init__(
        self,
        name: str,
        query: str,
        timestamp_type: str = 'chromium',
        custom_path: Optional[Path] = None,
        dynamic_profile: bool = False,
        db_file: str = 'History',
        profile_last_updated: bool = False,
    ) -> None:
        self.name = name
        self.query = query
        self.timestamp_type = timestamp_type
        self.db_file = db_file

        # Resolve database path
        if custom_path:
            # Enforce directory-only custom path
            if not isinstance(custom_path, Path):
                custom_path = Path(custom_path)
            if not custom_path.exists() or not custom_path.is_dir():
                raise FileNotFoundError(
                    f"Custom profile directory does not exist or is not a directory: '{custom_path}'"
                )
            self.database_path = custom_path / db_file
        elif name in CHROMIUM_PROFILE_BASES:
            self.database_path = self._select_chromium_profile(
                CHROMIUM_PROFILE_BASES[name], db_file, profile_last_updated
            )
        elif name in FIREFOX_BASES:
            self.database_path = self._select_firefox_profile(
                FIREFOX_BASES[name], db_file, profile_last_updated
            )
        elif name in FIXED_PATHS:
            self.database_path = FIXED_PATHS[name]
        else:
            raise ValueError(f"Unsupported browser name: {name}")

        if not self.database_path or not self.database_path.exists():
            raise FileNotFoundError(
                f"History database not found for '{name}'. Expected: '{self.database_path}'."
            )

    def _select_chromium_profile(self, base: Path, db_file: str, last_updated: bool) -> Path:
        if not base.exists():
            return None

        candidates = [
            p / db_file
            for p in base.iterdir()
            if p.is_dir() and (p / db_file).exists() and (p.name == 'Default' or p.name.startswith('Profile '))
        ]

        if not candidates:
            return None

        return max(candidates, key=lambda p: p.stat().st_mtime) if last_updated else candidates[0]

    def _select_firefox_profile(self, base: Path, db_file: str, last_updated: bool) -> Path:
        if not base.exists():
            return None

        candidates = [
            p / db_file
            for p in base.iterdir()
            if p.is_dir() and (p / db_file).exists()
        ]

        if not candidates:
            return None

        return max(candidates, key=lambda p: p.stat().st_mtime) if last_updated else candidates[0]

    def _copy_database(self) -> str:
        """Copy the locked original DB to a uniquely named temp file for safe reading.
        Uses a stable cache file and checks modification time to avoid unnecessary copies.
        """
        tmp_dir = Path(gettempdir())
        safe_name = self.name.replace(" ", "_")
        cache_name = f"bh_{safe_name}_cache.sqlite"
        target = tmp_dir / cache_name

        # Check if already have a cached copy that is up to date
        try:
            if target.exists():
                source_mtime = self.database_path.stat().st_mtime
                target_mtime = target.stat().st_mtime
                if source_mtime <= target_mtime:
                    return str(target)
        except OSError:
            pass # Fallback to copying if stat fails

        last_err = None
        for attempt in range(3):
            try:
                shutil.copy(self.database_path, target)
                break
            except OSError as e:
                last_err = e
                # Short backoff then retry
                time.sleep(0.05 * (attempt + 1))
        else:
            raise OSError(
                f"Failed copying history DB for '{self.name}' from '{self.database_path}' to '{target}': {last_err}"
            )

        return str(target)

    def history(self, search_term: str = "", limit: int = 100) -> List['HistoryItem']:
        db_path = self._copy_database()

        # Retry opening (handle rare cases where copy completes but FS metadata not flushed)
        last_err = None
        for attempt in range(3):
            try:
                connection = sqlite3.connect(db_path)
                break
            except OSError as e:
                last_err = e
                time.sleep(0.03 * (attempt + 1))
        else:
            raise OSError(
                f"Failed to open copied history DB for '{self.name}' at '{db_path}' after retries: {last_err}"
            )

        try:
            cursor = connection.cursor()
            
            if search_term:
                search_param = f"%{search_term}%"
                base, order = self.query.split(" ORDER BY ")
                sql = f"{base} WHERE title LIKE ? OR url LIKE ? ORDER BY {order} LIMIT ?"
                cursor.execute(sql, (search_param, search_param, limit))
            else:
                cursor.execute(f"{self.query} LIMIT ?", (limit,))
                
            rows = cursor.fetchall()
        finally:
            connection.close()
        return [HistoryItem(self, *row) for row in rows]

    def convert_timestamp(self, raw_time):
        try:
            if raw_time is None:
                return datetime.fromtimestamp(0)
            if self.timestamp_type == 'chromium':
                seconds = raw_time / 1_000_000 - CHROMIUM_EPOCH_OFFSET
            elif self.timestamp_type == 'unix_us':
                seconds = raw_time / 1_000_000
            else:
                seconds = 0
            # Clamp to valid range for datetime
            if seconds < 0:
                seconds = 0
            return datetime.fromtimestamp(seconds)
        except OSError:
            # Fallback to epoch if system clock range issue
            return datetime.fromtimestamp(0)


class HistoryItem:
    """Single history row wrapper."""

    def __init__(self, browser: Browser, url: str, title: str, last_visit_time: int) -> None:
        self.browser = browser
        self.url = url
        self.title = title.strip() if title else url
        self.last_visit_time = last_visit_time

    def timestamp(self) -> datetime:
        return self.browser.convert_timestamp(self.last_visit_time)


def get(browser_name: str, custom_profile_path: Optional[str] = None, profile_last_updated: bool = False) -> Optional[Browser]:
    """Factory for Browser objects.
    Returns None if the resolved database cannot be found (FileNotFoundError).
    """
    browser_name = browser_name.lower()
    profile_last_updated = bool(profile_last_updated)

    try:
        if browser_name in CHROMIUM_PROFILE_BASES or browser_name in FIXED_PATHS:
            return Browser(browser_name, CHROMIUM_QUERY, 'chromium', profile_last_updated=profile_last_updated)
        if browser_name in FIREFOX_BASES:
            return Browser(
                browser_name,
                FIREFOX_QUERY,
                'unix_us',
                dynamic_profile=True,
                db_file='places.sqlite',
                profile_last_updated=profile_last_updated,
            )
        if browser_name == 'chromium profile':
            if not custom_profile_path:
                raise FileNotFoundError('Custom chromium profile path not provided.')
            return Browser(
                'chromium profile',
                CHROMIUM_QUERY,
                'chromium',
                custom_path=Path(custom_profile_path),
                db_file='History',
            )
        if browser_name == 'firefox profile':
            if not custom_profile_path:
                raise FileNotFoundError('Custom firefox profile path not provided.')
            return Browser(
                'firefox profile',
                FIREFOX_QUERY,
                'unix_us',
                custom_path=Path(custom_profile_path),
                db_file='places.sqlite',
            )
        raise ValueError(f"Unsupported browser: {browser_name}")
    except FileNotFoundError:
        return None