"""Custom exception classes for CrewHub."""


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


class QuotaExceededError(MarketplaceError):
    """Usage quota exceeded for the pricing tier."""

    def __init__(self, detail: str = "Quota exceeded"):
        super().__init__(status_code=429, detail=detail)


class RateLimitError(MarketplaceError):
    """Rate limit exceeded."""

    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(status_code=429, detail=detail)


class PaymentVerificationError(MarketplaceError):
    """x402 payment verification failed."""

    def __init__(self, detail: str = "Payment verification failed"):
        super().__init__(status_code=402, detail=detail)


class AgentUnavailableError(MarketplaceError):
    """Agent is currently unavailable."""

    def __init__(self, detail: str = "Agent unavailable"):
        super().__init__(status_code=503, detail=detail)


class SpendingLimitError(MarketplaceError):
    """User has exceeded their daily spending limit."""

    def __init__(self, detail: str = "Daily spending limit exceeded"):
        super().__init__(status_code=429, detail=detail)


class ContentModerationError(MarketplaceError):
    """Content failed moderation checks."""

    def __init__(self, detail: str = "Content blocked by moderation policy"):
        super().__init__(status_code=422, detail=detail)


class AbuseDetectedError(MarketplaceError):
    """Abusive behavior detected."""

    def __init__(self, detail: str = "Suspicious activity detected"):
        super().__init__(status_code=429, detail=detail)


class DelegationDepthError(MarketplaceError):
    """Delegation chain too deep."""

    def __init__(self, detail: str = "Maximum delegation depth exceeded"):
        super().__init__(status_code=400, detail=detail)
