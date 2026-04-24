# Browser History V2 Plugin for Flow Launcher

The Browser History Plugin allows you to search your past web browsing directly from Flow Launcher. Whether you need to find an article you read yesterday or a website you visited weeks ago, this tool helps you find it instantly just by typing.

## Features

* **Universal Search:** Search across all your installed browsers at the same time.
* **Multi-Word Search:** Type words in any order to find what you are looking for (e.g., typing "youtube music" will easily find a page titled "Music - YouTube").
* **Broad Compatibility:** Works automatically with Chrome, Firefox, Edge, Brave, Opera, Vivaldi, Arc, and many others.
* **Profile Support:** If you share a computer or use separate "Work" and "Personal" browser profiles, the plugin can automatically detect the one you used most recently, or you can choose to search all of your profiles at once. 
* **Hide Websites:** You can block specific websites (like social media or video streaming sites) so they don't clutter up your search results.

## Installation

The easiest way to install this plugin is directly through Flow Launcher.

**Standard Installation (Recommended):**
1. Open Flow Launcher.
2. Open your Flow Launcher Settings and click on the **Plugin Store** tab.
3. Search for **Browser History V2**.
4. Click **Install**. 

**Manual Installation:**
1. Download [latest release](https://github.com/fahim-ahmed05/browser-history-v2/releases/latest/download/browser-history-v2.zip) from GitHub.
2. Open Flow Launcher **Settings** and go to **Plugin Store**.
3. Click on Install **plugin from local path button** on the top right corner.
4. Select the downloaded `.zip` file and click **Open**.
5. Restart Flow Launcher.

## Configuration

For most people, the plugin will work perfectly right out of the box. However, you can customize how it works by going into the plugin's settings in Flow Launcher. 

Here is what each setting does:

* **Browser Selection:** By default, this is set to "All Browsers". You can change this if you only want to search one specific browser or a custom profile.
* **Profile Search Mode:** Choose how the plugin handles browsers with multiple user profiles:
    * **Active Profile:** Searches only the history of the profile you used most recently.
    * **All Profiles:** Searches the history of every profile within the browser at the same time.
* **Custom Profile Directory:** You can ignore this unless you selected "Custom Profile" in the first setting. Point this to the folder containing your profile data, and the plugin will automatically detect how to read it.
* **History Limit:** This is the maximum number of past websites the plugin will load per profile. The default is 1,000. If Flow Launcher feels slow when you type, try lowering this number. 
* **Blocked Domains:** Type in the web addresses of any sites you don't want showing up in your search results. Separate them with commas (for example: `facebook.com, twitter.com, youtube.com`).

## Privacy & Data Handling

To prevent search errors while your browser is open and actively locking the history database, this plugin creates a temporary read-only copy of the database to perform searches. 

**Privacy Features:**
* **Local Storage:** The cached databases are stored securely inside Flow Launcher's designated User Data directory (`%APPDATA%\FlowLauncher\Settings\Plugins\Browser History V2`). If you uninstall or remove the plugin, the cache is automatically deleted with it.
* **Portable Mode Security:** If you run Flow Launcher in Portable Mode on a USB drive, the plugin continuously monitors the name of the host computer. If the computer name changes, the plugin automatically wipes the cache folder to ensure your private history data does not accidentally travel to or get exposed on a different machine.

> [!WARNING]
>
> If you sync your Flow Launcher user data folder (`%APPDATA%\FlowLauncher`) or portable installation folder using a cloud sync provider (e.g., OneDrive, Dropbox, Google Drive), please be aware that the `Cache` folder containing your temporary browser history database **will also be synced and uploaded** to your cloud provider. If you want to keep your history strictly local to your current machine, you should exclude the `Settings\Plugins\Browser History V2\Cache` folder from your sync configuration.

## Troubleshooting

**The plugin isn't showing any results.**
* Make sure you have actually browsed the web on this computer so there is a history to search.
* If you are an advanced user using a "Custom Profile Directory," make sure you pointed the setting to the exact folder containing your database files (like `History` or `places.sqlite`).

**Typing in Flow Launcher feels slow or laggy.**
* You might have too much history loading at once. Go to the plugin settings and lower the **History Limit** (try changing it from 1000 to 500).
* Alternatively, change your Browser Selection from "All Browsers" to a single specific browser so the plugin has less data to sort through.

**It's pulling up websites I don't want to see.**
* Use the **Blocked Domains** setting to hide those specific websites.

## Reporting Issues

If the plugin isn't working as expected, or if you have an idea to make it better, please let us know on GitHub:

1. Go to the **Issues** tab on our GitHub page.
2. Click **New Issue**.
3. Describe what is going wrong. If you are seeing an error message in Flow Launcher, please include what it says. 

*Tip: Take a quick look at the other issues first to see if someone has already reported the same problem.*