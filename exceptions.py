"""Custom exceptions for Jira CLI tool."""

class JiraError(Exception):
    """Base exception for Jira-related errors."""
    pass


class JiraAuthError(JiraError):
    """Raised when authentication fails."""
    def __init__(self, message: str = "Authentication failed"):
        self.message = message
        super().__init__(self.message)


class JiraConnectionError(JiraError):
    """Raised when connection to Jira fails."""
    def __init__(self, message: str = "Failed to connect to Jira"):
        self.message = message
        super().__init__(self.message)


class JiraAPIError(JiraError):
    """Raised when Jira API returns an error."""
    def __init__(self, status_code: int, response_text: str, message: str = None):
        self.status_code = status_code
        self.response_text = response_text
        if message is None:
            message = f"Jira API error: {status_code} - {response_text}"
        self.message = message
        super().__init__(self.message)


class JiraValidationError(JiraError):
    """Raised when input validation fails."""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = f"Validation error for {field}: {message}"
        super().__init__(self.message)


class JiraConfigError(JiraError):
    """Raised when configuration is invalid."""
    def __init__(self, message: str = "Configuration error"):
        self.message = message
        super().__init__(self.message)
