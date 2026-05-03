"""HTTP client wrapper for 川流/UnendingX API."""

import os
import requests
from click import ClickException
from .config import load_config, is_token_expired, update_access_token


class APIClient:
    """Thin wrapper around requests for 川流/UnendingX API calls.

    Automatically refreshes tokens when expired.
    Supports bypassing system proxy via NO_PROXY or trust_env=False.
    """

    def __init__(self, base_url: str = "http://localhost:8000", trust_env: bool = False):
        self.base_url = base_url.rstrip("/")
        self.trust_env = trust_env
        self._session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a requests session with proxy bypass."""
        session = requests.Session()
        if not self.trust_env:
            # Bypass system proxy settings for direct connection
            session.trust_env = False
            # Also clear any proxy env vars for this session
            session.proxies = {
                'http': None,
                'https': None,
            }
        return session

    def _headers(self, token: str | None = None) -> dict:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _handle_error(self, response: requests.Response) -> None:
        """Raise ClickException on HTTP errors."""
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            raise ClickException(f"HTTP {response.status_code}: {detail}")

    def _get_valid_token(self) -> str | None:
        """Get a valid access token, refreshing if necessary."""
        config = load_config()
        token = config.get("access_token")
        refresh = config.get("refresh_token")

        if not token or not refresh:
            return token

        # Check if token is expired or about to expire
        if is_token_expired():
            try:
                # Try to refresh (use session to bypass proxy)
                response = self._session.post(
                    f"{self.base_url}/api/auth/refresh",
                    json={"refresh_token": refresh},
                    timeout=30,
                    proxies={'http': None, 'https': None},
                )
                if response.status_code == 200:
                    data = response.json()
                    update_access_token(
                        access_token=data["access_token"],
                        refresh_token=refresh,
                        expires_in=data["expires_in"],
                    )
                    return data["access_token"]
            except Exception:
                pass
            return None

        return token

    def get(self, path: str, token: str | None = None) -> requests.Response:
        """Send GET request. Auto-refreshes token if expired."""
        if token is None:
            token = self._get_valid_token()
        url = f"{self.base_url}{path}"
        r = self._session.get(url, headers=self._headers(token), timeout=30,
                             proxies={'http': None, 'https': None})
        self._handle_error(r)
        return r

    def post(self, path: str, data: dict | None = None, token: str | None = None) -> requests.Response:
        """Send POST request. Auto-refreshes token if expired."""
        if token is None:
            token = self._get_valid_token()
        url = f"{self.base_url}{path}"
        r = self._session.post(url, json=data, headers=self._headers(token), timeout=30,
                              proxies={'http': None, 'https': None})
        self._handle_error(r)
        return r

    def put(self, path: str, data: dict | None = None, token: str | None = None) -> requests.Response:
        """Send PUT request. Auto-refreshes token if expired."""
        if token is None:
            token = self._get_valid_token()
        url = f"{self.base_url}{path}"
        r = self._session.put(url, json=data, headers=self._headers(token), timeout=30,
                              proxies={'http': None, 'https': None})
        self._handle_error(r)
        return r

    def delete(self, path: str, token: str | None = None) -> requests.Response:
        """Send DELETE request. Auto-refreshes token if expired."""
        if token is None:
            token = self._get_valid_token()
        url = f"{self.base_url}{path}"
        r = self._session.delete(url, headers=self._headers(token), timeout=30,
                                 proxies={'http': None, 'https': None})
        self._handle_error(r)
        return r


def api_request(method: str, path: str, base_url: str = "http://localhost:8000",
                data: dict | None = None, token: str | None = None) -> requests.Response:
    """Convenience function for one-off API requests."""
    client = APIClient(base_url)
    method_map = {
        "GET": client.get,
        "POST": client.post,
        "PUT": client.put,
        "DELETE": client.delete,
    }
    fn = method_map.get(method.upper())
    if fn is None:
        raise ClickException(f"Unsupported HTTP method: {method}")
    if method.upper() in ("POST", "PUT"):
        return fn(path, data=data, token=token)
    return fn(path, token=token)
