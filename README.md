# Inventory Sync System

Automated inventory synchronization system that mirrors stock levels from multiple suppliers to your Shopify store.

## Features

- ✅ **Multiple Supplier Support** - API-based and web scraping integrations
- ✅ **Smart Matching** - Products matched by EAN (priority) with SKU fallback
- ✅ **Safety Checks** - Prevents accidental stockouts with configurable limits
- ✅ **Comprehensive Logging** - JSON logs for every sync with full audit trail
- ✅ **Email Notifications** - Alerts for products not found and flagged items
- ✅ **Dry Run Mode** - Preview changes before applying
- ✅ **Rate Limiting** - Respects Shopify API limits with automatic retry
- ✅ **Extensible** - Easy to add new suppliers with plugin architecture

## System Requirements

- Python 3.11 or higher
- Shopify store with Admin API access
- Supplier credentials (API keys or portal logins)

## Installation

### 1. Clone or Download

```bash
cd inventory-sync
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium  # Required for web scraping suppliers
```

### 4. Configuration

#### A. Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```env
# Shopify Configuration
SHOPIFY_ACCESS_TOKEN=shpat_xxxxxxxxxxxxxxxxxxxxx
SHOPIFY_SHOP_URL=your-store.myshopify.com

# Oase Outdoors
OASE_USERNAME=your_username
OASE_PASSWORD=your_password
OASE_BASE_URL=https://api.oase-outdoors.com

# Email Notifications (optional)
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_FROM=your-email@gmail.com
EMAIL_TO=your-email@gmail.com
```

#### B. Configuration Files

Copy example configuration files:

```bash
cp config/shopify.json.example config/shopify.json
cp config/suppliers.json.example config/suppliers.json
cp config/email.json.example config/email.json  # Optional
```

Edit configuration files with your settings.

**config/shopify.json:**
```json
{
  "shop_url": "your-store.myshopify.com",
  "access_token": "shpat_xxxxx",
  "api_version": "2024-10"
}
```

**config/suppliers.json:**
```json
{
  "suppliers": [
    {
      "name": "oase_outdoors",
      "type": "api",
      "enabled": true,
      "config": {
        "base_url": "https://api.oase-outdoors.com",
        "username": "your_username",
        "password": "your_password"
      }
    }
  ],
  "status_mapping": {
    "in stock": 15,
    "på lager": 15,
    "low stock": 3,
    "out of stock": 0
  },
  "safety_limits": {
    "max_quantity_drop_percent": 80,
    "min_quantity_for_zero_check": 50,
    "enable_safety_checks": true
  }
}
```

## Usage

### Basic Commands

```bash
# Run sync for all enabled suppliers
python main.py

# Preview changes without updating (dry run)
python main.py --dry-run

# Sync only specific supplier
python main.py --supplier oase_outdoors

# Force update (bypass safety checks - use with caution!)
python main.py --force

# Combine flags
python main.py --supplier oase_outdoors --dry-run
```

### Running Tests

```bash
pytest tests/
```

### Scheduled Execution

#### On Railway (Recommended)

1. Create Railway project
2. Connect your GitHub repository
3. Add environment variables in Railway dashboard
4. Create a cron job:
   - Schedule: `0 */6 * * *` (every 6 hours)
   - Command: `python main.py`

#### Using Cron (Linux/Mac)

```bash
crontab -e
```

Add line:
```
0 */6 * * * cd /path/to/inventory-sync && /path/to/venv/bin/python main.py
```

#### Using Task Scheduler (Windows)

Create a scheduled task to run:
```
C:\path\to\venv\Scripts\python.exe C:\path\to\inventory-sync\main.py
```

## How It Works

### Sync Process

1. **Connect to Shopify** - Fetch all products with EAN/SKU and current inventory
2. **Authenticate with Suppliers** - Login to each enabled supplier
3. **Fetch Supplier Inventory** - Get current stock levels
4. **Match Products** - Match by EAN (priority), fallback to SKU
5. **Safety Checks** - Flag suspicious changes (large drops, zero-outs)
6. **Update Shopify** - Apply safe updates via Admin API
7. **Log Results** - Save detailed JSON log with all changes
8. **Send Notifications** - Email alerts for items needing attention

### Product Matching Priority

1. **EAN Match** (highest priority) - Exact match on barcode
2. **SKU Match** (fallback) - If EAN not found or not provided
3. **Not Found** - Logged and emailed for review
4. **Duplicates** - Flagged if multiple products share same identifier

### Safety Features

The system includes several safety checks to prevent accidental stockouts:

- **Large Drop Protection**: Flags updates where quantity drops by >80% (configurable)
- **Zero-Out Protection**: Flags high-inventory items (>50 units) going to zero
- **Duplicate Detection**: Identifies products with duplicate EAN/SKU
- **Dry Run Mode**: Preview all changes before applying
- **Detailed Logging**: Full audit trail of all changes

## Log Files

Logs are saved to `logs/sync_YYYY-MM-DD_HH-MM-SS.json` with structure:

```json
{
  "timestamp": "2025-10-24T14:30:00Z",
  "suppliers_processed": ["oase_outdoors"],
  "summary": {
    "total_supplier_products": 450,
    "matched_products": 420,
    "updated_in_shopify": 385,
    "not_found_in_shopify": 25,
    "flagged_for_review": 5
  },
  "updates": [...],
  "not_found": [...],
  "flagged": [...],
  "errors": [...]
}
```

## Email Notifications

Email notifications are sent when:
- ✅ Products not found in Shopify (review needed)
- ✅ Products flagged by safety checks (review needed)
- ✅ Errors during sync (action required)

Configure in `config/email.json`:

```json
{
  "smtp_host": "smtp.gmail.com",
  "smtp_port": 587,
  "username": "your-email@gmail.com",
  "password": "your_app_password",
  "from_email": "your-email@gmail.com",
  "to_emails": ["your-email@gmail.com"],
  "send_on_success": false,
  "send_on_warnings": true,
  "send_on_errors": true
}
```

**Gmail Users**: Generate an [App Password](https://support.google.com/accounts/answer/185833) for the `password` field.

## Adding New Suppliers

### 1. Create Supplier Class

Create `suppliers/your_supplier.py`:

```python
from suppliers.base import BaseSupplier

