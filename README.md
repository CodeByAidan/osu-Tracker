# osu!Tracker

<h3 align="center"><b><i>Better</i></b> <i>Discord Rich Presence for osu!</i></h3>

<p align="center">
   <img width="463" height="470" alt="osu!Tracker settings" src="https://github.com/user-attachments/assets/3cd37895-58c2-4632-a701-ecd7749fa334" />
</p>
<p align="center">
   <img width="322" height="135" alt="osu!Tracker Discord Rich Presence" src="https://github.com/user-attachments/assets/c10620ca-b122-4155-8367-75517437976a" />
   <img width="308" height="139" alt="osu!Tracker activity display" src="https://github.com/user-attachments/assets/6303cf7d-483d-4dbe-94da-5c8977f088af" />
</p>

<p align="center">
A Windows desktop app that tracks osu! in-game statistics and displays them in
Discord Rich Presence.
</p>

## Requirements

- Windows 10 or newer (sorry, no Linux or macOS support right now)
- Python 3.10 or later
- [Tosu!](https://tosu.app/) installed on your system

## Installation

1. Download `osu-tracker.exe` from the latest [GitHub release](https://github.com/user-attachments/releases) or [build it yourself](#building-a-executable).
2. Start Tosu! and confirm its local API is available (normally
   `http://127.0.0.1:24050/json`).
3. Open `osu-tracker.exe`.
4. Enter your Discord application ID in the app, if you want Discord Rich
   Presence, then select **Save settings** and **Start tracking**.

   > Create a Discord application in the [Discord Developer Portal](https://discord.com/developers/applications)
   > and copy its Client ID from **OAuth2**.
   > <img src="images/client-id-discord-location.png" alt="Discord client ID location" width="650">

> **Important:** Turn off Osu!'s in-game Discord Rich Presence before running
> osu!Tracker to prevent conflicting activities.
>
> <img src="images/osu-in-game-rpc-location.png" alt="Osu! in-game Discord Rich Presence setting" width="468">

## Use the app

The Discord **Details** and **State** dropdowns can use the gameplay summary, activity
state, map metadata, mods, accuracy, PP, combo, score, player name, star
rating, or BPM. Settings can be changed at any time and apply on the next
start (or after a restart).

![osu!Tracker settings](images/osu-tracker-settings.png)

## Command line (optional)

Make sure to install in a virtual environment the package in editable mode first!

```powershell
pip install -e .
```

The normal command opens the desktop app. For automation and troubleshooting,
the command-line interface is available:

```powershell
osu-tracker-cli --once --no-discord
```

Run `osu-tracker-cli --help` for all CLI options. `--configure` and
`--show-settings` continue to manage the same saved settings file.

## Building a executable

Clone the repository, open PowerShell in the project folder, then run:

```powershell
.\scripts\build-windows.ps1
```

The script installs the project and PyInstaller, then creates the executable at:

```text
dist\osu-tracker.exe
```

To use a specific Python command, pass it explicitly:

```powershell
.\scripts\build-windows.ps1 -Python py
```

## Documentation

See [docs/tosu-data.md](docs/tosu-data.md) for the complete Pydantic model
reference, common field lookups, and examples.
