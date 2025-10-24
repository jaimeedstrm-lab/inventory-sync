# Logs Directory

This directory stores JSON log files from each inventory sync run.

## Log File Naming

Logs are named with timestamp: `sync_YYYY-MM-DD_HH-MM-SS.json`

Example: `sync_2025-10-24_14-30-00.json`

## Log Structure

Each log file contains:

```json
{
  "timestamp": "ISO 8601 timestamp",
  "suppliers_processed": ["supplier1", "supplier2"],
  "summary": {
    "total_supplier_products": 0,
    "matched_products": 0,
    "updated_in_shopify": 0,
    "no_change": 0,
    "not_found_in_shopify": 0,
    "duplicate_identifiers": 0,
    "flagged_for_review": 0,
    "errors": 0
  },
  "updates": [...],
  "no_changes": [...],
  "not_found": [...],
  "duplicates": [...],
  "flagged": [...],
  "errors": [...]
}
```

## Viewing Logs

```bash
# View latest log
cat logs/$(ls -t logs/*.json | head -1)

# Pretty print latest log
python -m json.tool logs/$(ls -t logs/*.json | head -1)

# Count of syncs
ls logs/*.json | wc -l

# List all logs
ls -lh logs/*.json
```

## Log Retention

Logs are kept indefinitely by default. To clean up old logs:

```bash
# Delete logs older than 30 days
find logs/ -name "sync_*.json" -mtime +30 -delete

# Keep only last 50 logs
ls -t logs/sync_*.json | tail -n +51 | xargs rm
```

## Automated Log Management

Add to crontab for automatic cleanup:

```bash
# Clean up logs older than 30 days, runs daily at 3am
0 3 * * * find /path/to/inventory-sync/logs/ -name "sync_*.json" -mtime +30 -delete
```

## Important Notes

- Log files are NOT committed to git (see .gitignore)
- Each sync creates a new log file
- Log files typically 10-100KB depending on catalog size
- Keep logs for audit trail and troubleshooting
