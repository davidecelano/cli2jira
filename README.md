# Jira CLI Tool

A powerful, user-friendly command-line interface for interacting with Atlassian Jira. Create issues, search and list existing issues with an enhanced terminal experience featuring colors, progress indicators, and intuitive prompts.

## 🚀 Features

- **Issue Creation**: Interactive CLI for creating Jira issues with guided prompts
- **Issue Search**: Advanced search and filtering capabilities with JQL support


## 📋 Prerequisites

- Python 3.8 or higher
- Access to a Jira instance (Cloud or Server)
- Jira Personal Access Token (PAT) or API token

## 🛠️ Installation

1. **Clone the repository:**
	```bash
	git clone https://github.com/davidecelano/cli2jira.git
	cd cli2jira
	```

2. **Install dependencies:**
	```bash
	pip install -r requirements.txt
	```

3. **Configure environment variables:**
	Create a `.env` file in the project root (copy from `.env.example`):
	```env
	JIRA_URL=https://your-instance.atlassian.net
	JIRA_TOKEN=your_personal_access_token_here
	```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `JIRA_URL` | Your Jira instance URL | Yes |
| `JIRA_TOKEN` | Personal Access Token | Yes |

### Secure Credential Storage

The tool supports secure credential storage using your system's credential manager:

- **Windows**: Windows Credential Manager
- **macOS**: Keychain
- **Linux**: Secret Service API (GNOME) or KWallet

Credentials are stored securely and can be retrieved automatically on subsequent runs.

## 📖 Usage

### Command Line Options

Both tools support the following command-line options:

```bash
# Enable debug logging
python jira_create.py --debug
python jira_list.py --debug

# Disable SSL certificate verification (useful for self-signed certificates)
python jira_create.py --no-verify-ssl
python jira_list.py --no-verify-ssl

# Override Jira URL from environment
python jira_create.py --jira-url https://your-custom-jira-instance.com
python jira_list.py --jira-url https://your-custom-jira-instance.com

```

### Creating Issues

Run the issue creation tool:

```bash
python jira_create.py
```

The interactive CLI will guide you through:
1. **Project Selection**: Choose the target project
2. **Issue Type**: Select issue type (Bug, Task, Story, etc.)
3. **Field Input**: Fill in required and optional fields
4. **Confirmation**: Review and confirm before creation

### Listing Issues

Search and list existing issues:

```bash
python jira_list.py
```

Filter options include:
- **Project**: Filter by specific project key
- **User Filter**: Issues reported by/assigned to you, or all issues
- **Status**: Filter by issue status (Open, In Progress, Done, etc.)

## 🔍 Search Examples

### Find all open issues in a project:
```
Project Key: PROJ
User Filter: All issues
Status: Open
```

### Find issues assigned to you:
```
Project Key: PROJ
User Filter: Issues assigned to me
Status: (leave blank)
```

### Find your reported bugs:
```
Project Key: PROJ
User Filter: Issues reported by me
Status: (leave blank)
```

## 🏗️ Architecture

```
cli2jira/
├── jira_create.py    # Issue creation CLI
├── jira_list.py      # Issue search/listing CLI
├── auth.py           # Authentication and credential management
├── jira_api.py       # Jira API wrapper functions
├── requirements.txt  # Python dependencies
└── README.md         # This file
```

### Module Overview

- **`auth.py`**: Handles authentication setup, credential storage, and environment configuration
- **`jira_api.py`**: Contains API wrapper functions for making requests to Jira REST API
- **`jira_create.py`**: Interactive CLI for creating new Jira issues
- **`jira_list.py`**: Interactive CLI for searching and listing existing issues

## 🐛 Troubleshooting

### Common Issues

**"SSL certificate verification failed"**
- For self-signed certificates: Use `--no-verify-ssl` flag
- For corporate environments: Ensure your system's certificate store includes the corporate CA
- Check if your Jira instance uses a valid SSL certificate

**"Connection timeout"**
- Verify your Jira URL is accessible
- Check network connectivity and firewall settings
- Try using `--debug` for detailed connection information

**"Module not found"**
- Install dependencies: `pip install -r requirements.txt`
- Ensure you're using Python 3.8+

**"Authentication failed"**
- Verify your Personal Access Token is valid
- Check token permissions in Jira
- Try clearing stored credentials and re-authenticating


### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest

# Check code quality
python -m flake8
python -m mypy
```

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with the [Jira REST API](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)
- Uses [requests](https://requests.readthedocs.io/) for HTTP client functionality
- Secure credential storage powered by [keyring](https://github.com/jaraco/keyring)
