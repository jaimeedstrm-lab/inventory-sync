"""Real end-to-end test with actual Shopify updates.

WARNING: This will ACTUALLY UPDATE inventory in Shopify!
Only use this for testing with a few products.

This test:
1. Picks 3 products from Shopify (Order Nordic tagged)
2. Searches Order Nordic for their current stock
3. ACTUALLY updates Shopify with the new quantities
4. Verifies the updates were successful
5. Shows before/after comparison
"""
import sys
import time
from utils.config_loader import ConfigLoader
from core.shopify_client import ShopifyClient
from core.inventory_matcher import InventoryMatcher
from core.inventory_updater import InventoryUpdater
from suppliers.order_nordic import OrderNordicSupplier


def test_real_update():
    """Test with real Shopify updates."""
    print("="*70)
    print("REAL UPDATE TEST - 3 Products")
    print("="*70)
    print("\n⚠️  WARNING: This will ACTUALLY update inventory in Shopify!")
    print("Only 3 products will be updated for testing.")
    print("\n" + "="*70 + "\n")

    # Load config
    config_loader = ConfigLoader()
    shopify_config = config_loader.load_shopify_config()
    suppliers_config = config_loader.load_suppliers_config()
    status_mapping = config_loader.get_status_mapping()

    # Connect to Shopify
    print("Step 1: Connecting to Shopify...")
    shopify = ShopifyClient(
        shop_url=shopify_config["shop_url"],
        access_token=shopify_config["access_token"],
        api_version=shopify_config["api_version"]
    )

    if not shopify.test_connection():
        print("✗ Shopify connection failed")
        return False

    # Get Order Nordic products
    print("\nStep 2: Fetching Order Nordic products from Shopify...")
    nordic_variants = shopify.get_product_variants_with_inventory(tags="supplier:order_nordic")
    print(f"✓ Found {len(nordic_variants)} Order Nordic variants")

    # Pick 3 products for testing
    test_variants = {}
    for key, variant in nordic_variants.items():
        if key.startswith("EAN:") and len(test_variants) < 3:
            test_variants[key] = variant

    if len(test_variants) == 0:
        print("✗ No products found")
        return False

    print(f"\nSelected {len(test_variants)} products for testing:")
    for key, variant in test_variants.items():
        print(f"  • {variant.get('barcode')} - {variant.get('title')[:50]}")
        print(f"    Current Shopify stock: {variant.get('inventory_quantity')}")

    # Connect to Order Nordic
    print("\nStep 3: Connecting to Order Nordic...")
    order_nordic_config = None
    for supplier in suppliers_config["suppliers"]:
        if supplier["name"] == "order_nordic":
            order_nordic_config = supplier
            break

    supplier = OrderNordicSupplier(
        name="order_nordic",
        config=order_nordic_config["config"],
        status_mapping=status_mapping,
        headless=True
    )

    if not supplier.authenticate():
        print("✗ Order Nordic authentication failed")
        return False

    print("✓ Authenticated")

    # Search and collect data
    print("\nStep 4: Fetching current stock from Order Nordic...")
    print("-" * 70)

    supplier_products = []
    ean_list = []

    for key, variant in test_variants.items():
        ean = variant.get("barcode")
        ean_list.append(ean)

    # Search all at once
    for i, ean in enumerate(ean_list, 1):
        print(f"[{i}/{len(ean_list)}] Searching {ean}...")
        product = supplier.search_product_by_ean(ean)

        if product:
            supplier_products.append(product)
            print(f"  ✓ Found: {product.get('supplier_data', {}).get('title')}")
            print(f"    Order Nordic stock: {product.get('quantity')}")
        else:
            # Product not found - create entry with 0 quantity
            supplier_products.append({
                "ean": ean,
                "sku": None,
                "quantity": 0,
                "raw_status": "Not found on supplier",
                "supplier_data": {}
            })
            print(f"  ✗ Not found - will set to 0")

    supplier.cleanup()

    print(f"\n✓ Retrieved stock for {len(supplier_products)} products")

    # Match products
    print("\nStep 5: Matching products with Shopify...")
    matcher = InventoryMatcher(test_variants)
    match_results = matcher.match_products_batch(supplier_products)

    matched = match_results["matched"]
    not_found = match_results["not_found"]

    print(f"  Matched: {len(matched)}")
    print(f"  Not found: {len(not_found)}")

    if len(matched) == 0:
        print("✗ No products matched")
        return False

    # Prepare updates
    print("\nStep 6: Preparing updates...")
    updater = InventoryUpdater(
        max_quantity_drop_percent=999,  # Disable safety checks for test
        min_quantity_for_zero_check=999999,
        enable_safety_checks=False
    )

    update_results = updater.process_updates(matched, "order_nordic")
    safe_updates = update_results["safe_updates"]
    no_change = update_results["no_change"]

    print(f"  Updates needed: {len(safe_updates)}")
    print(f"  No change: {len(no_change)}")

    if len(safe_updates) == 0:
        print("\n⚠️  No updates needed - all products already have correct stock")
        print("\nShowing current state:")
        for update in no_change:
            print(f"  • {update.get('ean')} - Quantity: {update.get('new_quantity')} (no change)")
        return True

    # Show what will be updated
    print("\nProducts that will be updated:")
    print("-" * 70)
    for update in safe_updates:
        old_qty = update.get("old_quantity")
        new_qty = update.get("new_quantity")
        change = new_qty - old_qty
        ean = update.get("ean")
        sku = update.get("sku")

        print(f"\nEAN: {ean}")
        print(f"  SKU: {sku}")
        print(f"  Current Shopify: {old_qty}")
        print(f"  Order Nordic: {new_qty}")
        print(f"  Change: {change:+d}")

    # Confirm before updating
    print("\n" + "="*70)
    print("⚠️  READY TO UPDATE SHOPIFY")
    print("="*70)
    print(f"\n{len(safe_updates)} product(s) will be updated.")
    print("\nProceed? (yes/no): ", end="")

    try:
        response = input().strip().lower()
        if response != "yes":
            print("\n❌ Update cancelled by user")
            return False
    except (EOFError, KeyboardInterrupt):
        print("\n❌ Update cancelled")
        return False

    # Perform actual update
    print("\nStep 7: Updating Shopify...")
    print("-" * 70)

    shopify_updates = updater.prepare_shopify_updates(safe_updates)
    result = shopify.batch_update_inventory(
        updates=shopify_updates,
        dry_run=False  # REAL UPDATE!
    )

    print(f"\n✓ Update complete!")
    print(f"  Successful: {result['successful']}")
    print(f"  Failed: {result['failed']}")

    if result['failed'] > 0:
        print("\nErrors:")
        for error in result.get('errors', []):
            print(f"  ✗ {error.get('sku')} - {error.get('error')}")

    # Wait a moment for Shopify to update
    print("\nWaiting 3 seconds for Shopify to process...")
    time.sleep(3)

    # Verify updates
    print("\nStep 8: Verifying updates...")
    print("-" * 70)

    # Re-fetch from Shopify to verify
    nordic_variants_after = shopify.get_product_variants_with_inventory(tags="supplier:order_nordic")

    verification_results = []
    for update in safe_updates:
        ean = update.get("ean")
        expected_qty = update.get("new_quantity")
        ean_key = f"EAN:{ean}"

        if ean_key in nordic_variants_after:
            actual_qty = nordic_variants_after[ean_key].get("inventory_quantity")

            verified = actual_qty == expected_qty
            verification_results.append({
                "ean": ean,
                "expected": expected_qty,
                "actual": actual_qty,
                "verified": verified
            })

            status = "✓" if verified else "✗"
            print(f"{status} {ean}: Expected {expected_qty}, Got {actual_qty}")
        else:
            print(f"✗ {ean}: Not found in Shopify after update")
            verification_results.append({
                "ean": ean,
                "expected": expected_qty,
                "actual": None,
                "verified": False
            })

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    verified_count = sum(1 for r in verification_results if r["verified"])
    total_count = len(verification_results)

    print(f"\nUpdates verified: {verified_count}/{total_count}")

    if verified_count == total_count:
        print("\n✅ ALL UPDATES VERIFIED SUCCESSFULLY!")
        print("\nThe complete flow works:")
        print("  1. ✓ Fetched products from Shopify")
        print("  2. ✓ Searched Order Nordic")
        print("  3. ✓ Matched products correctly")
        print("  4. ✓ Updated Shopify successfully")
        print("  5. ✓ Verified updates are correct")
        print("\n🎉 System is working perfectly!")
        return True
    else:
        print(f"\n⚠️  {total_count - verified_count} updates could not be verified")
        print("\nFailed verifications:")
        for r in verification_results:
            if not r["verified"]:
                print(f"  • {r['ean']}: Expected {r['expected']}, Got {r['actual']}")
        return False


if __name__ == "__main__":
    success = test_real_update()
    sys.exit(0 if success else 1)
