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


def setup_environment(jira_url_override: str | None = None) -> tuple[str, str]:
    """Load environment variables from .env file and check for credentials.

    This centralizes credential handling so other scripts can import it.
    
    Args:
        jira_url_override: Optional Jira URL to override environment variable
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

    if not jira_url:
        jira_url = input("Enter Jira URL: ").strip()
        if not jira_url:
            logging.error("Jira URL is required.")
            sys.exit(1)

    if not jira_token:
        jira_token = getpass.getpass("Enter Jira Token (input will be hidden): ").strip()
        if not jira_token:
            logging.error("Jira Token is required.")
            sys.exit(1)

        # Optionally save to Credential Manager
        if platform.system() == "Windows" and KEYRING_AVAILABLE:
            try:
                save = input("Save token to Windows Credential Manager for future use? (y/n): ").lower().strip()
                if save == 'y':
                    keyring.set_password("jira-cli", "token", jira_token)
                    logging.info("Token saved to Windows Credential Manager.")
            except Exception as e:
                logging.warning(f"Could not save token to Credential Manager: {e}")

    return cast(str, jira_url), cast(str, jira_token)
