from flox import Flox, ICON_HISTORY, ICON_BROWSER, ICON_FILE
import pyperclip
import browsers
from urllib.parse import urlparse

# Constants
HISTORY_GLYPH = ''
DEFAULT_BROWSER = 'chrome'
CUSTOM_CHROMIUM = 'chromium profile'
CUSTOM_FIREFOX = 'firefox profile'


class BrowserHistory(Flox):

    def __init__(self):
        super().__init__()
        self.default_browser = self.settings.get('default_browser', DEFAULT_BROWSER).lower()
        self.custom_profile_path = self.settings.get('custom_profile_path', '')
        self.profile_last_updated = self.settings.get('profile_last_updated', False)
        self.all_browsers_history = self.settings.get('all_browsers_history', False)
        # Default limit changed to 1000 to match the SettingsTemplate.yaml
        self.history_limit = int(self.settings.get('history_limit', 1000)) 
        blocked_domains_str = self.settings.get('blocked_domains') or ''
        self.blocked_domains = [domain.strip().lower() for domain in blocked_domains_str.split(',') if domain.strip()]
        self.init_error = None  # Store any initialization error to display in query()

        # Initialize browser(s)
        if self.all_browsers_history:
            self.browsers = [
                browsers.get(browser_name, profile_last_updated=self.profile_last_updated)
                for browser_name in browsers.CHROMIUM_PROFILE_BASES.keys() | browsers.FIREFOX_BASES.keys()
            ]

            # Include custom browsers if a custom profile path is provided
            if self.custom_profile_path:
                custom_chromium = browsers.get(CUSTOM_CHROMIUM, custom_profile_path=self.custom_profile_path, profile_last_updated=self.profile_last_updated)
                custom_firefox = browsers.get(CUSTOM_FIREFOX, custom_profile_path=self.custom_profile_path, profile_last_updated=self.profile_last_updated)

                if custom_chromium:
                    self.browsers.append(custom_chromium)
                if custom_firefox:
                    self.browsers.append(custom_firefox)

            # Filter out None values (browsers with missing profiles)
            self.browsers = [browser for browser in self.browsers if browser is not None]
        else:
            # Validate custom profile path requirement
            if self.default_browser in (CUSTOM_CHROMIUM, CUSTOM_FIREFOX) and not self.custom_profile_path:
                self.browser = None
                self.init_error = "You selected a custom profile, but no folder path was provided in settings."
            else:
                self.browser = browsers.get(
                    self.default_browser,
                    custom_profile_path=self.custom_profile_path,
                    profile_last_updated=self.profile_last_updated
                )
                if self.browser is None:
                    self.init_error = f"Default browser '{self.default_browser}' not found or its profile/database is missing."

    def _is_domain_blocked(self, url):
        """Check if the domain of the given URL is in the blocked domains list."""
        if not self.blocked_domains:
            return False
        try:
            domain = urlparse(url).netloc.lower()
            return any(blocked_domain in domain for blocked_domain in self.blocked_domains)
        except Exception: # explicitly catch Exception to avoid swallowing system exits
            return False

    def query(self, query):
        try:
            # Surface any initialization error immediately
            if not self.all_browsers_history and (self.browser is None or self.init_error):
                self.add_item(
                    title='Browser not available',
                    subtitle=self.init_error or 'Unknown error initializing browser.'
                )
                return

            if self.all_browsers_history and (not hasattr(self, 'browsers') or not self.browsers):
                self.add_item(
                    title='No browser histories found',
                    subtitle='Could not locate any supported browser profile databases.'
                )
                return

            source_items = []
            if self.all_browsers_history:
                source_items = self._get_combined_history(query)
                if getattr(self, '_warnings', None):
                    self.add_item(
                        title='Some browsers were skipped',
                        subtitle='; '.join(self._warnings)[:150],
                        icon=ICON_BROWSER
                    )
            else:
                # Pass query to the database layer directly
                history_items = self.browser.history(search_term=query, limit=self.history_limit) if self.browser else []
                source_items = [h for h in history_items if not self._is_domain_blocked(h.url)]

            for idx, item in enumerate(source_items):
                # Format the datetime object to a 12-hour format string (e.g., '2026-04-10 02:30 PM')
                time_str = item.timestamp().strftime('%Y-%m-%d %I:%M %p')
                
                self.add_item(
                    title=item.title,
                    subtitle=f"[{time_str}] {item.url}",
                    icon=ICON_HISTORY,
                    glyph=HISTORY_GLYPH,
                    method=self.browser_open,
                    parameters=[item.url],
                    context=[item.title, item.url]
                )
        except Exception as e:
            self.add_item(
                title='An error occurred',
                subtitle=str(e),
            )

    def _get_combined_history(self, query):
        """Combine histories from all browsers, deduplicate, and sort."""
        combined_history = []
        self._warnings = []
        for browser in self.browsers:
            try:
                # Let SQLite handle the searching
                combined_history.extend(browser.history(search_term=query, limit=self.history_limit))
            except FileNotFoundError:
                continue  # Skip browsers with missing databases
            except OSError as e:
                # Collect problematic browsers but do not abort whole aggregation
                self._warnings.append(f"{browser.name}: {e}")
                continue

        # Deduplicate by URL and filter domains simultaneously
        seen_urls = set()
        unique_history = []
        for item in combined_history:
            if item.url not in seen_urls and not self._is_domain_blocked(item.url):
                unique_history.append(item)
                seen_urls.add(item.url)

        # Sort by normalized timestamp (most recent first)
        unique_history.sort(key=lambda x: x.timestamp(), reverse=True)

        return unique_history

    def context_menu(self, data):
        self.add_item(
            title='Open in browser',
            subtitle=data[0],
            icon=ICON_BROWSER,
            method=self.browser_open,
            parameters=[data[1]],
        )
        self.add_item(
            title='Copy to clipboard',
            subtitle=data[1],
            icon=ICON_FILE,
            method=self.copy_to_clipboard,
            parameters=[data[1]],
        )

    def copy_to_clipboard(self, data):
        pyperclip.copy(data)
        self.show_msg("Copied!", f"{data}")

    def run(self):
        """
        Entry point for Flow Launcher.
        This method is required to start the plugin.
        """
        pass  # Ensure this method exists


if __name__ == "__main__":
    BrowserHistory().run()