from bisect import bisect_left, insort
import itertools
import os
import random
from typing import Any, Generator, Iterable, List, Optional

import requests


class DataException(ValueError):
    def __init__(self) -> None:
        super().__init__("No data.")


class DeezerClient:

    """Deezer API client.

    Parameters
    ----------
    token : str, optional
        API access token for authenticated requests.
    """

    def __init__(self, token: Optional[str] = None) -> None:
        self.token = token
        self.base = "https://api.deezer.com/"
        self.session = requests.Session()

    def add_to_playlist(
        self, playlist_id: int, track_ids: Iterable[int]
    ) -> None:
        """Add tracks to a playlist (requires authentication)."""
        endpoint = f"playlist/{playlist_id}/tracks"
        params = {
            "request_method": "POST",
            "songs": ",".join(map(str, track_ids)),
        }
        self.request(endpoint, params)

    def clear_playlist(self, playlist_id: int) -> None:
        """Remove all tracks in a playlist."""
        track_ids = self.get_track_ids_in_playlist(playlist_id)
        if track_ids:
            self.delete_from_playlist(playlist_id, track_ids)

    def delete_from_playlist(
        self, playlist_id: int, track_ids: List[int]
    ) -> None:
        """Remove tracks from a playlist (requires authentication)."""
        endpoint = f"playlist/{playlist_id}/tracks"
        params = {
            "request_method": "DELETE",
            "songs": ",".join(map(str, track_ids)),
        }
        self.request(endpoint, params)

    def get_track(self, id: int) -> dict:
        """Return track data."""
        return self.request(f"track/{id}")

    def get_track_ids_in_playlist(self, playlist_id: int) -> List[int]:
        """Return list of IDs of the tracks in a playlist."""
        tracks = self.request(f"playlist/{playlist_id}")["tracks"]["data"]
        return [int(track["id"]) for track in tracks]

    def request(self, endpoint: str, params: dict = {}) -> dict:
        """Send API request and return its response body."""
        url = f"{self.base}/{endpoint}"
        params["output"] = "json"
        if self.token is not None:
            params["access_token"] = self.token
        data = self.session.get(url, params=params).json()
        if isinstance(data, dict) and "error" in data:
            if data["error"]["type"] == "DataException":
                raise DataException
            else:
                raise ValueError(data["error"]["message"])
        return data


class Index:

    """Efficient index."""

    def __init__(self, input: List[int] = []) -> None:
        self._list = sorted(input)

    def __contains__(self, x: int) -> bool:
        index = bisect_left(self._list, x)
        return index != len(self._list) and self._list[index] == x

    def append(self, x: int) -> None:
        insort(self._list, x)


def get_random_track_ids(
    client: DeezerClient, country: Optional[str] = None
) -> Generator[int, None, None]:
    """Generate distinct random valid track IDs.

    Parameters
    ----------
    client : DeezerClient
        API client instance.
    country : str, optional
        2-letter country code. If specified, only tracks that are
        available in this market will be generated.
    """
    done = Index()
    while True:
        id = random.randint(0, 2 ** 31)
        if id not in done:
            try:
                done.append(id)
                track = client.get_track(id)
                if country or country in track["available_countries"]:
                    yield id
            except DataException:
                pass


def update_playlist(playlist_length: int = 100) -> None:
    playlist_id = int(os.environ["RANDOM_PLAYLIST_ID"])
    token = os.environ["DEEZER_ACCESS_TOKEN"]
    country = os.environ["RANDOM_PLAYLIST_COUNTRY"]
    client = DeezerClient(token)
    client.clear_playlist(playlist_id)
    track_ids = itertools.islice(
        get_random_track_ids(client, country), playlist_length
    )
    client.add_to_playlist(playlist_id, track_ids)


def lambda_handler(event: Any, lambda_context: Any) -> None:
    update_playlist()
