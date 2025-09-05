import json
import requests
import logging
import urllib3

def make_api_request(jira_url: str, jira_token: str, endpoint: str, method: str = 'GET', payload: dict | None = None, verify_ssl: bool = True) -> dict | None:
    """A centralized function to handle all API requests."""
    headers = {
        "Authorization": f"Bearer {jira_token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    url = f"{jira_url}/rest/api/2/{endpoint}"

    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, verify=verify_ssl)
        elif method == 'POST':
            response = requests.post(url, headers=headers, data=json.dumps(payload), verify=verify_ssl)

        response.raise_for_status()
        if response.status_code == 204:
            return None
        return response.json()

    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error for API endpoint {url}: {e.response.status_code} - {e.response.text}")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error occurred: {e}")
        return None


def search_issues(jira_url: str, jira_token: str, jql_query: str, verify_ssl: bool = True) -> dict | None:
    """A centralized function to handle the search API request."""
    headers = {
        "Authorization": f"Bearer {jira_token}",
        "Accept": "application/json",
    }
    endpoint = "search"
    url = f"{jira_url}/rest/api/2/{endpoint}"
    params = {
        'jql': jql_query,
        'fields': 'summary,status,assignee,reporter,priority' # Define which fields to retrieve
    }

    try:
        response = requests.get(url, headers=headers, params=params, verify=verify_ssl)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error for API endpoint {url}: {e.response.status_code} - {e.response.text}")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error occurred: {e}")
        return None
