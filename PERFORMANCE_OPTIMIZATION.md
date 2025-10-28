# Performance Optimization for Web Scraping Suppliers

## Problem
Order Nordic sync was timing out after 6 hours in GitHub Actions when processing 2370 products.

## Root Cause Analysis
1. **GitHub Actions 6-hour timeout limit** - Hard limit on job execution time
2. **Slow scraping per product**: Each product took ~4-5 seconds to scrape
   - 500ms delay between products
   - 10-11 seconds waiting for page loads (networkidle + extra wait)
3. **Total time calculation**:
   - 2370 products × 4 seconds = 9,480 seconds = 2.6 hours
   - With overhead and Shopify API fetching = 4-6 hours total
   - **Result**: Consistently hitting the 6-hour timeout limit

## Optimizations Implemented

### Order Nordic (`suppliers/order_nordic.py`)

#### 1. Reduced page load waiting times
**Before:**
```python
self.page.wait_for_load_state("networkidle", timeout=10000)
self.page.wait_for_timeout(1000)
```

**After:**
```python
self.page.wait_for_load_state("domcontentloaded", timeout=5000)
self.page.wait_for_timeout(500)
```

**Impact**: ~6 seconds saved per product search

#### 2. Reduced delay between products
**Before:**
```python
self.page.wait_for_timeout(500)  # 500ms delay
```

**After:**
```python
self.page.wait_for_timeout(100)  # 100ms delay
```

**Impact**: 400ms × 2370 = 948 seconds = 15.8 minutes saved

#### 3. Optimized product page navigation
**Before:**
```python
self.page.wait_for_load_state("networkidle", timeout=10000)
self.page.wait_for_timeout(1000)
```

**After:**
```python
self.page.wait_for_load_state("domcontentloaded", timeout=5000)
self.page.wait_for_timeout(500)
```

**Impact**: Additional time savings on product page loads

### Response Nordic (`suppliers/response_nordic.py`)

Applied similar optimizations for consistency and future-proofing:

#### 1. Reduced typing delay for search
**Before:**
```python
search_box.type(ean, delay=200)
```

**After:**
```python
search_box.type(ean, delay=100)
```

#### 2. Reduced instant search wait time
**Before:**
```python
self.page.wait_for_timeout(5000)  # 5 seconds
```

**After:**
```python
self.page.wait_for_timeout(2000)  # 2 seconds
```

#### 3. Optimized product link wait and page load
**Before:**
```python
product_link.wait_for(state="visible", timeout=10000)
self.page.wait_for_load_state("domcontentloaded", timeout=15000)
self.page.wait_for_timeout(1500)
```

**After:**
```python
product_link.wait_for(state="visible", timeout=5000)
self.page.wait_for_load_state("domcontentloaded", timeout=8000)
self.page.wait_for_timeout(800)
```

#### 4. Reduced delay between products
**Before:**
```python
self.page.wait_for_timeout(500)  # 500ms delay
```

**After:**
```python
self.page.wait_for_timeout(100)  # 100ms delay
```

## Expected Performance Improvement

### Order Nordic (2370 products)
- **Delay savings**: 15.8 minutes (400ms × 2370)
- **Page load savings**: ~2-6 seconds per product × 2370 = 1.3 to 3.9 hours
- **Total expected time**: ~1.5 to 2 hours (down from 4-6 hours)
- **Result**: Should fit within GitHub Actions 6-hour limit

### Response Nordic (328 products)
- Already completing successfully, but will be faster
- Estimated time reduction: 30-40%

### Petcare (287 products)
- Not modified (uses different search approach)
- Already completing successfully

## Technical Notes

### Why `domcontentloaded` instead of `networkidle`?
- `networkidle` waits for all network connections to be idle (no network activity for 500ms)
- `domcontentloaded` waits only for HTML to be parsed and DOM ready
- For scraping, we only need the DOM elements to be present, not all images/resources loaded
- This typically saves 2-8 seconds per page load

### Why reduce delays between products?
- The 500ms delay was overly cautious to avoid rate limiting
- 100ms is sufficient to prevent overwhelming the server
- Web servers can typically handle multiple requests per second
- If rate limiting occurs, we can adjust back up

### Risks and Mitigation
1. **Risk**: Server might reject requests if we scrape too fast
   - **Mitigation**: 100ms delay still provides rate limiting (10 requests/second)
   - **Fallback**: Can increase back to 200-300ms if needed

2. **Risk**: Elements might not be loaded in time with shorter waits
   - **Mitigation**: Using explicit element waits with timeouts still in place
   - **Fallback**: Error handling will catch and log failed product searches

3. **Risk**: Some products might be missed due to faster scraping
   - **Mitigation**: Validation logic still in place to verify product data
   - **Fallback**: Products that fail will be logged and can be retried

## Testing Recommendations

1. **Test Order Nordic sync** in GitHub Actions
   - Monitor execution time (should be under 2 hours)
   - Verify all products are found and scraped correctly
   - Check for any new error patterns

2. **Monitor success rate**
   - Compare product match rates before and after optimization
   - Ensure no degradation in data quality

3. **Watch for rate limiting**
   - If server returns 429 errors or blocks requests, increase delays

## Alternative Solutions (Not Implemented)

If these optimizations are insufficient:

1. **Batch processing**: Split products into multiple jobs
2. **Parallel processing**: Run multiple browser instances
3. **Server-side filtering**: Request Shopify to filter by tags server-side
4. **GraphQL**: Use Shopify GraphQL API for faster queries
5. **Local execution**: Run large syncs locally instead of GitHub Actions
