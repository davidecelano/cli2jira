import os
import sys
import json
import requests
import logging
import argparse
from typing import Any
from auth import setup_environment
from jira_api import make_api_request
from utils import (
    Colors, print_success, print_info, print_warning, print_error,
    show_progress, select_from_list, get_field_input_complex, setup_logging
)
from exceptions import JiraError, JiraAuthError, JiraConnectionError, JiraAPIError

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Create Jira issues interactively')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--no-verify-ssl', action='store_true', help='Disable SSL certificate verification')
    parser.add_argument('--jira-url', help='Jira instance URL (overrides JIRA_URL environment variable)')
    return parser.parse_args()

# Parse command line arguments
args = parse_arguments()

# Configure logging based on debug flag
setup_logging(args.debug)

def main():
    """Main function to run the interactive CLI with improved UX."""
    print(f"{Colors.BOLD}{Colors.BLUE}🚀 Jira Issue Creator{Colors.END}")
    print(f"{Colors.BLUE}Create Jira issues interactively with guided prompts{Colors.END}\n")

    try:
        print_info("Setting up authentication...")
        jira_url, jira_token = setup_environment(args.jira_url)
        print_success("Authentication configured")

        # 1. Get Project
        print(f"\n{Colors.BOLD}Step 1: Project Selection{Colors.END}")
        project_key = input(f"{Colors.BOLD}Enter Project Key: {Colors.END}").strip().upper()
        if not project_key:
            print_error("Project Key cannot be empty")
            return

        # 2. Get Issue Type for Project
        print(f"\n{Colors.BOLD}Step 2: Issue Type Selection{Colors.END}")
        show_progress("Fetching available issue types")
        meta_issue_types = make_api_request(jira_url, jira_token, f"issue/createmeta/{project_key}/issuetypes", verify_ssl=not args.no_verify_ssl)
        if not meta_issue_types or not meta_issue_types.get('values'):
            print_error("Could not fetch issue types. Please check:")
            print("  • Project key '{project_key}' exists")
            print("  • You have permission to create issues in this project")
            print("  • Jira URL and credentials are correct")
            return

        issue_types = [it for it in meta_issue_types['values'] if not it.get('subtask', False)]
        if not issue_types:
            print_error("No issue types available for this project")
            return

        print_info("Please select an Issue Type:")
        selected_issue_type = select_from_list(issue_types)
        if not selected_issue_type:
            print_info("Issue creation cancelled")
            return

        # 3. Get Fields for selected Issue Type
        print(f"\n{Colors.BOLD}Step 3: Field Configuration{Colors.END}")
        show_progress("Fetching field configuration")
        meta_fields = make_api_request(jira_url, jira_token, f"issue/createmeta/{project_key}/issuetypes/{selected_issue_type['id']}", verify_ssl=not args.no_verify_ssl)
        if not meta_fields or not meta_fields.get('values'):
            print_error("Could not fetch field configuration for this issue type")
            return

        # 4. Separate and prompt for required fields
        issue_payload = {}
        required_fields = []
        optional_fields = []
        system_fields_to_ignore = ['project', 'issuetype', 'reporter', 'creator', 'status', 'resolution', 'watches', 'worklog', 'votes', 'attachment', 'subtasks', 'timetracking', 'progress', 'aggregateprogress']

        for field in meta_fields['values']:
            if field['fieldId'] in system_fields_to_ignore:
                continue
            if field.get('required', False):
                required_fields.append(field)
            else:
                optional_fields.append(field)

        print(f"\n{Colors.BOLD}Step 4: Required Fields{Colors.END}")
        print_info(f"Please fill in {len(required_fields)} required fields:")
        for i, field in enumerate(required_fields, 1):
            print(f"{Colors.BLUE}  [{i}/{len(required_fields)}]{Colors.END}")
            while True:
                value = get_field_input_complex(field)
                if value is not None:
                    issue_payload[field['fieldId']] = value
                    break

        # 5. Prompt for optional fields
        if optional_fields:
            print(f"\n{Colors.BOLD}Step 5: Optional Fields{Colors.END}")
            print_info(f"There are {len(optional_fields)} optional fields available")
            for field in optional_fields:
                try:
                    user_wants_to_set = input(f"{Colors.BOLD}Set '{field['name']}'? (y/n/skip all): {Colors.END}").lower().strip()
                    if user_wants_to_set == 'skip all':
                        print_info("Skipping remaining optional fields")
                        break
                    elif user_wants_to_set == 'y':
                        value = get_field_input_complex(field)
                        if value:
                            issue_payload[field['fieldId']] = value
                except (KeyboardInterrupt, EOFError):
                    print_info("Skipping remaining optional fields")
                    break

        # 6. Create the final payload
        final_payload = {"fields": {
            "project": {"key": project_key},
            "issuetype": {"id": selected_issue_type['id']},
            **issue_payload
        }}

        # 7. Confirmation
        print(f"\n{Colors.BOLD}{Colors.YELLOW}Step 6: Confirmation{Colors.END}")
        print(f"{Colors.BOLD}About to create this issue:{Colors.END}")
        print("-" * 60)

        # Format the payload nicely
        for key, value in final_payload['fields'].items():
            if key == 'description' and isinstance(value, str) and len(value) > 100:
                display_value = value[:100] + "..."
            else:
                display_value = json.dumps(value)
            print(f"  {Colors.BLUE}{key:<18}{Colors.END}: {display_value}")
        print("-" * 60)

        while True:
            confirm = input(f"{Colors.BOLD}Proceed with issue creation? (y/n): {Colors.END}").lower().strip()
            if confirm == 'y':
                break
            elif confirm == 'n':
                print_info("Issue creation cancelled")
                return
            else:
                print_warning("Please enter 'y' or 'n'")

        # 8. Create the issue
        print(f"\n{Colors.BOLD}Step 7: Creating Issue{Colors.END}")
        show_progress("Creating issue in Jira")
        created_issue = make_api_request(jira_url, jira_token, "issue", method='POST', payload=final_payload, verify_ssl=not args.no_verify_ssl)
        if created_issue:
            issue_key = created_issue['key']
            print_success(f"Issue created successfully!")
            print(f"{Colors.BOLD}Issue Key:{Colors.END} {Colors.GREEN}{issue_key}{Colors.END}")
            print(f"{Colors.BOLD}URL:{Colors.END} {Colors.BLUE}{jira_url}/browse/{issue_key}{Colors.END}")
            print(f"\n{Colors.GREEN}🎉 Issue '{issue_key}' is ready for your team!{Colors.END}")
        else:
            print_error("Failed to create issue. Please check your permissions and try again.")

    except JiraAuthError as e:
        print_error(f"Authentication failed: {e}")
        print_info("Please check your Jira token and try again.")
        if args.debug:
            logging.error(f"Auth error details: {e}", exc_info=True)
    except JiraConnectionError as e:
        print_error(f"Connection failed: {e}")
        print_info("Please check your internet connection and Jira URL.")
        if args.debug:
            logging.error(f"Connection error details: {e}", exc_info=True)
    except JiraAPIError as e:
        print_error(f"Jira API error: {e}")
        print_info("Please check your permissions and the data you're trying to submit.")
        if args.debug:
            logging.error(f"API error details: {e}", exc_info=True)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠ Operation cancelled by user{Colors.END}")
        sys.exit(0)
    except Exception as e:
        print_error(f"An unexpected error occurred: {e}")
        print_info("Please check your configuration and try again.")
        if args.debug:
            logging.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
