"""Tests for inventory matcher."""
import pytest
from core.inventory_matcher import InventoryMatcher


class TestInventoryMatcher:
    """Tests for InventoryMatcher class."""

    @pytest.fixture
    def sample_shopify_variants(self):
        """Sample Shopify variants for testing."""
        return {
            "EAN:1234567890123": {
                "product_id": 1,
                "variant_id": 10,
                "inventory_item_id": 100,
                "sku": "SKU-001",
                "barcode": "1234567890123",
                "title": "Product A - Variant 1",
                "inventory_quantity": 10
            },
            "SKU:SKU-001": {
                "product_id": 1,
                "variant_id": 10,
                "inventory_item_id": 100,
                "sku": "SKU-001",
                "barcode": "1234567890123",
                "title": "Product A - Variant 1",
                "inventory_quantity": 10
            },
            "EAN:9876543210987": {
                "product_id": 2,
                "variant_id": 20,
                "inventory_item_id": 200,
                "sku": "SKU-002",
                "barcode": "9876543210987",
                "title": "Product B - Variant 1",
                "inventory_quantity": 5
            },
            "SKU:SKU-002": {
                "product_id": 2,
                "variant_id": 20,
                "inventory_item_id": 200,
                "sku": "SKU-002",
                "barcode": "9876543210987",
                "title": "Product B - Variant 1",
                "inventory_quantity": 5
            },
            "SKU:SKU-003": {
                "product_id": 3,
                "variant_id": 30,
                "inventory_item_id": 300,
                "sku": "SKU-003",
                "barcode": None,
                "title": "Product C - No EAN",
                "inventory_quantity": 15
            }
        }

    @pytest.fixture
    def matcher(self, sample_shopify_variants):
        """Create matcher instance."""
        return InventoryMatcher(sample_shopify_variants)

    def test_match_by_ean(self, matcher):
        """Test matching by EAN."""
        variant, match_type, error = matcher.match_product(
            ean="1234567890123",
            sku="DIFFERENT-SKU"
        )
        assert match_type == "ean"
        assert variant is not None
        assert variant["variant_id"] == 10
        assert error is None

    def test_match_by_sku_fallback(self, matcher):
        """Test fallback to SKU when EAN not found."""
        variant, match_type, error = matcher.match_product(
            ean="9999999999999",  # Non-existent EAN
            sku="SKU-002"
        )
        assert match_type == "sku"
        assert variant is not None
        assert variant["variant_id"] == 20
        assert error is None

    def test_match_by_sku_only(self, matcher):
        """Test matching by SKU when no EAN provided."""
        variant, match_type, error = matcher.match_product(
            ean=None,
            sku="SKU-003"
        )
        assert match_type == "sku"
        assert variant is not None
        assert variant["variant_id"] == 30
        assert error is None

    def test_match_not_found(self, matcher):
        """Test no match found."""
        variant, match_type, error = matcher.match_product(
            ean="9999999999999",
            sku="NONEXISTENT"
        )
        assert match_type == "not_found"
        assert variant is None
        assert error is not None

    def test_match_normalize_ean(self, matcher):
        """Test EAN normalization during matching."""
        variant, match_type, error = matcher.match_product(
            ean="123-456-789-0123",  # With dashes
            sku=None
        )
        assert match_type == "ean"
        assert variant is not None

    def test_match_normalize_sku(self, matcher):
        """Test SKU normalization during matching."""
        variant, match_type, error = matcher.match_product(
            ean=None,
            sku="  sku-001  "  # With spaces and lowercase
        )
        assert match_type == "sku"
        assert variant is not None

    def test_batch_matching(self, matcher):
        """Test batch matching."""
        supplier_products = [
            {"ean": "1234567890123", "sku": "SKU-001", "quantity": 15},
            {"ean": "9876543210987", "sku": "SKU-002", "quantity": 10},
            {"ean": None, "sku": "SKU-003", "quantity": 20},
            {"ean": "9999999999999", "sku": "NOTFOUND", "quantity": 5}
        ]

        results = matcher.match_products_batch(supplier_products)

        assert len(results["matched"]) == 3
        assert len(results["not_found"]) == 1
        assert len(results["duplicates"]) == 0

    def test_get_stats(self, matcher):
        """Test statistics calculation."""
        stats = matcher.get_stats()

        assert stats["total_variant_identifiers"] == 5
        assert stats["products_with_ean"] == 2
        assert stats["products_with_sku"] == 3


class TestInventoryMatcherDuplicates:
    """Tests for duplicate detection."""

    @pytest.fixture
    def duplicate_shopify_variants(self):
        """Shopify variants with duplicates."""
        return {
            "EAN:1234567890123": {
                "product_id": 1,
                "variant_id": 10,
                "inventory_item_id": 100,
                "sku": "SKU-001",
                "barcode": "1234567890123",
                "title": "Product A",
                "inventory_quantity": 10
            },
            "SKU:SKU-001": {
                "product_id": 1,
                "variant_id": 10,
                "inventory_item_id": 100,
                "sku": "SKU-001",
                "barcode": "1234567890123",
                "title": "Product A",
                "inventory_quantity": 10
            },
            "SKU:DUPLICATE-SKU": {
                "product_id": 2,
                "variant_id": 20,
                "inventory_item_id": 200,
                "sku": "DUPLICATE-SKU",
                "barcode": None,
                "title": "Product B",
                "inventory_quantity": 5
            }
        }

    @pytest.fixture
    def matcher_with_duplicates(self, duplicate_shopify_variants):
        """Create matcher with duplicate data."""
        # Manually create duplicates by adding to lookup
        matcher = InventoryMatcher(duplicate_shopify_variants)

        # Add duplicate SKU
        duplicate_variant = {
            "product_id": 3,
            "variant_id": 30,
            "inventory_item_id": 300,
            "sku": "DUPLICATE-SKU",
            "barcode": None,
            "title": "Product C (Duplicate SKU)",
            "inventory_quantity": 8
        }
        matcher.sku_lookup["DUPLICATE-SKU"].append(duplicate_variant)

        return matcher

    def test_detect_duplicate_sku(self, matcher_with_duplicates):
        """Test duplicate SKU detection."""
        duplicates = matcher_with_duplicates.get_duplicate_identifiers()

        sku_duplicates = [d for d in duplicates if d["type"] == "SKU"]
        assert len(sku_duplicates) >= 1

        duplicate = sku_duplicates[0]
        assert duplicate["identifier"] == "DUPLICATE-SKU"
        assert duplicate["count"] == 2

    def test_match_returns_duplicate_status(self, matcher_with_duplicates):
        """Test that matching returns duplicate status."""
        variant, match_type, error = matcher_with_duplicates.match_product(
            ean=None,
            sku="DUPLICATE-SKU"
        )

        assert match_type == "duplicate"
        assert variant is None
        assert "Multiple products" in error
