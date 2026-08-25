"""Helpers for classifying Tosu activity state across app surfaces."""

from OsuTracker.models.tosu import Model

STATE_MENU = "menu"
STATE_PLAYING = "playing"
STATE_SPECTATING = "spectating"
STATE_UNKNOWN = "unknown"


def _spectating_state(player_name: str) -> str:
    player = player_name.strip() or "Unknown"
    return f"{STATE_SPECTATING}:{player}"


def classify_activity_state(model: Model) -> str:
    """Classify the current Tosu state into menu, playing, or spectating."""
    if model.menu.state != 2:
        return STATE_MENU

    # Empirically from captured data:
    # - 2: active play
    # - 6: spectating/replay view
    status = model.userProfile.rawBanchoStatus
    if status == 6:
        return _spectating_state(model.gameplay.name)
    if status == 2:
        return STATE_PLAYING

    if model.gameplay.name.strip() and model.userProfile.name.strip():
        if model.gameplay.name != model.userProfile.name:
            return _spectating_state(model.gameplay.name)
        return STATE_PLAYING

    return STATE_UNKNOWN


def activity_label(state: str) -> str:
    """Return a user-friendly label for an activity state."""
    if state.startswith(f"{STATE_SPECTATING}:"):
        player = state.split(":", 1)[1].strip() or "Unknown"
        return f"Spectating: {player}"

    labels = {
        STATE_MENU: "Browsing songs",
        STATE_PLAYING: "Playing",
        STATE_SPECTATING: "Spectating: Unknown",
        STATE_UNKNOWN: "Unknown",
    }
    return labels.get(state, "Unknown")
