import os
import sys
import requests
import logging
import argparse
from typing import cast
from auth import setup_environment
from jira_api import search_issues
from utils import (Colors, print_success, print_info, print_warning, print_error,
                   show_progress, select_from_string_list, get_field_input, setup_logging)
from exceptions import JiraError, JiraAuthError, JiraConnectionError, JiraAPIError

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Search and list Jira issues')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--no-verify-ssl', action='store_true', help='Disable SSL certificate verification')
    parser.add_argument('--jira-url', help='Jira instance URL (overrides JIRA_URL environment variable)')
    return parser.parse_args()

# Parse command line arguments
args = parse_arguments()

# Configure logging based on debug flag
setup_logging(args.debug)

def display_issue_results(issues: list):
    """Display search results in a formatted, colorful way."""
    if not issues:
        print_warning("No issues found matching your criteria.")
        return
    
    print_success(f"Found {len(issues)} issue(s):")
    print(f"\n{Colors.BOLD}{'='*80}{Colors.END}")
    
    for i, issue in enumerate(issues, 1):
        fields = issue['fields']
        key = issue['key']
        summary = fields['summary']
        status = fields['status']['name']
        assignee = fields.get('assignee')
        assignee_name = assignee['displayName'] if assignee else 'Unassigned'
        priority = fields.get('priority')
        priority_name = priority['name'] if priority else 'None'
        
        # Color coding based on status
        if status.lower() in ['open', 'to do']:
            status_color = Colors.YELLOW
        elif status.lower() in ['in progress', 'in review']:
            status_color = Colors.BLUE
        elif status.lower() in ['done', 'closed', 'resolved']:
            status_color = Colors.GREEN
        else:
            status_color = Colors.END
        
        print(f"{Colors.BOLD}{i:2d}. [{key}]{Colors.END}")
        print(f"    {Colors.BOLD}Summary:{Colors.END} {summary}")
        print(f"    {Colors.BOLD}Status:{Colors.END} {status_color}{status}{Colors.END}")
        print(f"    {Colors.BOLD}Assignee:{Colors.END} {assignee_name}")
        print(f"    {Colors.BOLD}Priority:{Colors.END} {priority_name}")
        print()

def main():
    """Enhanced main function with improved UX."""
    try:
        print(f"\n{Colors.BOLD}{Colors.BLUE}🚀 Jira Issue Lister{Colors.END}")
        print(f"{Colors.BLUE}Search and display Jira issues with ease{Colors.END}\n")
        
        # Setup authentication
        show_progress("Setting up authentication")
        jira_url, jira_token = setup_environment(args.jira_url)
        
        # Step 1: Get Project Key
        print(f"\n{Colors.BOLD}Step 1: Project Selection{Colors.END}")
        project_key = get_field_input(
            "Enter Project Key to search in",
            example="PROJ or leave blank for all projects"
        ).upper()
        
        # Step 2: Build JQL Query
        print(f"\n{Colors.BOLD}Step 2: Filter Selection{Colors.END}")
        jql_clauses = []
        if project_key:
            jql_clauses.append(f'project = "{project_key}"')
            print_success(f"Filtering by project: {project_key}")
        
        # User filter selection
        user_filters = [
            "Issues reported by me",
            "Issues assigned to me", 
            "All issues (no user filter)"
        ]
        
        selected_filter = select_from_string_list(user_filters, "Select a user filter:")
        
        if "reported by me" in selected_filter:
            jql_clauses.append("reporter = currentUser()")
            print_success("Filtering by issues reported by you")
        elif "assigned to me" in selected_filter:
            jql_clauses.append("assignee = currentUser()")
            print_success("Filtering by issues assigned to you")
        else:
            print_info("No user filter applied")
        
        # Step 3: Status filter
        print(f"\n{Colors.BOLD}Step 3: Status Filter{Colors.END}")
        status = get_field_input(
            "Enter Status to filter by",
            example="Open, In Progress, Done or leave blank for all"
        )
        if status:
            jql_clauses.append(f'status = "{status}"')
            print_success(f"Filtering by status: {status}")
        else:
            print_info("No status filter applied")
        
        # Step 4: Execute search
        print(f"\n{Colors.BOLD}Step 4: Executing Search{Colors.END}")
        final_jql = " AND ".join(jql_clauses)
        if not final_jql:
            print_error("At least one search criteria must be provided.")
            print_info("Please specify a project, user filter, or status.")
            return
        
        print_info(f"JQL Query: {final_jql}")
        show_progress("Searching Jira issues")
        
        results = search_issues(jira_url, jira_token, final_jql, verify_ssl=not args.no_verify_ssl)
        
        # Step 5: Display results
        print(f"\n{Colors.BOLD}Step 5: Results{Colors.END}")
        if results and 'issues' in results:
            display_issue_results(results['issues'])
        else:
            print_error("Could not retrieve issues. Please check your connection and credentials.")
            
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
        print_info("Please check your permissions and the search criteria.")
        if args.debug:
            logging.error(f"API error details: {e}", exc_info=True)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠ Operation cancelled by user.{Colors.END}")
        sys.exit(0)
    except Exception as e:
        print_error(f"An unexpected error occurred: {e}")
        print_info("Please check your configuration and try again.")
        if args.debug:
            logging.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
