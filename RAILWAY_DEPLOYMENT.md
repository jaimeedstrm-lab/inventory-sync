# Railway Deployment Guide

Deploy your inventory sync system to Railway for automatic scheduled execution.

## Why Railway?

- ✅ Free tier ($5/month credit, usually enough)
- ✅ Easy deployment from GitHub
- ✅ Built-in cron job support
- ✅ Environment variable management
- ✅ Automatic builds and deployments
- ✅ Logs and monitoring

## Prerequisites

- GitHub account
- Railway account (sign up at https://railway.app)
- Your inventory-sync code in a GitHub repository

## Step 1: Push Code to GitHub

```bash
cd inventory-sync

# Initialize git (if not already)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: Inventory sync system"

# Create GitHub repository and push
# Follow GitHub instructions to create repo
git remote add origin https://github.com/yourusername/inventory-sync.git
git branch -M main
git push -u origin main
```

## Step 2: Create Railway Project

1. Go to https://railway.app
2. Sign up / Log in with GitHub
3. Click "New Project"
4. Select "Deploy from GitHub repo"
5. Authorize Railway to access your repositories
6. Select your `inventory-sync` repository
7. Click "Deploy Now"

Railway will automatically:
- Detect the Dockerfile
- Build the container
- Deploy it

## Step 3: Configure Environment Variables

In Railway dashboard:

1. Click on your project
2. Go to "Variables" tab
3. Click "Raw Editor"
4. Paste all your environment variables:

```env
SHOPIFY_ACCESS_TOKEN=shpat_your_token_here
SHOPIFY_SHOP_URL=your-store.myshopify.com
SHOPIFY_API_VERSION=2024-10

OASE_USERNAME=your_username
OASE_PASSWORD=your_password
OASE_BASE_URL=https://api.oase-outdoors.com

EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_FROM=your-email@gmail.com
EMAIL_TO=your-email@gmail.com
EMAIL_SEND_ON_SUCCESS=false
EMAIL_SEND_ON_WARNINGS=true
EMAIL_SEND_ON_ERRORS=true
```

5. Click "Save"

**Important:** Never commit `.env` file to GitHub! Always use Railway's environment variables.

## Step 4: Set Up Cron Job

Railway will initially deploy as a one-time run. We need to configure it as a cron job.

### Option A: Using Railway Cron (Recommended)

1. In Railway dashboard, go to your service
2. Click "Settings"
3. Under "Service", change type to "Cron Job"
4. Set schedule: `0 */6 * * *` (every 6 hours)
5. Click "Save"

### Option B: Using GitHub Actions

If Railway's cron is not available on free tier, use GitHub Actions:

Create `.github/workflows/sync.yml`:

```yaml
name: Inventory Sync

on:
  schedule:
    # Run every 6 hours
    - cron: '0 */6 * * *'
  workflow_dispatch: # Allow manual trigger

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          playwright install chromium
          playwright install-deps

      - name: Run sync
        env:
          SHOPIFY_ACCESS_TOKEN: ${{ secrets.SHOPIFY_ACCESS_TOKEN }}
          SHOPIFY_SHOP_URL: ${{ secrets.SHOPIFY_SHOP_URL }}
          OASE_USERNAME: ${{ secrets.OASE_USERNAME }}
          OASE_PASSWORD: ${{ secrets.OASE_PASSWORD }}
          EMAIL_USERNAME: ${{ secrets.EMAIL_USERNAME }}
          EMAIL_PASSWORD: ${{ secrets.EMAIL_PASSWORD }}
        run: python main.py
```

Then add secrets in GitHub:
- Go to repo → Settings → Secrets and variables → Actions
- Add each environment variable as a secret

## Step 5: Test Deployment

### Manual Trigger (Test Run)

In Railway dashboard:
1. Go to "Deployments"
2. Click "Deploy" to trigger manually
3. Watch the logs to ensure it runs successfully

### Check Logs

In Railway dashboard:
1. Click on your deployment
2. Go to "Logs" tab
3. Watch the output in real-time

Expected output:
```
Loading configuration...
Connecting to Shopify...
✓ Successfully connected to Shopify store: Your Store Name
Fetching products from Shopify...
✓ Loaded 500 product identifiers from Shopify
...
```

## Step 6: Monitor & Maintain

### View Logs

Railway keeps recent logs. To view:
1. Go to Railway dashboard
2. Click your service
3. Click "Logs"

### Download Historical Logs

Since logs are stored in the container, they'll be lost on restart. To persist logs:

**Option 1: Add Railway Volume**
1. In Railway, add a Volume
2. Mount at `/app/logs`
3. Logs will persist across deployments

**Option 2: Send Logs to External Service**

Add to `main.py` to upload logs to S3, Google Drive, etc. after each sync.

**Option 3: Email Logs**

Modify email notifier to attach log file to email.

### Scaling Considerations

**Free Tier Limits:**
- $5 credit per month
- ~500 hours execution time
- If you run every 6 hours (4× daily):
  - ~30 seconds per run = 2 minutes/day
  - ~60 minutes/month = ~$0.50/month
  - Well within free tier!

**If You Exceed:**
- Add payment method (pay-as-you-go)
- Or reduce sync frequency to every 12 hours

## Troubleshooting Railway Deployment

### Issue: "Build failed"

**Check:**
- Dockerfile syntax
- All dependencies in requirements.txt
- Railway logs for specific error

**Fix:**
```bash
# Test locally first
docker build -t inventory-sync .
docker run -it --env-file .env inventory-sync
```

### Issue: "Runtime error"

**Check:**
- Environment variables are set correctly in Railway
- Shopify API credentials are valid
- Supplier credentials are correct

**Fix:**
- Review Railway logs
- Test locally with same environment variables

### Issue: "Playwright browser not found"

**Fix:** Make sure Dockerfile includes:
```dockerfile
RUN playwright install chromium
RUN playwright install-deps chromium
```

### Issue: "Connection timeout"

**Possible causes:**
- Supplier portal blocking Railway's IP
- Network issue
- Rate limiting

**Fix:**
- Check supplier portal accessibility
- Add retry logic
- Contact supplier about IP whitelisting

## Railway Dashboard Overview

### Key Sections

1. **Overview** - Status, last deployment, metrics
2. **Deployments** - History of all deployments
3. **Logs** - Real-time and historical logs
4. **Metrics** - CPU, memory, network usage
5. **Settings** - Configure service, cron schedule
6. **Variables** - Environment variables

### Useful Commands

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link project
railway link

# View logs locally
railway logs

# Run command in Railway environment
railway run python main.py --dry-run
```

## Cost Estimation

**Typical usage (4× daily):**
- Runtime per sync: ~30 seconds
- Memory: ~200MB
- Network: ~10MB per sync

**Monthly estimate:**
- Execution time: ~2 hours/month
- Cost: ~$0.50/month (well within $5 free tier)

**With 3 suppliers, 6× daily:**
- Runtime per sync: ~60 seconds
- Monthly: ~6 hours
- Cost: ~$1.50/month (still within free tier)

## Security Best Practices

1. ✅ **Never commit secrets** - Use Railway environment variables
2. ✅ **Use read-only API tokens** where possible
3. ✅ **Enable 2FA** on Railway account
4. ✅ **Rotate credentials** regularly
5. ✅ **Monitor logs** for suspicious activity
6. ✅ **Use HTTPS** for all API calls

## Rollback Procedure

If a deployment causes issues:

1. In Railway dashboard → Deployments
2. Find previous working deployment
3. Click "Redeploy"

Or via CLI:
```bash
railway rollback
```

## Advanced: Multiple Environments

Create separate Railway projects for:

**Production:**
- Runs every 6 hours
- Updates live Shopify inventory
- Production credentials

**Staging:**
- Runs on-demand
- Uses test Shopify store
- Test credentials

To deploy to staging:
```bash
railway environment staging
railway up
```

## Monitoring & Alerts

### Built-in Railway Monitoring

Railway provides:
- CPU usage graphs
- Memory usage
- Network traffic
- Deployment history

### External Monitoring

For advanced monitoring, integrate with:

- **Sentry** - Error tracking
- **DataDog** - Application monitoring
- **UptimeRobot** - Uptime monitoring (check cron execution)

### Email Alerts

Already built-in! Your system emails you when:
- Products not found
- Safety checks triggered
- Errors occur

## Updating Your Deployment

When you make code changes:

```bash
git add .
git commit -m "Update supplier integration"
git push
```

Railway automatically:
1. Detects the push
2. Rebuilds the container
3. Deploys the new version
4. Switches traffic to new version

**Zero-downtime deployment!**

## Alternative Hosting Options

If Railway doesn't work for you:

### PythonAnywhere
- Similar to Railway
- $5/month for scheduled tasks
- Good Python support

### Heroku
- More expensive ($7/month minimum)
- Better free tier features in the past
- Good documentation

### AWS Lambda + EventBridge
- Pay per execution
- Very cheap for infrequent runs
- More complex setup

### Your Own Server
- One-time cost
- Full control
- Requires maintenance

## Need Help?

Railway documentation: https://docs.railway.app
Railway Discord: https://discord.gg/railway

---

**You're all set!** Your inventory sync is now running automatically in the cloud. 🚀
