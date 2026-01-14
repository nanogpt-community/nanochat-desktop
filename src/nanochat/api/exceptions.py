"""API exceptions."""


class NanoChatAPIError(Exception):
    """Base exception for API errors."""
    pass


class AuthenticationError(NanoChatAPIError):
    """Authentication failed."""
    pass


class ConnectionError(NanoChatAPIError):
    """Network connection error."""
    pass


class RateLimitError(NanoChatAPIError):
    """Rate limit exceeded."""
    pass
