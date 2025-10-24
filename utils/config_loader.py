"""Configuration loader for inventory sync system."""
import json
import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv


class ConfigLoader:
    """Load and manage configuration from JSON files and environment variables."""

    def __init__(self, config_dir: str = "config"):
        """Initialize configuration loader.

        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        load_dotenv()  # Load environment variables from .env file

    def load_json(self, filename: str) -> Dict[str, Any]:
        """Load JSON configuration file.

        Args:
            filename: Name of the JSON file (without .json extension)

        Returns:
            Dictionary containing configuration data

        Raises:
            FileNotFoundError: If configuration file doesn't exist
            json.JSONDecodeError: If JSON is invalid
        """
        file_path = self.config_dir / f"{filename}.json"

        if not file_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {file_path}\n"
                f"Please copy {file_path}.example to {file_path} and configure it."
            )

        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_shopify_config(self) -> Dict[str, Any]:
        """Load Shopify configuration with environment variable overrides.

        Returns:
            Dictionary containing Shopify configuration
        """
        try:
            config = self.load_json("shopify")
        except FileNotFoundError:
            # If file doesn't exist, use environment variables only
            config = {}

        # Override with environment variables if present
        config['shop_url'] = os.getenv('SHOPIFY_SHOP_URL', config.get('shop_url'))
        config['access_token'] = os.getenv('SHOPIFY_ACCESS_TOKEN', config.get('access_token'))
        config['api_version'] = os.getenv('SHOPIFY_API_VERSION', config.get('api_version', '2024-10'))

        # Validate required fields
        if not config.get('shop_url') or not config.get('access_token'):
            raise ValueError(
                "Missing required Shopify configuration. "
                "Please set SHOPIFY_SHOP_URL and SHOPIFY_ACCESS_TOKEN in .env file or config/shopify.json"
            )

        return config

    def load_suppliers_config(self) -> Dict[str, Any]:
        """Load suppliers configuration with environment variable overrides.

        Returns:
            Dictionary containing suppliers configuration
        """
        config = self.load_json("suppliers")

        # Override supplier credentials with environment variables if present
        for supplier in config.get('suppliers', []):
            supplier_name = supplier.get('name', '')
            if not supplier_name:
                continue

            supplier_config = supplier.setdefault('config', {})

            prefixes = []
            env_prefix = supplier.get('env_prefix')
            if env_prefix:
                prefixes.append(env_prefix)
            prefixes.append(supplier_name)
            prefixes.append(supplier_name.replace('-', '_'))
            prefixes.append(supplier_name.replace('-', '').replace('_', ''))
            prefixes = [p.upper() for p in prefixes if p]

            def _get_first_env_var(keys):
                for key in keys:
                    value = os.getenv(key)
                    if value:
                        return value
                return None

            username = _get_first_env_var([f"{prefix}_USERNAME" for prefix in prefixes])
            if username:
                supplier_config['username'] = username

            password = _get_first_env_var([f"{prefix}_PASSWORD" for prefix in prefixes])
            if password:
                supplier_config['password'] = password

        return config

    def load_email_config(self) -> Dict[str, Any]:
        """Load email configuration with environment variable overrides.

        Returns:
            Dictionary containing email configuration
        """
        try:
            config = self.load_json("email")
        except FileNotFoundError:
            # If file doesn't exist, use environment variables only
            config = {}

        # Override with environment variables if present
        config['smtp_host'] = os.getenv('EMAIL_SMTP_HOST', config.get('smtp_host'))
        config['smtp_port'] = int(os.getenv('EMAIL_SMTP_PORT', config.get('smtp_port', 587)))
        config['username'] = os.getenv('EMAIL_USERNAME', config.get('username'))
        config['password'] = os.getenv('EMAIL_PASSWORD', config.get('password'))
        config['from_email'] = os.getenv('EMAIL_FROM', config.get('from_email'))

        to_emails = os.getenv('EMAIL_TO')
        if to_emails:
            config['to_emails'] = [email.strip() for email in to_emails.split(',')]

        config['send_on_success'] = os.getenv('EMAIL_SEND_ON_SUCCESS',
                                               str(config.get('send_on_success', False))).lower() == 'true'
        config['send_on_warnings'] = os.getenv('EMAIL_SEND_ON_WARNINGS',
                                                str(config.get('send_on_warnings', True))).lower() == 'true'
        config['send_on_errors'] = os.getenv('EMAIL_SEND_ON_ERRORS',
                                              str(config.get('send_on_errors', True))).lower() == 'true'

        return config

    def get_enabled_suppliers(self) -> list:
        """Get list of enabled supplier configurations.

        Returns:
            List of enabled supplier configuration dictionaries
        """
        suppliers_config = self.load_suppliers_config()
        return [s for s in suppliers_config.get('suppliers', []) if s.get('enabled', False)]

    def get_status_mapping(self) -> Dict[str, int]:
        """Get status to quantity mapping.

        Returns:
            Dictionary mapping status strings to inventory quantities
        """
        suppliers_config = self.load_suppliers_config()
        return suppliers_config.get('status_mapping', {})

    def get_safety_limits(self) -> Dict[str, Any]:
        """Get safety limit configuration.

        Returns:
            Dictionary containing safety limit settings
        """
        suppliers_config = self.load_suppliers_config()
        return suppliers_config.get('safety_limits', {
            'max_quantity_drop_percent': 80,
            'min_quantity_for_zero_check': 50,
            'enable_safety_checks': True
        })
