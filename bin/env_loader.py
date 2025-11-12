#!/usr/bin/env python3
"""
Simple .env file loader
Loads environment variables from .env file without external dependencies
"""
import os
from pathlib import Path
from typing import Dict, Optional


def load_env_file(env_file: str = ".env") -> Dict[str, str]:
    """
    Load environment variables from .env file

    Args:
        env_file: Path to .env file (default: .env in current directory)

    Returns:
        Dictionary of environment variables loaded from file
    """
    env_vars = {}

    # Check if file exists
    if not os.path.exists(env_file):
        return env_vars

    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                # Skip empty lines and comments
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                # Parse KEY=VALUE format
                if '=' in line:
                    # Split on first = only
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()

                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]

                    # Handle inline comments (after value)
                    # But only if not within quotes
                    if '#' in value and not ('"' in line or "'" in line):
                        value = value.split('#')[0].strip()

                    env_vars[key] = value

    except Exception as e:
        print(f"Warning: Error reading .env file '{env_file}': {e}")

    return env_vars


def get_env(key: str, default: Optional[str] = None, env_file: str = ".env") -> Optional[str]:
    """
    Get environment variable with .env file fallback

    Priority:
    1. System environment variable
    2. .env file
    3. Default value

    Args:
        key: Environment variable name
        default: Default value if not found
        env_file: Path to .env file

    Returns:
        Environment variable value or default
    """
    # First check system environment
    value = os.environ.get(key)
    if value is not None:
        return value

    # Then check .env file
    env_vars = load_env_file(env_file)
    value = env_vars.get(key)
    if value is not None:
        return value

    # Return default
    return default


def load_dotenv(env_file: str = ".env", override: bool = False):
    """
    Load .env file into os.environ (similar to python-dotenv)

    Args:
        env_file: Path to .env file
        override: If True, override existing environment variables
    """
    env_vars = load_env_file(env_file)

    for key, value in env_vars.items():
        if override or key not in os.environ:
            os.environ[key] = value
