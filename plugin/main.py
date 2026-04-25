from flox import Flox, ICON_HISTORY, ICON_BROWSER, ICON_FILE
import pyperclip
import browsers
from urllib.parse import urlparse
import platform
import shutil
from pathlib import Path

# Constants
HISTORY_GLYPH = ""
CUSTOM_PROFILE = "custom profile"


class BrowserHistory(Flox):

    def __init__(self):
        super().__init__()

        # Get the exact Flow Launcher Settings/Plugins/BrowserHistory folder
        self.cache_dir = Path(self.settings_path).parent / "Cache"

        current_pc = platform.node()
        saved_pc = self.settings.get("last_computer_name", "")

        # If the computer name changed (e.g., Portable mode moved to a new PC), wipe the cache
        if current_pc != saved_pc:
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir, ignore_errors=True)
            self.settings["last_computer_name"] = current_pc

        # Ensure the cache directory exists for this session
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Read the unified dropdown
        self.default_browser = self.settings.get(
            "default_browser", "All Browsers"
        ).lower()
        self.all_browsers_history = self.default_browser == "all browsers"

        self.custom_profile_path = self.settings.get("custom_profile_path", "")
        self.history_limit = int(self.settings.get("history_limit", 1000))

        # Determine profile handling from the new dropdown setting
        profile_mode = self.settings.get("profile_search_mode", "Active Profile")
        self.search_all_profiles = profile_mode == "All Profiles"
        self.profile_last_updated = profile_mode == "Active Profile"

        blocked_domains_str = self.settings.get("blocked_domains") or ""
        self.blocked_domains = [
            domain.strip().lower()
            for domain in blocked_domains_str.split(",")
            if domain.strip()
        ]
        self.init_error = None

        # Initialize browser(s) array uniformly
        self.browsers = []

        if self.all_browsers_history:
            browser_names = (
                list(browsers.CHROMIUM_PROFILE_BASES.keys())
                + list(browsers.FIREFOX_BASES.keys())
                + list(browsers.FIXED_PATHS.keys())
            )
        else:
            browser_names = [self.default_browser]

        for browser_name in browser_names:
            # Handle the manual custom profile choice robustly
            if browser_name == CUSTOM_PROFILE:
                if not self.custom_profile_path:
                    self.init_error = "Custom Profile selected, but no directory path was provided in settings."
                    continue
                try:
                    if self.search_all_profiles:
                        profiles = browsers.get_all_profiles(
                            browser_name,
                            self.cache_dir,
                            custom_profile_path=self.custom_profile_path,
                        )
                        if profiles:
                            self.browsers.extend(profiles)
                    else:
                        b = browsers.get(
                            browser_name,
                            self.cache_dir,
                            custom_profile_path=self.custom_profile_path,
                            profile_last_updated=self.profile_last_updated,
                        )
                        if b:
                            self.browsers.append(b)
                except Exception as e:
                    self.init_error = str(e)  # Bubbles the exact error up to the UI
                continue

            # Auto-detect standard profiles or search all
            if self.search_all_profiles:
                self.browsers.extend(
                    browsers.get_all_profiles(browser_name, self.cache_dir)
                )
            else:
                b = browsers.get(
                    browser_name,
                    self.cache_dir,
                    profile_last_updated=self.profile_last_updated,
                )
                if b:
                    self.browsers.append(b)

        # In "All Browsers" mode, if a custom path is ALSO provided, append it
        if self.all_browsers_history and self.custom_profile_path:
            try:
                if self.search_all_profiles:
                    b_custom_list = browsers.get_all_profiles(
                        CUSTOM_PROFILE,
                        self.cache_dir,
                        custom_profile_path=self.custom_profile_path,
                    )
                    self.browsers.extend(b_custom_list)
                else:
                    b_custom = browsers.get(
                        CUSTOM_PROFILE,
                        self.cache_dir,
                        custom_profile_path=self.custom_profile_path,
                        profile_last_updated=self.profile_last_updated,
                    )
                    if b_custom:
                        self.browsers.append(b_custom)
            except Exception:
                pass  # Fail silently for the background custom injection so that don't block normal browsers

        # Different browser variants can resolve to the same profile database path.
        # Keep only the first instance per resolved DB path to avoid duplicate reads/caches.
        unique_browsers = []
        seen_db_paths = set()
        for browser in self.browsers:
            try:
                db_key = str(browser.database_path.resolve()).lower()
            except Exception:
                db_key = str(browser.database_path).lower()

            if db_key in seen_db_paths:
                continue

            seen_db_paths.add(db_key)
            unique_browsers.append(browser)

        self.browsers = unique_browsers

        if not self.browsers and not self.init_error:
            self.init_error = (
                "Could not locate any supported browser profile databases."
            )

    def _is_domain_blocked(self, url):
        """Check if the domain of the given URL is in the blocked domains list."""
        if not self.blocked_domains:
            return False
        try:
            domain = urlparse(url).netloc.lower()
            return any(
                blocked_domain in domain for blocked_domain in self.blocked_domains
            )
        except Exception:
            return False

    def query(self, query):
        if not self.browsers:
            self.add_item(
                title="Browser not available",
                subtitle=self.init_error or "Unknown error initializing browser.",
            )
            return

        try:
            source_items = self._get_combined_history(query)

            if getattr(self, "_warnings", None):
                self.add_item(
                    title="Some browsers or profiles were skipped",
                    subtitle="; ".join(self._warnings)[:150],
                    icon=ICON_BROWSER,
                )

            for idx, item in enumerate(source_items):
                time_str = item.timestamp().strftime("%b %d, %Y %I:%M %p")

                self.add_item(
                    title=item.title,
                    subtitle=f"[{time_str}] {item.url}",
                    icon=ICON_HISTORY,
                    glyph=HISTORY_GLYPH,
                    method=self.browser_open,
                    parameters=[item.url],
                    context=[item.title, item.url],
                )
        except Exception as e:
            self.add_item(
                title="An error occurred",
                subtitle=str(e),
            )

    def _get_combined_history(self, query):
        combined_history = []
        self._warnings = []

        for browser in self.browsers:
            try:
                combined_history.extend(
                    browser.history(search_term=query, limit=self.history_limit)
                )
            except FileNotFoundError:
                continue
            except OSError as e:
                self._warnings.append(f"{browser.name}: {e}")
                continue

        seen_urls = set()
        unique_history = []
        for item in combined_history:
            if item.url not in seen_urls and not self._is_domain_blocked(item.url):
                unique_history.append(item)
                seen_urls.add(item.url)

        unique_history.sort(key=lambda x: x.timestamp(), reverse=True)

        return unique_history

    def context_menu(self, data):
        self.add_item(
            title="Open in browser",
            subtitle=data[0],
            icon=ICON_BROWSER,
            method=self.browser_open,
            parameters=[data[1]],
        )
        self.add_item(
            title="Copy to clipboard",
            subtitle=data[1],
            icon=ICON_FILE,
            method=self.copy_to_clipboard,
            parameters=[data[1]],
        )

    def copy_to_clipboard(self, data):
        pyperclip.copy(data)
        self.show_msg("Copied!", f"{data}")

    def run(self):
        pass


if __name__ == "__main__":
    BrowserHistory().run()
