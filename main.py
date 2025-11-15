"""Main entry point for inventory sync system."""
import argparse
import sys
from typing import Optional

from utils.config_loader import ConfigLoader
from core.logger import SyncLogger
from core.shopify_client import ShopifyClient
from core.inventory_matcher import InventoryMatcher
from core.inventory_updater import InventoryUpdater
from utils.email_notifier import EmailNotifier
from suppliers.oase_outdoors import OaseOutdoorsSupplier
from suppliers.order_nordic import OrderNordicSupplier
from suppliers.response_nordic import ResponseNordicSupplier
from suppliers.petcare import PetcareSupplier


def get_supplier_instance(supplier_config: dict, status_mapping: dict):
    """Create supplier instance based on configuration.

    Args:
        supplier_config: Supplier configuration dictionary
        status_mapping: Status to quantity mapping

    Returns:
        Supplier instance

    Raises:
        ValueError: If supplier type is unknown
    """
    supplier_name = supplier_config["name"]
    supplier_type = supplier_config["type"]
    config = supplier_config["config"]

    if supplier_name == "oase_outdoors":
        return OaseOutdoorsSupplier(supplier_name, config, status_mapping)
    elif supplier_name == "order_nordic":
        return OrderNordicSupplier(supplier_name, config, status_mapping)
    elif supplier_name == "response_nordic":
        return ResponseNordicSupplier(supplier_name, config, status_mapping)
    elif supplier_name == "petcare":
        return PetcareSupplier(supplier_name, config, status_mapping)
    # Add more suppliers here as they are implemented
    else:
        raise ValueError(f"Unknown supplier: {supplier_name}")


