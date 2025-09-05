import os
import sys
import json
import requests
import subprocess
import tempfile
import logging
import time
import argparse
from typing import Any
from auth import setup_environment
from jira_api import make_api_request

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
if args.debug:
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
else:
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# ANSI color codes for better UX
class Colors:
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_success(message: str):
    """Print success message in green."""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")

def print_info(message: str):
    """Print info message in blue."""
    print(f"{Colors.BLUE}ℹ {message}{Colors.END}")

def print_warning(message: str):
    """Print warning message in yellow."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")

def print_error(message: str):
    """Print error message in red."""
    print(f"{Colors.RED}✗ {message}{Colors.END}")

def show_progress(message: str, duration: float = 1.0):
    """Show a simple progress indicator."""
    print(f"{Colors.BLUE}{message}...{Colors.END}", end='', flush=True)
    time.sleep(duration)
    print(f"\r{Colors.GREEN}✓ {message} completed{Colors.END}")

# --- User Interaction Functions ---

def select_from_list(options: list[dict], name_key: str = 'name') -> dict:
    """Presents a numbered list and returns the selected item with better UX."""
    if not options:
        print_error("No options available")
        return {}
    
    print(f"\n{Colors.BOLD}Available options:{Colors.END}")
    print("-" * 50)
    
    for i, option in enumerate(options, 1):
        name = option.get(name_key, 'Unknown')
        if len(options) <= 10:
            print(f"  {Colors.BLUE}{i:2d}{Colors.END}. {name}")
        else:
            # For large lists, show in columns
            if i % 2 == 1:
                print(f"  {Colors.BLUE}{i:2d}{Colors.END}. {name:<30}", end='')
            else:
                print(f"  {Colors.BLUE}{i:2d}{Colors.END}. {name}")
    
    if len(options) > 10:
        print(f"\n{Colors.YELLOW}Showing {len(options)} options{Colors.END}")
    
    while True:
        try:
            choice = input(f"\n{Colors.BOLD}Select option (1-{len(options)}) or 'q' to quit: {Colors.END}").strip()
            if choice.lower() == 'q':
                print_info("Selection cancelled")
                return {}
            choice_num = int(choice)
            if 1 <= choice_num <= len(options):
                selected = options[choice_num - 1]
                print_success(f"Selected: {selected.get(name_key, 'Unknown')}")
                return selected
            else:
                print_warning(f"Please enter a number between 1 and {len(options)}")
        except ValueError:
            print_error("Please enter a valid number or 'q' to quit")

def get_field_input(field_meta: dict) -> Any:
    """Gets and formats user input based on field type with improved UX."""
    field_name = field_meta['name']
    field_schema = field_meta['schema']
    field_type = field_schema.get('type')
    field_id = field_meta['fieldId']
    required = field_meta.get('required', False)

    print(f"\n{Colors.BOLD}Field: {field_name}{Colors.END}")
    if required:
        print(f"{Colors.YELLOW}(Required){Colors.END}")
    else:
        print(f"{Colors.BLUE}(Optional - press Enter to skip){Colors.END}")

    if 'allowedValues' in field_meta and field_meta['allowedValues']:
        print_info(f"Select a value for '{field_name}':")
        selected_option = select_from_list(field_meta['allowedValues'])
        if not selected_option:
            return None
        if field_type in ['priority', 'user', 'component', 'version', 'option']:
             return {"id": selected_option['id']}
        return selected_option['value']
    
    elif field_type == 'array':
        items_type = field_schema.get('items')
        example = "user1,user2" if items_type == 'user' else "component1,component2"
        user_input = input(f"{Colors.BOLD}Enter {field_name} (comma-separated, e.g., {example}): {Colors.END}").strip()
        if not user_input:
            if required:
                print_warning("This field is required. Please provide a value.")
                return get_field_input(field_meta)  # Retry
            return None
        values = [s.strip() for s in user_input.split(',') if s.strip()]
        if items_type in ['component', 'version']:
            return [{ "name": v } for v in values]
        return values

    elif field_id == 'description':
        print_info("Opening editor for Description... (Save and close the file to continue)")
        editor = os.getenv('EDITOR', 'vim')
        with tempfile.NamedTemporaryFile(mode='w+', suffix=".tmp", delete=False) as tf:
            temp_filename = tf.name
        try:
            subprocess.run([editor, temp_filename], check=True)
            with open(temp_filename, 'r') as tf:
                content = tf.read().strip()
                if content:
                    print_success("Description saved")
                    return content
                else:
                    if required:
                        print_warning("Description cannot be empty. Please try again.")
                        return get_field_input(field_meta)  # Retry
                    return None
        except subprocess.CalledProcessError:
            print_error("Failed to open editor. Please set EDITOR environment variable.")
            # Fallback to simple input
            return input(f"{Colors.BOLD}Description: {Colors.END}").strip() or None
        finally:
            os.remove(temp_filename)

    else:
        while True:
            user_input = input(f"{Colors.BOLD}{field_name}: {Colors.END}").strip()
            if user_input or not required:
                return user_input or None
            print_warning("This field is required. Please provide a value.")

# --- Main Application Logic ---

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
            print(f"  • Project key '{project_key}' exists")
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
                value = get_field_input(field)
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
                        value = get_field_input(field)
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
            
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠ Operation cancelled by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print_error(f"An unexpected error occurred: {e}")
        print_info("Please check your configuration and try again")

if __name__ == "__main__":
    main()