class YourSupplier(BaseSupplier):
    def authenticate(self) -> bool:
        # Implement authentication logic
        # Return True if successful
        pass

    def fetch_inventory(self) -> List[Dict[str, Any]]:
        # Fetch and return inventory data
        # Return list of dicts with: ean, sku, quantity
        pass
```

### 2. Register in main.py

Add to `get_supplier_instance()` function:

```python
elif supplier_name == "your_supplier":
    return YourSupplier(supplier_name, config, status_mapping)
```

### 3. Configure

Add to `config/suppliers.json`:

```json
{
  "name": "your_supplier",
  "type": "api",
  "enabled": true,
  "config": {
    "username": "...",
    "password": "..."
  }
}
```

### 4. Add Credentials

Add to `.env`:

```env
YOUR_SUPPLIER_USERNAME=xxx
YOUR_SUPPLIER_PASSWORD=xxx
```

## Status Mapping

The system converts text statuses to quantities. Configure in `config/suppliers.json`:

```json
"status_mapping": {
  "in stock": 15,        // Set to 15 units
  "på lager": 15,        // Norwegian: in stock
  "low stock": 3,        // Set to 3 units
  "lite på lager": 3,    // Norwegian: low stock
  "out of stock": 0,     // Set to 0 units
  "ikke på lager": 0     // Norwegian: out of stock
}
```

If supplier provides numeric quantities, they're used directly.

## Troubleshooting

### Connection Issues

```bash
# Test Shopify connection
python -c "from utils.config_loader import ConfigLoader; from core.shopify_client import ShopifyClient; c = ConfigLoader().load_shopify_config(); s = ShopifyClient(c['shop_url'], c['access_token']); s.test_connection()"
```

### Email Issues

```bash
# Test email configuration
python -c "from utils.config_loader import ConfigLoader; from utils.email_notifier import EmailNotifier; c = ConfigLoader().load_email_config(); e = EmailNotifier(**c); e.test_connection()"
```

### View Logs

```bash
# View latest log
cat logs/$(ls -t logs/ | head -1)

# Pretty print latest log
python -m json.tool logs/$(ls -t logs/ | head -1)
```

### Common Issues

**"No location found for inventory updates"**
- Your Shopify store needs at least one active location
- Check Settings > Locations in Shopify admin

**"Rate limited"**
- System automatically handles rate limiting with retries
- Shopify Basic plan: 2 requests/second
- Sync will slow down automatically if needed

**"Authentication failed"**
- Verify credentials in `.env` file
- Check supplier portal is accessible
- Some suppliers may require IP whitelisting

## Project Structure

```
inventory-sync/
├── config/              # Configuration files
│   ├── shopify.json
│   ├── suppliers.json
│   └── email.json
├── core/                # Core system components
│   ├── logger.py
│   ├── shopify_client.py
│   ├── inventory_matcher.py
│   └── inventory_updater.py
├── suppliers/           # Supplier integrations
│   ├── base.py
│   └── oase_outdoors.py
├── utils/               # Utilities
│   ├── config_loader.py
│   ├── email_notifier.py
│   └── helpers.py
├── tests/               # Unit tests
├── logs/                # Generated log files
├── main.py              # Entry point
└── requirements.txt     # Dependencies
```

## API Rate Limits

**Shopify Basic Plan:**
- 2 requests per second
- Burst limit: 40 requests
- System automatically respects limits with retry logic

**Best Practices:**
- Run sync every 4-6 hours (not more frequently)
- Use dry-run mode for testing
- Monitor log files for rate limit warnings

## Security

- ✅ Never commit `.env` file or config files with credentials
- ✅ Use environment variables for sensitive data
- ✅ Use Shopify private app tokens (not public app)
- ✅ For Gmail: use App Passwords, not account password
- ✅ Restrict Railway environment variables to production only

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Run in `--dry-run` mode to preview
3. Review configuration files
4. Check this README for troubleshooting

## License

Private project for inventory management.

---

**Built with:** Python, Shopify Admin API, Playwright
**Deployment:** Railway (recommended), or any Python hosting platform
# Railway Deployment
