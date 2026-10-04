Comic Carousel Generator

OPEN THE APPLICATION
--------------------
- macOS: double-click "run.command".
- Linux: run "./run.sh".
- Windows: run ".\run.ps1".

Your browser opens by itself. The first launch downloads a private copy of Python and two
libraries, which needs a network connection and takes about a minute. Nothing is installed
system-wide.

This release needs "uv" on your computer. If it is missing, the launcher prints the one
install command and stops. The native launcher images described in app/launcher/manifest.json
are not built yet; they are the next milestone and will remove that requirement.

USE IT
------
Press "Choose a folder", pick the folder holding your scans, and wait. Every image in that
folder is processed. Each scan gets its own folder beside it, named after it, for example
"brain tumor raw-carousel-001", holding one 1080x1350 PNG per panel plus summary.png.
Nothing is ever overwritten. "Choose scans" does the same for hand-picked files.

Tick "Show me the boxes before exporting" to check the panels first. That editor also opens
by itself for a scan the app is unsure about, and the row says why.

RECOVERY
--------
Keep the launcher beside the "app" directory. If the browser does not open, the terminal
window prints the exact address to paste. Press Quit in the page, or close the terminal, to
stop it.

Application data: none yet. Exports go where you choose; the app keeps no database.
Logs: the terminal window the launcher opened.
Support contact: goosnav.com
