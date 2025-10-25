"""Mini sync test with just 5 products for quick verification."""
import sys
from utils.config_loader import ConfigLoader
from core.shopify_client import ShopifyClient
from suppliers.order_nordic import OrderNordicSupplier


def test_mini_sync():
    """Test sync with just 5 products."""
    print("="*70)
    print("MINI SYNC TEST - 5 Products from Order Nordic")
    print("="*70)
    print("\nThis will:")
    print("1. Fetch 5 products from Shopify (tagged with Order Nordic)")
    print("2. Search for them on Order Nordic")
    print("3. Show what WOULD be updated (DRY RUN - no actual changes)")
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
        return

    # Get Order Nordic products from Shopify
    print("\nStep 2: Fetching Order Nordic products from Shopify...")
    nordic_variants = shopify.get_product_variants_with_inventory(tags="supplier:order_nordic")

    print(f"✓ Found {len(nordic_variants)} total Order Nordic variants")

    # Get first 5 with EAN
    test_products = []
    for key, variant in nordic_variants.items():
        if key.startswith("EAN:") and len(test_products) < 5:
            test_products.append({
                "ean": variant.get("barcode"),
                "title": variant.get("title"),
                "current_quantity": variant.get("inventory_quantity"),
                "variant_id": variant.get("variant_id"),
                "product_id": variant.get("product_id")
            })

    if len(test_products) == 0:
        print("✗ No products with EAN found")
        return

    print(f"\nTesting with {len(test_products)} products:")
    for i, p in enumerate(test_products, 1):
        print(f"  {i}. {p['ean']} - {p['title'][:50]}")
        print(f"     Current Shopify stock: {p['current_quantity']}")

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
        return

    print("✓ Authenticated with Order Nordic")

    # Search for products
    print("\nStep 4: Searching for products on Order Nordic...")
    print("-" * 70)

    results = []
    for i, product in enumerate(test_products, 1):
        ean = product["ean"]
        print(f"\n[{i}/{len(test_products)}] Searching for {ean}...")

        on_product = supplier.search_product_by_ean(ean)

        if on_product:
            new_qty = on_product.get("quantity")
            old_qty = product["current_quantity"]
            status = on_product.get("raw_status")

            print(f"  ✓ Found on Order Nordic")
            print(f"    Title: {on_product.get('supplier_data', {}).get('title')}")
            print(f"    Status: {status}")
            print(f"    Order Nordic stock: {new_qty}")
            print(f"    Shopify current: {old_qty}")

            if new_qty != old_qty:
                change = new_qty - old_qty
                print(f"    >>> WOULD UPDATE: {old_qty} → {new_qty} (change: {change:+d})")
            else:
                print(f"    >>> NO CHANGE NEEDED")

            results.append({
                "ean": ean,
                "title": product["title"],
                "found": True,
                "old_qty": old_qty,
                "new_qty": new_qty,
                "would_update": new_qty != old_qty
            })
        else:
            print(f"  ✗ NOT found on Order Nordic")
            print(f"    >>> WOULD SET TO 0 (product not available)")

            results.append({
                "ean": ean,
                "title": product["title"],
                "found": False,
                "old_qty": product["current_quantity"],
                "new_qty": 0,
                "would_update": product["current_quantity"] != 0
            })

    # Cleanup
    supplier.cleanup()

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    found_count = sum(1 for r in results if r["found"])
    not_found_count = sum(1 for r in results if not r["found"])
    would_update_count = sum(1 for r in results if r["would_update"])

    print(f"\nProducts tested: {len(results)}")
    print(f"  Found on Order Nordic: {found_count}")
    print(f"  Not found: {not_found_count}")
    print(f"  Would update in Shopify: {would_update_count}")
    print(f"  No change needed: {len(results) - would_update_count}")

    if would_update_count > 0:
        print(f"\nProducts that WOULD be updated:")
        for r in results:
            if r["would_update"]:
                status = "FOUND" if r["found"] else "NOT FOUND"
                print(f"  • {r['ean']}: {r['old_qty']} → {r['new_qty']} ({status})")

    print("\n" + "="*70)
    print("NOTE: This was a DRY RUN - NO changes were made to Shopify!")
    print("="*70)

    print("\n✅ Mini sync test complete!")
    print("\nIf everything looks correct, you can run:")
    print("  python3 main.py --supplier order_nordic --dry-run")
    print("\nFor a full test with all products (will take longer)")


if __name__ == "__main__":
    test_mini_sync()
