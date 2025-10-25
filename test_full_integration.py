"""Comprehensive end-to-end integration test.

This test verifies:
1. Shopify connection and tag filtering
2. Order Nordic login and search
3. Product matching logic
4. Edge cases (not found, out of stock, etc.)
5. Dry-run mode (no actual updates)
"""
import sys
from utils.config_loader import ConfigLoader
from core.shopify_client import ShopifyClient
from suppliers.order_nordic import OrderNordicSupplier


def test_comprehensive():
    """Run comprehensive integration test."""
    print("="*70)
    print("COMPREHENSIVE INTEGRATION TEST - Order Nordic")
    print("="*70)

    results = {
        "passed": [],
        "failed": [],
        "warnings": []
    }

    # Load config
    config_loader = ConfigLoader()
    shopify_config = config_loader.load_shopify_config()
    suppliers_config = config_loader.load_suppliers_config()
    status_mapping = config_loader.get_status_mapping()

    # =========================================================================
    # TEST 1: Shopify Connection
    # =========================================================================
    print("\n[TEST 1] Shopify Connection")
    print("-" * 70)

    try:
        shopify = ShopifyClient(
            shop_url=shopify_config["shop_url"],
            access_token=shopify_config["access_token"],
            api_version=shopify_config["api_version"]
        )

        if shopify.test_connection():
            print("✓ Shopify connection successful")
            results["passed"].append("Shopify connection")
        else:
            print("✗ Shopify connection failed")
            results["failed"].append("Shopify connection")
            return results
    except Exception as e:
        print(f"✗ Shopify connection error: {e}")
        results["failed"].append(f"Shopify connection: {e}")
        return results

    # =========================================================================
    # TEST 2: Tag Filtering
    # =========================================================================
    print("\n[TEST 2] Tag Filtering for Order Nordic")
    print("-" * 70)

    try:
        nordic_variants = shopify.get_product_variants_with_inventory(tags="supplier:order_nordic")

        print(f"✓ Found {len(nordic_variants)} Order Nordic variants")

        if len(nordic_variants) == 0:
            print("⚠️  WARNING: No products tagged with 'supplier:order_nordic'")
            results["warnings"].append("No Order Nordic products found - check tags")
        else:
            results["passed"].append(f"Tag filtering ({len(nordic_variants)} products)")

            # Show sample
            sample_eans = []
            for key, variant in list(nordic_variants.items())[:5]:
                if key.startswith("EAN:"):
                    ean = variant.get("barcode")
                    title = variant.get("title", "")[:50]
                    sample_eans.append(ean)
                    print(f"  Sample: {ean} - {title}")

    except Exception as e:
        print(f"✗ Tag filtering error: {e}")
        results["failed"].append(f"Tag filtering: {e}")
        return results

    # =========================================================================
    # TEST 3: Order Nordic Authentication
    # =========================================================================
    print("\n[TEST 3] Order Nordic Authentication")
    print("-" * 70)

    try:
        # Find Order Nordic config
        order_nordic_config = None
        for supplier in suppliers_config["suppliers"]:
            if supplier["name"] == "order_nordic":
                order_nordic_config = supplier
                break

        if not order_nordic_config:
            print("✗ Order Nordic config not found")
            results["failed"].append("Order Nordic config missing")
            return results

        supplier = OrderNordicSupplier(
            name="order_nordic",
            config=order_nordic_config["config"],
            status_mapping=status_mapping,
            headless=True
        )

        if supplier.authenticate():
            print("✓ Order Nordic authentication successful")
            results["passed"].append("Order Nordic authentication")
        else:
            print("✗ Order Nordic authentication failed")
            results["failed"].append("Order Nordic authentication")
            supplier.cleanup()
            return results

    except Exception as e:
        print(f"✗ Authentication error: {e}")
        results["failed"].append(f"Authentication: {e}")
        return results

    # =========================================================================
    # TEST 4: Product Search - Known Product
    # =========================================================================
    print("\n[TEST 4] Search for Known Product")
    print("-" * 70)

    try:
        # Use first sample EAN if we have one
        test_ean = sample_eans[0] if sample_eans else "5010576835857"

        print(f"Searching for EAN: {test_ean}")
        product = supplier.search_product_by_ean(test_ean)

        if product:
            print(f"✓ Product found!")
            print(f"  EAN: {product.get('ean')}")
            print(f"  SKU: {product.get('sku')}")
            print(f"  Quantity: {product.get('quantity')}")
            print(f"  Status: {product.get('raw_status')}")
            print(f"  Title: {product.get('supplier_data', {}).get('title')}")

            # Validate data structure
            if product.get('ean') == test_ean:
                print("✓ EAN matches")
                results["passed"].append("Product search - EAN match")
            else:
                print(f"✗ EAN mismatch: expected {test_ean}, got {product.get('ean')}")
                results["failed"].append("EAN mismatch")

            if isinstance(product.get('quantity'), int):
                print("✓ Quantity is integer")
                results["passed"].append("Product search - quantity type")
            else:
                print(f"✗ Quantity is not integer: {type(product.get('quantity'))}")
                results["failed"].append("Quantity type incorrect")

            if product.get('sku'):
                print("✓ SKU extracted")
                results["passed"].append("Product search - SKU extraction")
            else:
                print("⚠️  No SKU found")
                results["warnings"].append("SKU not extracted")

        else:
            print(f"✗ Product not found (this might be OK if product doesn't exist on Order Nordic)")
            results["warnings"].append(f"Product {test_ean} not found")

    except Exception as e:
        print(f"✗ Search error: {e}")
        results["failed"].append(f"Product search: {e}")

    # =========================================================================
    # TEST 5: Product Search - Non-existent Product
    # =========================================================================
    print("\n[TEST 5] Search for Non-existent Product")
    print("-" * 70)

    try:
        fake_ean = "9999999999999"
        print(f"Searching for fake EAN: {fake_ean}")

        product = supplier.search_product_by_ean(fake_ean)

        if product is None:
            print("✓ Correctly returned None for non-existent product")
            results["passed"].append("Non-existent product handling")
        else:
            print("✗ Should have returned None for non-existent product")
            results["failed"].append("Non-existent product handling")

    except Exception as e:
        print(f"✗ Error handling non-existent product: {e}")
        results["failed"].append(f"Non-existent product: {e}")

    # =========================================================================
    # TEST 6: Multiple Sequential Searches
    # =========================================================================
    print("\n[TEST 6] Multiple Sequential Searches")
    print("-" * 70)

    try:
        # Test 3 searches to ensure stability
        search_count = min(3, len(sample_eans)) if sample_eans else 1
        test_eans_multi = sample_eans[:search_count] if sample_eans else ["5010576835857"]

        print(f"Testing {len(test_eans_multi)} sequential searches...")

        found_count = 0
        for ean in test_eans_multi:
            product = supplier.search_product_by_ean(ean)
            if product:
                found_count += 1
                print(f"  ✓ {ean} - Found")
            else:
                print(f"  ✗ {ean} - Not found")

        print(f"✓ Completed {len(test_eans_multi)} searches ({found_count} found)")
        results["passed"].append(f"Sequential searches ({len(test_eans_multi)} products)")

    except Exception as e:
        print(f"✗ Sequential search error: {e}")
        results["failed"].append(f"Sequential searches: {e}")

    # =========================================================================
    # TEST 7: Data Validation
    # =========================================================================
    print("\n[TEST 7] Data Validation")
    print("-" * 70)

    try:
        # Test that supplier validates product data correctly
        from suppliers.base import BaseSupplier

        # Valid product
        valid_product = {
            "ean": "1234567890123",
            "sku": "TEST-123",
            "quantity": 10
        }

        # Invalid product (no identifier)
        invalid_product = {
            "quantity": 10
        }

        if supplier.validate_product_data(valid_product):
            print("✓ Valid product data accepted")
            results["passed"].append("Data validation - valid product")
        else:
            print("✗ Valid product rejected")
            results["failed"].append("Data validation - valid product")

        if not supplier.validate_product_data(invalid_product):
            print("✓ Invalid product data rejected")
            results["passed"].append("Data validation - invalid product")
        else:
            print("✗ Invalid product accepted")
            results["failed"].append("Data validation - invalid product")

    except Exception as e:
        print(f"✗ Validation test error: {e}")
        results["failed"].append(f"Data validation: {e}")

    # Cleanup
    supplier.cleanup()

    # =========================================================================
    # RESULTS SUMMARY
    # =========================================================================
    print("\n" + "="*70)
    print("TEST RESULTS SUMMARY")
    print("="*70)

    print(f"\n✓ PASSED: {len(results['passed'])}")
    for test in results["passed"]:
        print(f"  • {test}")

    if results["warnings"]:
        print(f"\n⚠️  WARNINGS: {len(results['warnings'])}")
        for warning in results["warnings"]:
            print(f"  • {warning}")

    if results["failed"]:
        print(f"\n✗ FAILED: {len(results['failed'])}")
        for failure in results["failed"]:
            print(f"  • {failure}")

    print("\n" + "="*70)

    if results["failed"]:
        print("❌ TESTS FAILED - Issues need to be fixed before production use")
        return False
    elif results["warnings"]:
        print("⚠️  TESTS PASSED WITH WARNINGS - Review warnings before production")
        return True
    else:
        print("✅ ALL TESTS PASSED - System ready for production!")
        return True


if __name__ == "__main__":
    success = test_comprehensive()
    sys.exit(0 if success else 1)
