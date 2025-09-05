import json
import requests
import logging
import urllib3
import time
from typing import Dict, Optional, Any
from exceptions import JiraAuthError, JiraConnectionError, JiraAPIError
from utils import validate_url, validate_token

# Disable SSL warnings if requested
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def make_api_request(jira_url: str, jira_token: str, endpoint: str, method: str = 'GET',
                    payload: Optional[Dict] = None, verify_ssl: bool = True,
                    max_retries: int = 3, retry_delay: float = 1.0) -> Optional[Dict]:
    """A centralized function to handle all API requests with enhanced error handling and retry logic."""

    # Validate inputs
    try:
        jira_url = validate_url(jira_url)
        jira_token = validate_token(jira_token)
    except Exception as e:
        logging.error(f"Input validation failed: {e}")
        raise

    headers = {
        "Authorization": f"Bearer {jira_token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    url = f"{jira_url}/rest/api/2/{endpoint}"

    last_exception = None

    for attempt in range(max_retries):
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, verify=verify_ssl, timeout=30)
            elif method == 'POST':
                response = requests.post(url, headers=headers, data=json.dumps(payload),
                                       verify=verify_ssl, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # Handle different response codes
            if response.status_code == 401:
                raise JiraAuthError("Invalid credentials. Please check your Jira token.")
            elif response.status_code == 403:
                raise JiraAuthError("Access forbidden. Please check your permissions.")
            elif response.status_code == 404:
                raise JiraAPIError(response.status_code, response.text,
                                 f"Resource not found: {endpoint}")
            elif response.status_code >= 400:
                raise JiraAPIError(response.status_code, response.text)

            response.raise_for_status()

            if response.status_code == 204:
                return None
            return response.json()

        except requests.exceptions.Timeout:
            last_exception = JiraConnectionError("Request timed out. Please check your connection.")
        except requests.exceptions.ConnectionError:
            last_exception = JiraConnectionError("Failed to connect to Jira. Please check the URL and your network connection.")
        except requests.exceptions.SSLError as e:
            if verify_ssl:
                last_exception = JiraConnectionError("SSL certificate verification failed. Use --no-verify-ssl to bypass.")
            else:
                last_exception = JiraConnectionError(f"SSL error: {str(e)}")
        except requests.exceptions.HTTPError as e:
            # This should be caught by the status code checks above, but just in case
            last_exception = JiraAPIError(e.response.status_code, e.response.text)
        except requests.exceptions.RequestException as e:
            last_exception = JiraConnectionError(f"Network error: {str(e)}")
        except Exception as e:
            last_exception = JiraAPIError(500, str(e), f"Unexpected error: {str(e)}")

        # Retry logic for transient failures
        if attempt < max_retries - 1:
            logging.warning(f"Attempt {attempt + 1} failed: {last_exception}. Retrying in {retry_delay}s...")
            time.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff

    # All retries exhausted
    logging.error(f"All {max_retries} attempts failed. Last error: {last_exception}")
    raise last_exception


def search_issues(jira_url: str, jira_token: str, jql_query: str, verify_ssl: bool = True,
                 max_retries: int = 3) -> Optional[Dict]:
    """A centralized function to handle the search API request with enhanced error handling."""

    # Validate inputs
    try:
        jira_url = validate_url(jira_url)
        jira_token = validate_token(jira_token)
    except Exception as e:
        logging.error(f"Input validation failed: {e}")
        raise

    headers = {
        "Authorization": f"Bearer {jira_token}",
        "Accept": "application/json",
    }
    endpoint = "search"
    url = f"{jira_url}/rest/api/2/{endpoint}"
    params = {
        'jql': jql_query,
        'fields': 'summary,status,assignee,reporter,priority,created,updated'
    }

    last_exception = None

    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, params=params,
                                  verify=verify_ssl, timeout=30)

            # Handle different response codes
            if response.status_code == 401:
                raise JiraAuthError("Invalid credentials. Please check your Jira token.")
            elif response.status_code == 403:
                raise JiraAuthError("Access forbidden. Please check your permissions.")
            elif response.status_code == 404:
                raise JiraAPIError(response.status_code, response.text,
                                 "Search endpoint not found")
            elif response.status_code >= 400:
                raise JiraAPIError(response.status_code, response.text)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            last_exception = JiraConnectionError("Search request timed out. Please try again.")
        except requests.exceptions.ConnectionError:
            last_exception = JiraConnectionError("Failed to connect to Jira. Please check the URL and your network connection.")
        except requests.exceptions.SSLError as e:
            if verify_ssl:
                last_exception = JiraConnectionError("SSL certificate verification failed. Use --no-verify-ssl to bypass.")
            else:
                last_exception = JiraConnectionError(f"SSL error: {str(e)}")
        except requests.exceptions.HTTPError as e:
            last_exception = JiraAPIError(e.response.status_code, e.response.text)
        except requests.exceptions.RequestException as e:
            last_exception = JiraConnectionError(f"Network error: {str(e)}")
        except Exception as e:
            last_exception = JiraAPIError(500, str(e), f"Unexpected error: {str(e)}")

        # Retry logic for transient failures
        if attempt < max_retries - 1:
            logging.warning(f"Search attempt {attempt + 1} failed: {last_exception}. Retrying in 1s...")
            time.sleep(1)

    # All retries exhausted
    logging.error(f"All {max_retries} search attempts failed. Last error: {last_exception}")
    raise last_exception
