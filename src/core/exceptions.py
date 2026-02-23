"""Custom exception classes for the A2A Marketplace."""


class MarketplaceError(Exception):
    """Base exception for all marketplace errors."""

    def __init__(self, status_code: int = 500, detail: str = "Internal server error"):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class NotFoundError(MarketplaceError):
    """Resource not found."""

    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=404, detail=detail)


class UnauthorizedError(MarketplaceError):
    """Authentication required or invalid credentials."""

    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(status_code=401, detail=detail)


class ForbiddenError(MarketplaceError):
    """Insufficient permissions."""

    def __init__(self, detail: str = "Forbidden"):
        super().__init__(status_code=403, detail=detail)


class InsufficientCreditsError(MarketplaceError):
    """User does not have enough credits."""

    def __init__(self, detail: str = "Insufficient credits"):
        super().__init__(status_code=402, detail=detail)


class ConflictError(MarketplaceError):
    """Resource conflict (e.g., duplicate entry)."""

    def __init__(self, detail: str = "Conflict"):
        super().__init__(status_code=409, detail=detail)


class RateLimitError(MarketplaceError):
    """Rate limit exceeded."""

    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(status_code=429, detail=detail)


class AgentUnavailableError(MarketplaceError):
    """Agent is currently unavailable."""

    def __init__(self, detail: str = "Agent unavailable"):
        super().__init__(status_code=503, detail=detail)
