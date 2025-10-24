# Email Notification Setup Guide

## Quick Fix for Gmail

The error you got means Gmail rejected the login because:
1. You're using your regular password (not allowed for apps)
2. You need an "App Password" instead

### Step 1: Enable 2-Factor Authentication

1. Go to: https://myaccount.google.com/security
2. Find "2-Step Verification"
3. Enable it if not already enabled

### Step 2: Generate App Password

1. Go to: https://myaccount.google.com/apppasswords
2. Select app: "Mail"
3. Select device: "Other (custom name)" → Type: "Inventory Sync"
4. Click "Generate"
5. Copy the 16-character password (looks like: `abcd efgh ijkl mnop`)

### Step 3: Update .env File

```bash
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=abcdefghijklmnop  # ← The 16-char app password (no spaces)
EMAIL_FROM=your-email@gmail.com
EMAIL_TO=your-email@gmail.com
```

### Step 4: Test Email

```bash
source venv/bin/activate
python -c "from utils.config_loader import ConfigLoader; from utils.email_notifier import EmailNotifier; c = ConfigLoader().load_email_config(); e = EmailNotifier(**c); e.test_connection()"
```

## Alternative: Disable Email Notifications

If you don't want email notifications right now, you can disable them:

**Option 1: Remove email config**
```bash
rm config/email.json
```

**Option 2: Or just ignore the error**
The sync will still work fine, you just won't get email notifications.

## Alternative Email Providers

### Using Outlook/Hotmail

```bash
EMAIL_SMTP_HOST=smtp.office365.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your-email@outlook.com
EMAIL_PASSWORD=your_password
```

### Using SendGrid (Free tier: 100 emails/day)

1. Sign up at: https://sendgrid.com/
2. Create API key
3. Configure:

```bash
EMAIL_SMTP_HOST=smtp.sendgrid.net
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=apikey
EMAIL_PASSWORD=your_sendgrid_api_key
EMAIL_FROM=your-verified-sender@yourdomain.com
```

### Using Mailgun (Free tier: 1000 emails/month)

1. Sign up at: https://www.mailgun.com/
2. Verify domain or use sandbox
3. Get SMTP credentials

```bash
EMAIL_SMTP_HOST=smtp.mailgun.org
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=postmaster@your-domain.mailgun.org
EMAIL_PASSWORD=your_mailgun_password
```

## Testing Email

After configuring, test with:

```bash
source venv/bin/activate
python test_email.py
```

Where test_email.py contains:

```python
from utils.config_loader import ConfigLoader
from utils.email_notifier import EmailNotifier

config_loader = ConfigLoader()
email_config = config_loader.load_email_config()

notifier = EmailNotifier(**email_config)

if notifier.test_connection():
    print("✓ Email configuration working!")

    # Send test email
    notifier.send_sync_report(
        summary={"total_supplier_products": 10, "matched_products": 8, "errors": 0},
        not_found_products=[{"ean": "123", "sku": "TEST"}],
        flagged_products=[],
        errors=[],
        suppliers_processed=["test"]
    )
    print("✓ Test email sent!")
else:
    print("✗ Email configuration failed")
```

## For Now: Skip Email

You can run the system without email notifications. They're optional!

Just run the sync and check logs manually:

```bash
python main.py --dry-run
cat logs/sync_*.json | tail -1
```
