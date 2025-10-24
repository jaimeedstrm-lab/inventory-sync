# Quick Start Guide

Get your inventory sync system running in 5 minutes.

## Prerequisites

- Python 3.11+
- Shopify store with Admin API access
- Supplier credentials (for Oase Outdoors or other suppliers)

## Installation

### Step 1: Run Setup Script

```bash
cd inventory-sync
./setup.sh
```

This will:
- Create virtual environment
- Install dependencies
- Install Playwright browsers
- Create configuration files from examples

### Step 2: Configure Shopify

Edit `.env` file:

```env
SHOPIFY_ACCESS_TOKEN=shpat_your_token_here
SHOPIFY_SHOP_URL=your-store.myshopify.com
```

**How to get Shopify credentials:**

1. Go to Shopify Admin → Settings → Apps and sales channels
2. Click "Develop apps" → "Create an app"
3. Name it "Inventory Sync"
4. Configure Admin API scopes:
   - `read_products`
   - `write_products`
   - `read_inventory`
   - `write_inventory`
   - `read_locations`
5. Install app and copy the Admin API access token

### Step 3: Configure Oase Outdoors

Edit `.env` file:

```env
OASE_USERNAME=your_username
OASE_PASSWORD=your_password
OASE_BASE_URL=https://your-oase-api-url.com
```

### Step 4: Test Connection

```bash
source venv/bin/activate  # Activate virtual environment
python main.py --dry-run
```

This will:
- Connect to Shopify
- Fetch your products
- Connect to Oase Outdoors
- Fetch their inventory
- Match products by EAN/SKU
- **Preview** changes (without updating)

### Step 5: Review Results

Check the output:

```
============================================================
SYNC SUMMARY
============================================================
Suppliers processed: oase_outdoors

Products:
  Total from suppliers:     450
  Matched in Shopify:       420
  Updated in Shopify:       0  ← 0 because dry-run
  No change needed:         35

Issues:
  Not found in Shopify:     25  ← Review these
  Duplicate identifiers:    0
  Flagged for review:       5   ← Review these
  Errors:                   0

Log file: logs/sync_2025-10-24_14-30-00.json
============================================================
```

### Step 6: Review Flagged Items

If items are flagged, check the log file:

```bash
cat logs/sync_2025-10-24_14-30-00.json | grep -A 5 "flagged"
```

Example flagged item:
```json
{
  "sku": "ABC-123",
  "reason": "quantity_drop_82% (was 100, now 18)",
  "old_qty": 100,
  "new_qty": 18
}
```

**What to do:**
- Verify this is correct with your supplier
- If correct, run with `--force` to bypass safety check
- If incorrect, contact supplier about data issue

### Step 7: Run Real Sync

Once you're confident:

```bash
python main.py
```

This will update your Shopify inventory!

## Common First-Run Issues

### "Configuration error: Missing required Shopify configuration"

**Fix:** Make sure `.env` file has `SHOPIFY_ACCESS_TOKEN` and `SHOPIFY_SHOP_URL`

### "Authentication failed with oase_outdoors"

**Fix:** Check credentials in `.env` file. Try logging in manually to supplier portal to verify.

### "No location found for inventory updates"

**Fix:** Go to Shopify Admin → Settings → Locations and ensure you have at least one active location.

### "Not found in Shopify: 25 products"

**Fix:** These products exist in supplier data but not in your Shopify store. You'll get an email list. Options:
- Add these products to Shopify
- Ignore them (they'll be logged but won't cause errors)

## Setting Up Email Notifications

### For Gmail

1. Enable 2FA on your Google account
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Edit `.env`:

```env
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your_app_password_here
EMAIL_FROM=your-email@gmail.com
EMAIL_TO=your-email@gmail.com
```

### Test Email

```bash
python -c "from utils.config_loader import ConfigLoader; from utils.email_notifier import EmailNotifier; c = ConfigLoader().load_email_config(); e = EmailNotifier(**c); e.test_connection()"
```

## Scheduling Automatic Syncs

### Option 1: Railway (Recommended)

1. Create Railway account: https://railway.app
2. Create new project
3. Connect GitHub repository
4. Add environment variables from `.env` file
5. Create cron job:
   - Name: Inventory Sync
   - Schedule: `0 */6 * * *` (every 6 hours)
   - Command: `python main.py`

### Option 2: Local Cron (Linux/Mac)

```bash
crontab -e
```

Add:
```
0 */6 * * * cd /Users/youruser/inventory-sync && /Users/youruser/inventory-sync/venv/bin/python main.py
```

### Option 3: Task Scheduler (Windows)

1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily, repeat every 6 hours
4. Action: Start a program
   - Program: `C:\path\to\inventory-sync\venv\Scripts\python.exe`
   - Arguments: `main.py`
   - Start in: `C:\path\to\inventory-sync`

## Daily Workflow

Once set up, the system runs automatically. You just need to:

1. **Check emails** for flagged items or products not found
2. **Review logs** occasionally: `ls -lh logs/`
3. **Handle flagged items** by verifying with suppliers
4. **Add missing products** to Shopify if needed

## Understanding the Output

### Green ✓ = Good
- Authentication successful
- Products matched
- Inventory updated

### Yellow ⚠️ = Review Needed
- Products not found in Shopify → Add them or ignore
- Flagged for safety review → Verify with supplier
- Duplicate identifiers → Clean up your Shopify catalog

### Red ✗ = Action Required
- Authentication failed → Check credentials
- API errors → Check Shopify connection
- Rate limited → System handles automatically, but check if excessive

## CLI Commands Reference

```bash
# Preview changes (recommended first)
python main.py --dry-run

# Run actual sync
python main.py

# Sync only Oase Outdoors
python main.py --supplier oase_outdoors

# Force update (bypass safety checks)
python main.py --force

# Combine: preview Oase only
python main.py --supplier oase_outdoors --dry-run

# Help
python main.py --help
```

## Next Steps

- ✅ Add more suppliers (see SCRAPING_GUIDE.md)
- ✅ Customize status mapping in `config/suppliers.json`
- ✅ Adjust safety limits in `config/suppliers.json`
- ✅ Set up monitoring/alerting
- ✅ Review logs regularly

## Support Checklist

If something goes wrong:

1. ✅ Check log files: `cat logs/$(ls -t logs/ | head -1)`
2. ✅ Run in dry-run mode: `python main.py --dry-run`
3. ✅ Test Shopify connection
4. ✅ Test supplier authentication manually
5. ✅ Check configuration files
6. ✅ Review this guide

## Success Indicators

You'll know it's working when:

- ✅ Dry-run completes without errors
- ✅ Products are matched successfully
- ✅ Updates are applied to Shopify
- ✅ Log files show successful syncs
- ✅ Email notifications arrive (if configured)
- ✅ Shopify inventory matches supplier inventory

---

**Ready to go!** Run `python main.py --dry-run` to start.
