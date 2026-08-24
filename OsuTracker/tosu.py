"""Client helpers for Tosu's local JSON API."""

import requests

from OsuTracker.models.tosu import Model


def fetch_tosu_data(endpoint: str, timeout: float = 2.0) -> Model:
    """Fetch the current game state from Tosu.

    Raises:
        requests.RequestException: If Tosu cannot be reached.
        pydantic.ValidationError: If the response does not match Model.
    """
    response = requests.get(endpoint, timeout=timeout)
    response.raise_for_status()
    return Model.model_validate_json(response.content)