def sync_inventory(
    supplier_filter: Optional[str] = None,
    dry_run: bool = False,
    force: bool = False,
    test_limit: Optional[int] = None,
    test_eans: Optional[list] = None
):
    """Run inventory synchronization.

    Args:
        supplier_filter: Only sync this supplier (optional)
        dry_run: If True, don't update inventory, just preview
        force: If True, bypass safety checks
        test_limit: Limit number of products to sync (for testing)
        test_eans: Specific EANs to test (overrides test_limit)
    """
    # Load configuration
    print("Loading configuration...")
    config_loader = ConfigLoader()

    try:
        shopify_config = config_loader.load_shopify_config()
        suppliers_config = config_loader.load_suppliers_config()
        status_mapping = config_loader.get_status_mapping()
        safety_limits = config_loader.get_safety_limits()

        # Try to load email config (optional)
        try:
            email_config = config_loader.load_email_config()
            email_enabled = bool(email_config.get("smtp_host") and email_config.get("username"))
        except:
            email_config = None
            email_enabled = False

    except Exception as e:
        print(f"✗ Configuration error: {e}")
        sys.exit(1)

    # Initialize logger
    logger = SyncLogger()

    if dry_run:
        print("\n" + "="*60)
        print("DRY RUN MODE - No changes will be made to Shopify")
        print("="*60 + "\n")

    if force:
        print("\n" + "="*60)
        print("FORCE MODE - Safety checks disabled")
        print("="*60 + "\n")
        safety_limits["enable_safety_checks"] = False

    try:
        # Initialize Shopify client
        print("\nConnecting to Shopify...")
        shopify = ShopifyClient(
            shop_url=shopify_config["shop_url"],
            access_token=shopify_config["access_token"],
            api_version=shopify_config["api_version"]
        )

        # Test connection
        if not shopify.test_connection():
            logger.log_error("shopify_connection", "Failed to connect to Shopify")
            raise Exception("Shopify connection failed")

        # Get enabled suppliers
        enabled_suppliers = config_loader.get_enabled_suppliers()

        # Filter by supplier if specified
        if supplier_filter:
            enabled_suppliers = [
                s for s in enabled_suppliers
                if s["name"] == supplier_filter
            ]
            if not enabled_suppliers:
                print(f"✗ Supplier '{supplier_filter}' not found or not enabled")
                sys.exit(1)

        if not enabled_suppliers:
            print("✗ No enabled suppliers found in configuration")
            sys.exit(1)

        print(f"\nProcessing {len(enabled_suppliers)} supplier(s)...")

        # Initialize inventory updater (once for all suppliers)
        updater = InventoryUpdater(
            max_quantity_drop_percent=safety_limits["max_quantity_drop_percent"],
            min_quantity_for_zero_check=safety_limits["min_quantity_for_zero_check"],
            enable_safety_checks=safety_limits["enable_safety_checks"]
        )

        # Process each supplier
        for supplier_config in enabled_suppliers:
            supplier_name = supplier_config["name"]
            logger.log_supplier_start(supplier_name)

            try:
                # Fetch Shopify products filtered by this supplier's tag
                supplier_tag = supplier_config.get("shopify_tag")

                print(f"\nFetching products from Shopify for {supplier_name}...")
                if supplier_tag:
                    print(f"  Filtering by tag: {supplier_tag}")
                    shopify_variants = shopify.get_product_variants_with_inventory(tags=supplier_tag)
                else:
                    print(f"  ⚠️  No shopify_tag configured - fetching ALL products (slower)")
                    shopify_variants = shopify.get_product_variants_with_inventory()

                # Initialize matcher for this supplier
                matcher = InventoryMatcher(shopify_variants)
                stats = matcher.get_stats()
                print(f"✓ Loaded {stats['total_variant_identifiers']} product identifiers from Shopify")
                print(f"  - Products with EAN: {stats['products_with_ean']}")
                print(f"  - Products with SKU: {stats['products_with_sku']}")

                # Check for duplicates in Shopify
                duplicates = matcher.get_duplicate_identifiers()
                if duplicates:
                    print(f"\n⚠️  Found {len(duplicates)} duplicate identifiers in Shopify:")
                    for dup in duplicates:
                        logger.log_duplicate(
                            identifier=dup["identifier"],
                            identifier_type=dup["type"],
                            count=dup["count"],
                            products=dup["products"]
                        )
                        print(f"  - {dup['type']}: {dup['identifier']} ({dup['count']} products)")

                # Get supplier instance
                supplier = get_supplier_instance(supplier_config, status_mapping)

                # Fetch products from supplier
                with supplier:
                    # Special handling for Order Nordic and Response Nordic (EAN search-based)
                    if supplier_name in ["order_nordic", "response_nordic"]:
                        # Extract EANs from Shopify products to search for
                        ean_list = []
                        for key, variant in shopify_variants.items():
                            if key.startswith("EAN:"):
                                ean = variant.get("barcode")
                                if ean:
                                    ean_list.append(ean)

                        # Use specific test EANs if provided, otherwise limit by count
                        if test_eans:
                            # Filter to only test the specified EANs
                            ean_list = [ean for ean in ean_list if ean in test_eans]
                            print(f"  [TEST MODE] Using {len(ean_list)} specific test EANs")
                        elif test_limit:
                            ean_list = ean_list[:test_limit]
                            print(f"  [TEST MODE] Limiting to {len(ean_list)} EANs")

                        print(f"  Found {len(ean_list)} EANs to search for on {supplier_name}")

                        # Authenticate first
                        if not supplier.authenticate():
                            raise Exception(f"Failed to authenticate with {supplier_name}")

                        # Search for products by EAN list
                        supplier_products = supplier.search_products_by_ean_list(ean_list)

                        # Add products not found on supplier with quantity 0
                        # This ensures products that no longer exist on supplier are marked as out of stock
                        found_eans = {p.get("ean") for p in supplier_products if p.get("ean")}
                        not_found_eans = set(ean_list) - found_eans

                        for ean in not_found_eans:
                            supplier_products.append({
                                "ean": ean,
                                "quantity": 0,
                                "title": f"Product not found on {supplier_name}",
                                "sku": None,
                                "status": "not_found_on_supplier"
                            })

                        print(f"  Products found on supplier: {len(found_eans)}")
                        print(f"  Products NOT found (will be set to 0): {len(not_found_eans)}")

                        # Safety check: If NO products found at all, something is wrong - abort sync
                        if len(found_eans) == 0 and len(ean_list) > 0:
                            raise Exception(f"SAFETY CHECK FAILED: Found 0 products out of {len(ean_list)} searched. This indicates a scraping/auth failure, not real stock levels. Aborting sync to prevent setting everything to 0.")

                    elif supplier_name == "petcare":
                        # Special handling for Petcare (SKU search-based with EAN verification)
                        # Extract SKU-EAN pairs from Shopify products
                        sku_ean_pairs = []
                        seen_skus = set()  # Track SKUs to avoid duplicates
                        for key, variant in shopify_variants.items():
                            sku = variant.get("sku")
                            ean = variant.get("barcode")
                            if sku and sku not in seen_skus:  # SKU is required and must be unique
                                sku_ean_pairs.append((sku, ean))
                                seen_skus.add(sku)

                        # Limit for testing if specified
                        if test_limit:
                            sku_ean_pairs = sku_ean_pairs[:test_limit]
                            print(f"  [TEST MODE] Limiting to {len(sku_ean_pairs)} SKU-EAN pairs")

                        print(f"  Found {len(sku_ean_pairs)} SKU-EAN pairs to search for on {supplier_name}")

                        # Authenticate first
                        if not supplier.authenticate():
                            raise Exception(f"Failed to authenticate with {supplier_name}")

                        # Search for products by SKU-EAN pairs
                        supplier_products = supplier.search_products_by_sku_list(sku_ean_pairs)

                        # Add products not found on supplier with quantity 0
                        found_eans = {p.get("ean") for p in supplier_products if p.get("ean")}
                        searched_eans = {ean for sku, ean in sku_ean_pairs if ean}

                        not_found_eans = searched_eans - found_eans

                        for sku, ean in sku_ean_pairs:
                            if ean in not_found_eans:
                                supplier_products.append({
                                    "ean": ean,
                                    "sku": sku,
                                    "quantity": 0,
                                    "title": f"Product not found on {supplier_name}",
                                    "status": "not_found_on_supplier"
                                })

                        print(f"  Products found on supplier: {len(found_eans)}")
                        print(f"  Products NOT found (will be set to 0): {len(not_found_eans)}")

                        # Safety check: If NO products found at all, something is wrong - abort sync
                        if len(found_eans) == 0 and len(sku_ean_pairs) > 0:
                            raise Exception(f"SAFETY CHECK FAILED: Found 0 products out of {len(sku_ean_pairs)} searched. This indicates a scraping/auth failure, not real stock levels. Aborting sync to prevent setting everything to 0.")

                    else:
                        # Regular API-based suppliers
                        supplier_products = supplier.get_products()

                logger.increment_supplier_products(len(supplier_products))

                # Match products
                print(f"Matching products with Shopify catalog...")
                match_results = matcher.match_products_batch(supplier_products)

                matched = match_results["matched"]
                not_found = match_results["not_found"]
                match_duplicates = match_results["duplicates"]

                print(f"✓ Matched: {len(matched)}")
                print(f"  Not found in Shopify: {len(not_found)}")
                print(f"  Duplicates: {len(match_duplicates)}")

                logger.increment_matched_products(len(matched))

                # Log not found products
                for item in not_found:
                    product = item["supplier_product"]
                    logger.log_not_found(
                        ean=product.get("ean"),
                        sku=product.get("sku"),
                        supplier=supplier_name
                    )

                # Log duplicate matches
                for item in match_duplicates:
                    product = item["supplier_product"]
                    logger.log_error(
                        error_type="duplicate_identifier",
                        message=item["error"],
                        context={
                            "ean": product.get("ean"),
                            "sku": product.get("sku"),
                            "supplier": supplier_name
                        }
                    )

                # Process updates (apply safety checks)
                update_results = updater.process_updates(matched, supplier_name)

                safe_updates = update_results["safe_updates"]
                flagged_updates = update_results["flagged_updates"]
                no_change = update_results["no_change"]

                print(f"\nUpdate analysis:")
                print(f"  Safe to update: {len(safe_updates)}")
                print(f"  Flagged for review: {len(flagged_updates)}")
                print(f"  No change needed: {len(no_change)}")

                # Log flagged updates
                for update in flagged_updates:
                    logger.log_flagged(
                        ean=update["ean"],
                        sku=update["sku"],
                        reason=update["flag_reason"],
                        old_qty=update["old_quantity"],
                        new_qty=update["new_quantity"],
                        supplier=supplier_name
                    )

                # Print flagged updates report
                if flagged_updates:
                    print(updater.format_flagged_report(flagged_updates))

                # Update inventory in Shopify
                if safe_updates:
                    shopify_updates = updater.prepare_shopify_updates(safe_updates)
                    result = shopify.batch_update_inventory(
                        updates=shopify_updates,
                        dry_run=dry_run
                    )

                    print(f"\nShopify update results:")
                    print(f"  Successful: {result['successful']}")
                    print(f"  Failed: {result['failed']}")
                    if dry_run:
                        print(f"  Skipped (dry run): {result['skipped']}")

                    # Log updates
                    for update in safe_updates:
                        logger.log_update(
                            ean=update["ean"],
                            sku=update["sku"],
                            supplier=supplier_name,
                            old_qty=update["old_quantity"],
                            new_qty=update["new_quantity"],
                            shopify_product_id=update["product_id"],
                            shopify_variant_id=update["variant_id"]
                        )

                    # Log errors from batch update
                    for error in result.get("errors", []):
                        logger.log_error(
                            error_type="shopify_update",
                            message=error["error"],
                            context={
                                "sku": error["sku"],
                                "ean": error["ean"]
                            }
                        )

                # Log no-change items
                for update in no_change:
                    logger.log_update(
                        ean=update["ean"],
                        sku=update["sku"],
                        supplier=supplier_name,
                        old_qty=update["old_quantity"],
                        new_qty=update["new_quantity"],
                        shopify_product_id=update["product_id"],
                        shopify_variant_id=update["variant_id"]
                    )

            except Exception as e:
                error_msg = f"Failed to process supplier {supplier_name}: {str(e)}"
                print(f"\n✗ {error_msg}")
                logger.log_error(
                    error_type="supplier_processing",
                    message=str(e),
                    context={"supplier": supplier_name}
                )
                continue

        # Print and save summary
        logger.print_summary()
        logger.save()

        # Send email notification if configured
        if email_enabled and email_config:
            try:
                notifier = EmailNotifier(
                    smtp_host=email_config["smtp_host"],
                    smtp_port=email_config["smtp_port"],
                    username=email_config["username"],
                    password=email_config["password"],
                    from_email=email_config["from_email"],
                    to_emails=email_config["to_emails"],
                    send_on_success=email_config.get("send_on_success", False),
                    send_on_warnings=email_config.get("send_on_warnings", True),
                    send_on_errors=email_config.get("send_on_errors", True),
                    subject_prefix=email_config.get("subject_prefix", "[Inventory Sync]")
                )

                notifier.send_sync_report(
                    summary=logger.get_summary(),
                    not_found_products=logger.get_not_found_products(),
                    flagged_products=logger.get_flagged_products(),
                    errors=logger.get_errors(),
                    suppliers_processed=logger.log_data["suppliers_processed"]
                )
            except Exception as e:
                print(f"⚠️  Failed to send email notification: {e}")

        # Exit with appropriate code
        if logger.has_errors():
            sys.exit(1)
        elif logger.has_warnings():
            sys.exit(0)  # Warnings are not fatal
        else:
            sys.exit(0)

    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        logger.log_error("fatal", str(e))
        logger.save()
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Synchronize inventory from suppliers to Shopify",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run sync for all enabled suppliers
  python main.py

  # Run in dry-run mode (preview changes)
  python main.py --dry-run

  # Sync only Oase Outdoors
  python main.py --supplier oase_outdoors

  # Force update (bypass safety checks)
  python main.py --force

  # Dry-run for specific supplier
  python main.py --supplier oase_outdoors --dry-run
        """
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without updating Shopify"
    )

    parser.add_argument(
        "--supplier",
        type=str,
        help="Only sync specific supplier (e.g., 'oase_outdoors')"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass safety checks (use with caution!)"
    )

    parser.add_argument(
        "--test-limit",
        type=int,
        help="Limit number of products to test (for quick verification)"
    )

    parser.add_argument(
        "--test-eans",
        type=str,
        help="Comma-separated list of specific EANs to test"
    )

    args = parser.parse_args()

    # Parse test EANs if provided
    test_eans = None
    if args.test_eans:
        test_eans = [ean.strip() for ean in args.test_eans.split(',')]

    sync_inventory(
        supplier_filter=args.supplier,
        dry_run=args.dry_run,
        force=args.force,
        test_limit=args.test_limit,
        test_eans=test_eans
    )


if __name__ == "__main__":
    main()
