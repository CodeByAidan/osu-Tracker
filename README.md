# osu!Tracker

#### **_Better_** _Discord Rich Presence for osu!_

A Python application that tracks osu! in-game statistics and displays as a Discord Rich Presence.

## Requirements

- Python 3.10 or higher
- [Tosu!](https://tosu.app/) installed on your system

## Installation

1. Install Python 3.10 or higher from [python.org](https://www.python.org/downloads/).
2. Clone this repository or download the source code as a ZIP file and extract it.
3. Open a terminal or command prompt in the project directory.
4. Install the package in editable mode (in a virtual environment):

   ```bash
   pip install -e .
   ```

5. **Start Tosu!** and confirm that its local API is available.

6. Create a Discord application at the [Discord Developer Portal](https://discord.com/developers/applications), copy its Application ID, and set it in your shell:

   ```powershell
   $env:DISCORD_CLIENT_ID = "your-application-id"
   ```

   The application must be running in the Discord desktop client. The default
   `osu` large image can be replaced by an asset with the same key in the
   Discord application's Rich Presence art settings.

## Run the application:

> **Important:** Turn off osu!'s in-game Discord Rich Presence before running
> osu!Tracker to prevent conflicting activities.
>
> ![Osu! in-game Discord Presence](images/image.png)

```bash
python -m OsuTracker
```

After installation, the console script can also be used:

```bash
osu-tracker
```

The tracker polls Tosu every five seconds and prints the latest JSON snapshot.
Use `python -m OsuTracker --once` to fetch one snapshot and exit, or pass
`--endpoint` and `--interval` to override the defaults.

With `DISCORD_CLIENT_ID` set, the tracker also publishes the current map,
difficulty, accuracy, and PP to Discord. While a beatmap is playing, its cover
art is shown in the activity and links to its osu! beatmap page. Use
`--no-discord` to run without RPC, or pass `--client-id YOUR_APPLICATION_ID`
for a one-off override.

The activity shows `Playing` while the beatmap clock advances, `Paused` when
the clock stops during gameplay, and `Scrolling for a new song` on other Tosu
screens.

## Features

- Read the current osu! state from Tosu's local JSON API.
- Poll continuously or fetch a single snapshot.
- Report unavailable Tosu connections without a traceback.

## Documentation

See [docs/tosu-data.md](docs/tosu-data.md) for the complete Pydantic model
reference, common field lookups, and examples.
