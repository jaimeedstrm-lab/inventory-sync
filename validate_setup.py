#!/usr/bin/env python3
"""Quick validation script to check if the setup is correct."""
import sys
from pathlib import Path


def check_file(path: str, description: str) -> bool:
    """Check if a file exists."""
    if Path(path).exists():
        print(f"✓ {description}")
        return True
    else:
        print(f"✗ {description} - MISSING: {path}")
        return False


def validate_setup():
    """Validate the project setup."""
    print("=" * 60)
    print("Inventory Sync - Setup Validation")
    print("=" * 60)
    print()

    checks = [
        # Core files
        ("main.py", "Main entry point"),
        ("requirements.txt", "Python dependencies"),
        ("setup.sh", "Setup script"),
        (".env.example", "Environment variables template"),
        (".gitignore", "Git ignore file"),

        # Configuration
        ("config/shopify.json.example", "Shopify config template"),
        ("config/suppliers.json.example", "Suppliers config template"),
        ("config/email.json.example", "Email config template"),

        # Core modules
        ("core/logger.py", "Logger module"),
        ("core/shopify_client.py", "Shopify client"),
        ("core/inventory_matcher.py", "Inventory matcher"),
        ("core/inventory_updater.py", "Inventory updater"),

        # Suppliers
        ("suppliers/base.py", "Base supplier class"),
        ("suppliers/oase_outdoors.py", "Oase Outdoors integration"),

        # Utils
        ("utils/config_loader.py", "Config loader"),
        ("utils/helpers.py", "Helper functions"),
        ("utils/email_notifier.py", "Email notifier"),

        # Tests
        ("tests/test_helpers.py", "Helper tests"),
        ("tests/test_matcher.py", "Matcher tests"),

        # Documentation
        ("README.md", "Main documentation"),
        ("QUICKSTART.md", "Quick start guide"),
        ("SCRAPING_GUIDE.md", "Scraping guide"),
        ("RAILWAY_DEPLOYMENT.md", "Deployment guide"),
        ("PROJECT_SUMMARY.md", "Project summary"),

        # Deployment
        ("Dockerfile", "Docker configuration"),
        ("railway.json", "Railway configuration"),
    ]

    all_ok = True
    for file_path, description in checks:
        if not check_file(file_path, description):
            all_ok = False

    print()
    print("=" * 60)

    if all_ok:
        print("✓ ALL CHECKS PASSED!")
        print()
        print("Next steps:")
        print("1. Run: ./setup.sh")
        print("2. Edit .env with your credentials")
        print("3. Test: python main.py --dry-run")
        print()
        return 0
    else:
        print("✗ SOME FILES ARE MISSING!")
        print()
        print("Please ensure all files are created correctly.")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(validate_setup())
