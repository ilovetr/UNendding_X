"""HTTP client wrapper for 川流/UnendingX API."""

import requests
from click import ClickException
from .config import load_config, is_token_expired, update_access_token


class APIClient:
    """Thin wrapper around requests for 川流/UnendingX API calls.
    
    Automatically refreshes tokens when expired.
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")

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
                # Try to refresh
                response = requests.post(
                    f"{self.base_url}/api/auth/refresh",
                    json={"refresh_token": refresh},
                    timeout=30,
                )
                if response.status_code == 200:
                    data = response.json()
                    update_access_token(
                        access_token=data["access_token"],
                        refresh_token=refresh,  # Keep same refresh (or use new if returned)
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
        r = requests.get(url, headers=self._headers(token), timeout=30)
        self._handle_error(r)
        return r

    def post(self, path: str, data: dict | None = None, token: str | None = None) -> requests.Response:
        """Send POST request. Auto-refreshes token if expired."""
        if token is None:
            token = self._get_valid_token()
        url = f"{self.base_url}{path}"
        r = requests.post(url, json=data, headers=self._headers(token), timeout=30)
        self._handle_error(r)
        return r

    def put(self, path: str, data: dict | None = None, token: str | None = None) -> requests.Response:
        """Send PUT request. Auto-refreshes token if expired."""
        if token is None:
            token = self._get_valid_token()
        url = f"{self.base_url}{path}"
        r = requests.put(url, json=data, headers=self._headers(token), timeout=30)
        self._handle_error(r)
        return r

    def delete(self, path: str, token: str | None = None) -> requests.Response:
        """Send DELETE request. Auto-refreshes token if expired."""
        if token is None:
            token = self._get_valid_token()
        url = f"{self.base_url}{path}"
        r = requests.delete(url, headers=self._headers(token), timeout=30)
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
