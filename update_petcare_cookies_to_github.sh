#!/bin/bash
# Script to refresh Petcare cookies and automatically update GitHub Secret

set -e  # Exit on error

echo "=================================================="
echo "Petcare Cookie Updater (with GitHub integration)"
echo "=================================================="
echo ""

# Step 1: Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "⚠️  GitHub CLI (gh) is not installed."
    echo ""
    echo "To install:"
    echo "  brew install gh"
    echo ""
    echo "After installation, authenticate with:"
    echo "  gh auth login"
    echo ""
    echo "For now, we'll just refresh cookies locally."
    echo "You'll need to update GitHub Secret manually."
    echo ""
    MANUAL_MODE=true
else
    # Check if authenticated
    if ! gh auth status &> /dev/null; then
        echo "⚠️  GitHub CLI is installed but not authenticated."
        echo ""
        echo "Please run: gh auth login"
        echo ""
        echo "For now, we'll just refresh cookies locally."
        echo "You'll need to update GitHub Secret manually."
        echo ""
        MANUAL_MODE=true
    else
        echo "✓ GitHub CLI is installed and authenticated"
        MANUAL_MODE=false
    fi
fi

echo ""

# Step 2: Refresh cookies
echo "Step 1: Refreshing Petcare cookies..."
echo "---------------------------------------"
python3 refresh_petcare_cookies.py

# Check if cookies file was created
if [ ! -f "cookies/petcare_cookies.json" ]; then
    echo ""
    echo "❌ Cookie file not found. Something went wrong."
    exit 1
fi

echo ""
echo "✓ Cookies refreshed successfully!"
echo ""

# Step 3: Update GitHub Secret
if [ "$MANUAL_MODE" = true ]; then
    echo "Step 2: Copy to clipboard (manual mode)"
    echo "---------------------------------------"
    cat cookies/petcare_cookies.json | pbcopy
    echo "✓ Cookies copied to clipboard!"
    echo ""
    echo "📋 Manual steps:"
    echo "   1. Go to: https://github.com/jaimeedstrm-lab/inventory-sync/settings/secrets/actions"
    echo "   2. Click on 'PETCARE_COOKIES' → 'Update'"
    echo "   3. Paste (Cmd+V) the new content"
    echo "   4. Click 'Update secret'"
    echo ""
else
    echo "Step 2: Updating GitHub Secret..."
    echo "---------------------------------------"

    # Read cookie content
    COOKIE_CONTENT=$(cat cookies/petcare_cookies.json)

    # Update GitHub Secret
    echo "$COOKIE_CONTENT" | gh secret set PETCARE_COOKIES -R jaimeedstrm-lab/inventory-sync

    if [ $? -eq 0 ]; then
        echo "✓ GitHub Secret updated successfully!"
        echo ""
        echo "✅ All done! Petcare cookies are now updated in GitHub Actions."
    else
        echo "❌ Failed to update GitHub Secret."
        echo ""
        echo "Manual fallback: Cookies copied to clipboard"
        cat cookies/petcare_cookies.json | pbcopy
        echo "Please update manually at:"
        echo "https://github.com/jaimeedstrm-lab/inventory-sync/settings/secrets/actions"
    fi
fi

echo ""
echo "=================================================="
echo "Summary"
echo "=================================================="
echo "Cookies file: cookies/petcare_cookies.json"
echo "Total cookies: $(cat cookies/petcare_cookies.json | grep -c '"name":')"
echo "Next update: In ~2 months"
echo ""
