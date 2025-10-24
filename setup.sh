#!/bin/bash

# Setup script for inventory-sync system

echo "=========================================="
echo "Inventory Sync System - Setup"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | sed -n 's/Python \([0-9]\+\.[0-9]\+\).*/\1/p')

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
    echo "❌ Python 3.11 or higher is required. You have Python $python_version"
    exit 1
fi
echo "✓ Python version OK ($python_version)"
echo ""

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Install Playwright browsers
echo "Installing Playwright browsers (for web scraping)..."
playwright install chromium
echo "✓ Playwright browsers installed"
echo ""

# Create configuration files from examples
echo "Setting up configuration files..."

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✓ Created .env file - PLEASE EDIT THIS FILE WITH YOUR CREDENTIALS"
else
    echo "✓ .env file already exists"
fi

if [ ! -f "config/shopify.json" ]; then
    cp config/shopify.json.example config/shopify.json
    echo "✓ Created config/shopify.json - PLEASE EDIT THIS FILE"
else
    echo "✓ config/shopify.json already exists"
fi

if [ ! -f "config/suppliers.json" ]; then
    cp config/suppliers.json.example config/suppliers.json
    echo "✓ Created config/suppliers.json - PLEASE EDIT THIS FILE"
else
    echo "✓ config/suppliers.json already exists"
fi

if [ ! -f "config/email.json" ]; then
    cp config/email.json.example config/email.json
    echo "✓ Created config/email.json (optional) - EDIT IF YOU WANT EMAIL NOTIFICATIONS"
else
    echo "✓ config/email.json already exists"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your credentials"
echo "2. Edit config/*.json files with your settings"
echo "3. Test with: python main.py --dry-run"
echo "4. Run sync: python main.py"
echo ""
echo "For help: python main.py --help"
echo ""
