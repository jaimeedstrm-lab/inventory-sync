"""Restore inventory to original values if test goes wrong.

This script allows you to manually restore inventory for specific products.
"""
import sys
from utils.config_loader import ConfigLoader
from core.shopify_client import ShopifyClient


def restore_inventory():
    """Manually restore inventory for products."""
    print("="*70)
    print("INVENTORY RESTORE TOOL")
    print("="*70)
    print("\nThis tool lets you manually set inventory for specific products.")
    print()

    # Load config
    config_loader = ConfigLoader()
    shopify_config = config_loader.load_shopify_config()

    # Connect to Shopify
    shopify = ShopifyClient(
        shop_url=shopify_config["shop_url"],
        access_token=shopify_config["access_token"],
        api_version=shopify_config["api_version"]
    )

    if not shopify.test_connection():
        print("✗ Shopify connection failed")
        return

    print("✓ Connected to Shopify\n")

    # Get location
    location_id = shopify.get_primary_location_id()
    if not location_id:
        print("✗ No location found")
        return

    print(f"Using location ID: {location_id}\n")

    # Interactive mode
    while True:
        print("-" * 70)
        print("Enter product EAN (or 'quit' to exit):")
        try:
            ean = input("> ").strip()

            if ean.lower() in ['quit', 'exit', 'q']:
                break

            if not ean:
                continue

            # Find product
            ean_key = f"EAN:{ean}"
            all_variants = shopify.get_product_variants_with_inventory()

            if ean_key not in all_variants:
                print(f"✗ Product with EAN {ean} not found in Shopify")
                continue

            variant = all_variants[ean_key]
            current_qty = variant.get("inventory_quantity", 0)

            print(f"\nFound: {variant.get('title')}")
            print(f"Current quantity: {current_qty}")
            print(f"\nEnter new quantity:")

            new_qty = input("> ").strip()

            if not new_qty.isdigit():
                print("✗ Invalid quantity")
                continue

            new_qty = int(new_qty)

            print(f"\nWill update {ean} from {current_qty} to {new_qty}")
            print("Confirm? (yes/no):")

            confirm = input("> ").strip().lower()

            if confirm == "yes":
                # Update
                shopify.update_inventory_level(
                    inventory_item_id=variant.get("inventory_item_id"),
                    location_id=location_id,
                    available=new_qty
                )
                print(f"✓ Updated successfully!")
            else:
                print("Cancelled")

        except (EOFError, KeyboardInterrupt):
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"✗ Error: {e}")

    print("\nDone!")


if __name__ == "__main__":
    restore_inventory()
