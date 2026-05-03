"""Configuration management for 川流/UnendingX CLI.

Stores config at ~/.config/unendingx/config.json
Secure storage for access_token and refresh_token with encryption.
"""

import json
import os
import uuid
import hashlib
import hmac
import base64
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "unendingx"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "base_url": "http://81.70.187.125:80",
    "default_server": None,  # Can be set to override base_url
    "agent_id": None,
    "name": None,
    "access_token": None,
    "refresh_token": None,
    "device_id": None,  # Client-generated device identifier
    "token_expires_at": None,  # Access token expiry timestamp
    "history_enabled": True,  # CLI command history
    "command_history": [],  # Last N commands
}

# Fields that need encryption
SECURE_FIELDS = ["access_token", "refresh_token"]


def _get_machine_key() -> bytes:
    """
    Derive a machine-specific encryption key.

    Uses a combination of:
    - User home directory path (salt)
    - Machine/hardware identifiers when available

    Note: This provides basic obfuscation for local file protection.
    For stronger security, consider OS keyring (keyring package) in production.
    """
    # Use config file path as part of the key derivation
    # This makes the key unique per user installation
    salt = str(CONFIG_FILE).encode("utf-8")

    # Add machine-specific identifiers if available
    try:
        import platform
        machine_id = f"{platform.node()}-{platform.machine()}-{platform.system()}".encode("utf-8")
    except Exception:
        machine_id = b"default-machine-id"

    # Derive a consistent key using PBKDF2
    key = hashlib.pbkdf2_hmac(
        "sha256",
        machine_id,
        salt,
        iterations=100000,
        dklen=32,
    )
    return key


def _encrypt(plaintext: str) -> str:
    """Encrypt a string using Fernet (AES-128-CBC with HMAC)."""
    from cryptography.fernet import Fernet
    key = _get_machine_key()
    f = Fernet(base64.urlsafe_b64encode(key))
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def _decrypt(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted string."""
    from cryptography.fernet import Fernet
    key = _get_machine_key()
    f = Fernet(base64.urlsafe_b64encode(key))
    return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")


def _encrypt_config(data: dict) -> dict:
    """Encrypt sensitive fields in config data."""
    result = dict(data)
    for field in SECURE_FIELDS:
        if result.get(field):
            # Mark encrypted fields with ENC: prefix
            result[field] = f"ENC:{_encrypt(result[field])}"
    return result


def _decrypt_config(data: dict) -> dict:
    """Decrypt sensitive fields in config data."""
    result = dict(data)
    for field in SECURE_FIELDS:
        value = result.get(field)
        if value and isinstance(value, str) and value.startswith("ENC:"):
            try:
                result[field] = _decrypt(value[4:])  # Remove ENC: prefix
            except Exception:
                # If decryption fails, leave as-is (might be legacy unencrypted)
                pass
    return result


def _get_device_id() -> str:
    """Get or create a unique device ID for this installation."""
    config = load()
    if config.get("device_id"):
        return config["device_id"]
    device_id = str(uuid.uuid4())
    config["device_id"] = device_id
    save(config)
    return device_id


def load() -> dict:
    """Load configuration from disk.

    Returns the config dict with decrypted sensitive fields,
    creating default if file doesn't exist.
    """
    if not CONFIG_FILE.exists():
        return dict(DEFAULT_CONFIG)

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Merge with defaults so new keys are always present
        merged = dict(DEFAULT_CONFIG)
        merged.update(data)
        # Decrypt sensitive fields
        return _decrypt_config(merged)
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_CONFIG)


def save(data: dict) -> None:
    """Save configuration to disk with encrypted sensitive fields.

    Creates the config directory if it doesn't exist.
    Sensitive fields (access_token, refresh_token) are encrypted.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    # Encrypt sensitive fields before saving
    encrypted_data = _encrypt_config(data)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(encrypted_data, f, indent=2, ensure_ascii=False)


def save_auth(agent_id: str, name: str, access_token: str, refresh_token: str,
              expires_in: int, base_url: str) -> None:
    """Save authentication data including refresh token."""
    import time
    config = load()
    config["agent_id"] = agent_id
    config["name"] = name
    config["access_token"] = access_token
    config["refresh_token"] = refresh_token
    config["base_url"] = base_url
    config["device_id"] = _get_device_id()
    config["token_expires_at"] = time.time() + expires_in
    save(config)


def update_access_token(access_token: str, refresh_token: str, expires_in: int) -> None:
    """Update access token after refresh."""
    import time
    config = load()
    config["access_token"] = access_token
    config["refresh_token"] = refresh_token
    config["token_expires_at"] = time.time() + expires_in
    save(config)


def is_token_expired() -> bool:
    """Check if the stored access token is expired or about to expire."""
    import time
    config = load()
    expires_at = config.get("token_expires_at")
    if not expires_at:
        return True
    # Consider expired if less than 1 minute remaining
    return time.time() >= (expires_at - 60)


def get_default_server() -> str | None:
    """Get the configured default server URL."""
    config = load()
    return config.get("default_server")


def set_default_server(url: str) -> None:
    """Set the default server URL."""
    config = load()
    config["default_server"] = url
    save(config)


def clear_default_server() -> None:
    """Clear the default server URL."""
    config = load()
    config.pop("default_server", None)
    save(config)


def add_to_history(command: str) -> None:
    """Add a command to history (max 100 entries)."""
    config = load()
    if not config.get("history_enabled", True):
        return
    history = config.get("command_history", [])
    # Remove duplicates
    if command in history:
        history.remove(command)
    # Add to end
    history.append(command)
    # Keep only last 100
    if len(history) > 100:
        history = history[-100:]
    config["command_history"] = history
    save(config)


def get_history() -> list[str]:
    """Get command history."""
    config = load()
    return config.get("command_history", [])


def clear_history() -> None:
    """Clear command history."""
    config = load()
    config["command_history"] = []
    save(config)


# Aliases used by cli.py
load_config = load
save_config = save
