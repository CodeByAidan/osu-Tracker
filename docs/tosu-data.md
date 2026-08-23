# Tosu Data Reference

The `Model` class in `OsuTracker.models` represents the JSON returned by Tosu at
`http://127.0.0.1:24050/json`. The tracker validates a response like this:

```python
from OsuTracker.__main__ import fetch_tosu_data
from OsuTracker.models import Model

raw_data = fetch_tosu_data()
state = Model.model_validate(raw_data)
```

Pydantic converts the JSON into objects. Use dot notation for normal fields.
The model accepts both JSON aliases and Python field names.

## Common Lookups

| What you need              | Python expression                                        |
| -------------------------- | -------------------------------------------------------- |
| Player name                | `state.gameplay.name`                                    |
| Current score              | `state.gameplay.score`                                   |
| Current PP                 | `state.gameplay.pp.current`                              |
| Full-combo PP              | `state.gameplay.pp.fc`                                   |
| Maximum PP this play       | `state.gameplay.pp.maxThisPlay`                          |
| Current combo              | `state.gameplay.combo.current`                           |
| Maximum combo              | `state.gameplay.combo.max`                               |
| Accuracy                   | `state.gameplay.accuracy`                                |
| Health                     | `state.gameplay.hp.normal` or `state.gameplay.hp.smooth` |
| Mods                       | `state.menu.mods.str`                                    |
| Mod bitmask                | `state.menu.mods.num`                                    |
| Map artist                 | `state.menu.bm.metadata.artist`                          |
| Map title                  | `state.menu.bm.metadata.title`                           |
| Map difficulty             | `state.menu.bm.metadata.difficulty`                      |
| Mapper                     | `state.menu.bm.metadata.mapper`                          |
| Beatmap ID                 | `state.menu.bm.id`                                       |
| Beatmap set ID             | `state.menu.bm.set`                                      |
| Star rating                | `state.menu.bm.stats.SR`                                 |
| Approach rate              | `state.menu.bm.stats.AR`                                 |
| Circle size                | `state.menu.bm.stats.CS`                                 |
| Overall difficulty         | `state.menu.bm.stats.OD`                                 |
| HP drain                   | `state.menu.bm.stats.HP`                                 |
| Current BPM                | `state.menu.bm.stats.BPM.realtime`                       |
| BPM range                  | `state.menu.bm.stats.BPM.min` and `.max`                 |
| 300 hits                   | `state.gameplay.hits.field_300`                          |
| 100 hits                   | `state.gameplay.hits.field_100`                          |
| 50 hits                    | `state.gameplay.hits.field_50`                           |
| Misses                     | `state.gameplay.hits.field_0`                            |
| Grade                      | `state.gameplay.hits.grade.current`                      |
| Unstable rate              | `state.gameplay.hits.unstableRate`                       |
| Logged-in profile name     | `state.userProfile.name`                                 |
| Global rank                | `state.userProfile.rank`                                 |
| Profile performance points | `state.userProfile.performancePoints`                    |

## Top-Level Model

`Model` contains these sections:

- `client`: Tosu client version or channel.
- `settings`: Tosu interface and osu! folder settings.
- `menu`: selected beatmap, mods, menu state, and PP estimates.
- `gameplay`: live score, combo, accuracy, hits, health, keys, and leaderboard.
- `resultsScreen`: the most recent results-screen values.
- `userProfile`: the current osu! profile information.
- `tourney`: tournament manager state and clients.

## Model Reference

### Settings and Selected Beatmap

- `Settings`: `showInterface`, `folders`.
- `Folders`: `game`, `skin`, `songs` paths.
- `MainMenu`: `bassDensity`.
- `Menu`: `mainMenu`, `state`, `gameMode`, `isChatEnabled`, `bm`, `mods`, `pp`.
- `Bm`: `time`, `id`, `set`, `md5`, `rankedStatus`, `metadata`, `stats`, `path`.
- `Time`: `firstObj`, `current`, `full`, `mp3` timestamps in milliseconds.
- `Metadata`: `artist`, `artistOriginal`, `title`, `titleOriginal`, `mapper`, `difficulty`.
- `Stats`: `AR`, `CS`, `OD`, `HP`, `SR`, `BPM`, `circles`, `sliders`, `spinners`, `holds`, `maxCombo`, `fullSR`, `memoryAR`, `memoryCS`, `memoryOD`, `memoryHP`.
- `BPM`: `realtime`, `common`, `min`, `max`; values are floats because Tosu can return fractional BPM.
- `Path`: `full`, `folder`, `file`, `bg`, `audio` paths or filenames.
- `Mods`: `num` numeric bitmask and `str` display string, such as `RX`.
- `Pp`: percentage projections `field_90` through `field_100`, `strains`, and `strainsAll`.
- `Series`: a strain series `name` and numeric `data` points.
- `StrainsAll`: `series` and `xaxis` values.

### Live Gameplay

- `Gameplay`: `gameMode`, `name`, `score`, `accuracy`, `combo`, `hp`, `hits`, `pp`, `keyOverlay`, `leaderboard`, `isReplayUiHidden`.
- `Combo`: `current`, `max`.
- `Hp`: `normal`, `smooth`.
- `Hits`: hit counts, `grade`, `unstableRate`, and `hitErrorArray`.
- `Grade`: `current`, `maxThisPlay`.
- `GameplayPp`: `current`, `fc`, `maxThisPlay`.
- `KeyOverlay`: `k1`, `k2`, `m1`, `m2` key states.
- `KeyState`: `isPressed`, `count`.
- `Leaderboard`: `hasLeaderboard`, `isVisible`, `ourplayer`, `slots`.
- `PlayerScore`: player name, score, combo, mods, hit counts, team, position, and passing state.

### Results, Profile, and Tournament

- `ResultsScreen`: hit counts, `mode`, `name`, `score`, `accuracy`, `maxCombo`, `mods`, `grade`, `createdAt`.
- `UserProfile`: login/status fields, `name`, `id`, `level`, `playCount`, `rank`, `countryCode`, and performance points.
- `Tourney`: `manager`, `ipcClients`.
- `Manager`: tournament IPC state, best-of value, team names, stars, visibility flags, chat, and gameplay scores.
- `TeamName`: `left`, `right` team names.
- `Stars`: `left`, `right` star values.
- `Bools`: `scoreVisible`, `starsVisible`.
- `Score`: `left`, `right` scores.
- `TournamentGameplay`: `score`.

## JSON Aliases

Some Tosu keys are not valid or convenient Python attribute names. The model
uses these aliases:

| Tosu JSON key            | Python field                                                   |
| ------------------------ | -------------------------------------------------------------- |
| `"90"` through `"100"`   | `state.menu.pp.field_90` through `field_100`                   |
| `"0"`                    | `state.gameplay.hits.field_0` or `state.resultsScreen.field_0` |
| `"50"`, `"100"`, `"300"` | corresponding `field_50`, `field_100`, `field_300`             |
| `"_isReplayUiHidden"`    | `state.gameplay.isReplayUiHidden`                              |

To serialize a model back using Tosu's original key names:

```python
json_data = state.model_dump(by_alias=True)
```

## Raw Data Versus Model Data

Use the raw dictionary when you need an unknown or newly added Tosu field:

```python
raw_value = raw_data["gameplay"]["score"]
model_value = state.gameplay.score
```

The Pydantic model is intentionally strict for known fields. If Tosu changes
its response shape, validation reports the exact path that needs updating in
`OsuTracker/models/tosu.py`.
