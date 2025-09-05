import os
import sys
import logging
import getpass
import platform
from typing import cast
try:
    import keyring
    KEYRING_AVAILABLE = True
except Exception:
    KEYRING_AVAILABLE = False
from dotenv import load_dotenv
from exceptions import JiraConfigError, JiraAuthError
from utils import validate_url, validate_token


def setup_environment(jira_url_override: str | None = None) -> tuple[str, str]:
    """Load environment variables from .env file and check for credentials.

    This centralizes credential handling so other scripts can import it.

    Args:
        jira_url_override: Optional Jira URL to override environment variable

    Returns:
        Tuple of (jira_url, jira_token)

    Raises:
        JiraConfigError: If configuration is invalid
        JiraAuthError: If authentication setup fails
    """
    load_dotenv()
    jira_url = jira_url_override or os.getenv("JIRA_URL")
    jira_token = os.getenv("JIRA_TOKEN")

    # Try to load from Windows Credential Manager if on Windows and keyring available
    if platform.system() == "Windows" and KEYRING_AVAILABLE and not jira_token:
        try:
            stored_token = keyring.get_password("jira-cli", "token")
            if stored_token:
                jira_token = stored_token
                logging.info("Token loaded from Windows Credential Manager.")
        except Exception as e:
            logging.warning(f"Could not retrieve token from Credential Manager: {e}")

    # Get Jira URL if not provided
    if not jira_url:
        try:
            jira_url = input("Enter Jira URL: ").strip()
            jira_url = validate_url(jira_url)
        except Exception as e:
            raise JiraConfigError(f"Invalid Jira URL: {e}")

    # Get Jira token if not provided
    if not jira_token:
        try:
            jira_token = getpass.getpass("Enter Jira Token (input will be hidden): ").strip()
            jira_token = validate_token(jira_token)
        except Exception as e:
            raise JiraAuthError(f"Invalid Jira token: {e}")

        # Optionally save to Credential Manager
        if platform.system() == "Windows" and KEYRING_AVAILABLE:
            try:
                save = input("Save token to Windows Credential Manager for future use? (y/n): ").lower().strip()
                if save == 'y':
                    keyring.set_password("jira-cli", "token", jira_token)
                    logging.info("Token saved to Windows Credential Manager.")
            except Exception as e:
                logging.warning(f"Could not save token to Credential Manager: {e}")

    # Final validation
    try:
        jira_url = validate_url(jira_url)
        jira_token = validate_token(jira_token)
    except Exception as e:
        raise JiraConfigError(f"Configuration validation failed: {e}")

    return cast(str, jira_url), cast(str, jira_token)
