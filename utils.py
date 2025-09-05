"""Shared utilities for Jira CLI tool."""

import os
import sys
import subprocess
import tempfile
import time
import logging
from typing import Any, Dict, List, Optional
from exceptions import JiraValidationError


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


def select_from_list(options: List[Dict], name_key: str = 'name', allow_quit: bool = True) -> Optional[Dict]:
    """Presents a numbered list and returns the selected item with better UX."""
    if not options:
        print_error("No options available")
        return None

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
            quit_text = " or 'q' to quit" if allow_quit else ""
            choice = input(f"\n{Colors.BOLD}Select option (1-{len(options)}){quit_text}: {Colors.END}").strip()
            if allow_quit and choice.lower() == 'q':
                print_info("Selection cancelled")
                return None
            choice_num = int(choice)
            if 1 <= choice_num <= len(options):
                selected = options[choice_num - 1]
                print_success(f"Selected: {selected.get(name_key, 'Unknown')}")
                return selected
            else:
                print_warning(f"Please enter a number between 1 and {len(options)}")
        except ValueError:
            print_error("Please enter a valid number or 'q' to quit")


def select_from_string_list(options: List[str], prompt: str, allow_quit: bool = True) -> Optional[str]:
    """Enhanced selection from a string list with better formatting and quit option."""
    print(f"\n{Colors.BOLD}{prompt}{Colors.END}")
    for i, option in enumerate(options, 1):
        print(f"  {i}. {option}")
    if allow_quit:
        print("  0. Quit")
    while True:
        try:
            choice = input(f"\n{Colors.BLUE}Select an option (1-{len(options)}): {Colors.END}").strip()
            if allow_quit and choice == '0':
                print_info("Operation cancelled by user.")
                return None
            choice_num = int(choice)
            if 1 <= choice_num <= len(options):
                return options[choice_num - 1]
            else:
                print_error("Invalid selection. Please try again.")
        except ValueError:
            print_error("Please enter a valid number.")


def get_field_input(prompt: str, required: bool = False, example: str = "") -> str:
    """Get user input with validation and retry logic."""
    while True:
        if example:
            full_prompt = f"{Colors.BLUE}{prompt} (e.g., {example}): {Colors.END}"
        else:
            full_prompt = f"{Colors.BLUE}{prompt}: {Colors.END}"

        value = input(full_prompt).strip()

        if required and not value:
            print_error("This field is required. Please try again.")
            continue

        return value


def get_field_input_complex(field_meta: Dict) -> Any:
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
                return get_field_input_complex(field_meta)  # Retry
            return None
        values = [s.strip() for s in user_input.split(',') if s.strip()]
        if items_type in ['component', 'version']:
            return [{"name": v} for v in values]
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
                        return get_field_input_complex(field_meta)
                    return None
        except subprocess.CalledProcessError:
            print_error("Failed to open editor. Please set EDITOR environment variable.")
            # Fallback to simple input
            return input(f"{Colors.BOLD}Enter {field_name}: {Colors.END}").strip()
        finally:
            try:
                os.unlink(temp_filename)
            except:
                pass

    else:
        # Default input handling
        user_input = input(f"{Colors.BOLD}Enter {field_name}: {Colors.END}").strip()
        if not user_input and required:
            print_warning("This field is required. Please provide a value.")
            return get_field_input_complex(field_meta)
        return user_input if user_input else None


def validate_url(url: str) -> str:
    """Validate and normalize Jira URL."""
    if not url:
        raise JiraValidationError("url", "URL cannot be empty")

    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = f'https://{url}'

    # Remove trailing slash
    url = url.rstrip('/')

    return url


def validate_token(token: str) -> str:
    """Validate Jira API token."""
    token = token.strip()
    if not token:
        raise JiraValidationError("token", "Token cannot be empty")

    if len(token) < 10:
        raise JiraValidationError("token", "Token appears to be too short")

    return token


def setup_logging(debug: bool = False):
    """Configure logging based on debug flag."""
    if debug:
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
