"""Test fixture: clean production file with no placeholder patterns.

This file simulates production code with complete, real implementations.
The PlaceholderScanner should find zero violations here.
"""

import hashlib
import hmac
from typing import Optional


def authenticate(username: str, password: str) -> bool:
    """Verify user credentials against stored hash.

    Args:
        username: The user's login name.
        password: The plaintext password to verify.

    Returns:
        True if credentials are valid, False otherwise.
    """
    stored_hash = _get_stored_hash(username)
    if stored_hash is None:
        return False
    return hmac.compare_digest(
        hashlib.sha256(password.encode()).hexdigest(),
        stored_hash
    )


def get_user_profile(user_id: int) -> dict:
    """Retrieve user profile from the data store.

    Args:
        user_id: Unique identifier for the user.

    Returns:
        Dictionary with user profile fields.

    Raises:
        ValueError: If user_id is not found.
    """
    profile = _load_from_store(user_id)
    if profile is None:
        raise ValueError(f"User {user_id} not found")
    return profile


def send_notification(user_id: int, message: str) -> None:
    """Send a notification to the specified user.

    Args:
        user_id: Target user's identifier.
        message: Notification content.
    """
    endpoint = _get_notification_endpoint(user_id)
    _dispatch(endpoint, message)


def calculate_total(items: list) -> float:
    """Calculate the total price for a list of items.

    Args:
        items: List of dicts with 'price' and 'quantity' keys.

    Returns:
        Sum of price * quantity for all items.
    """
    return sum(item["price"] * item.get("quantity", 1) for item in items)


def _get_stored_hash(username: str) -> Optional[str]:
    """Internal: retrieve stored password hash for username."""
    store = {"admin": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}
    return store.get(username)


def _load_from_store(user_id: int) -> Optional[dict]:
    """Internal: load user profile from storage."""
    store = {1: {"id": 1, "name": "Alice", "email": "alice@example.com"}}
    return store.get(user_id)


def _get_notification_endpoint(user_id: int) -> str:
    """Internal: resolve notification endpoint for user."""
    return f"https://notify.example.com/users/{user_id}"


def _dispatch(endpoint: str, message: str) -> None:
    """Internal: send HTTP POST to notification endpoint."""
    import urllib.request
    import json
    data = json.dumps({"message": message}).encode()
    req = urllib.request.Request(endpoint, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=5) as _:
        pass
