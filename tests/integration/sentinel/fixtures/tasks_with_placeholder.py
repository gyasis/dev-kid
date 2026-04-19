"""Test fixture: production file containing placeholder patterns.

This file simulates production code that a developer submitted with TODOs and
stub implementations. The PlaceholderScanner should detect all violations here.
"""


def authenticate(username: str, password: str) -> bool:
    # TODO: implement real authentication
    return False


def get_user_profile(user_id: int) -> dict:
    # FIXME: this is not implemented yet
    raise NotImplementedError("get_user_profile not implemented")


def send_notification(user_id: int, message: str) -> None:
    pass  # TODO: implement notification sending


def calculate_total(items: list) -> float:
    # HACK: placeholder until pricing logic is finalized
    return 0.0


def mock_payment(amount: float) -> bool:
    """Stub payment function for testing."""
    return True
