"""Tests for helper functions."""
import pytest
from utils.helpers import (
    normalize_status,
    normalize_ean,
    normalize_sku,
    calculate_quantity_drop_percent,
    format_product_identifier,
    sanitize_supplier_name
)


class TestNormalizeStatus:
    """Tests for normalize_status function."""

    def test_numeric_int(self):
        """Test with integer input."""
        assert normalize_status(10, {}) == 10
        assert normalize_status(0, {}) == 0

    def test_numeric_float(self):
        """Test with float input."""
        assert normalize_status(10.5, {}) == 10
        assert normalize_status(10.9, {}) == 10

    def test_numeric_string(self):
        """Test with numeric string."""
        assert normalize_status("25", {}) == 25
        assert normalize_status("10.5", {}) == 10

    def test_status_mapping_exact(self):
        """Test exact status mapping."""
        mapping = {
            "in stock": 15,
            "out of stock": 0,
            "low stock": 3
        }
        assert normalize_status("In Stock", mapping) == 15
        assert normalize_status("OUT OF STOCK", mapping) == 0
        assert normalize_status("Low Stock", mapping) == 3

    def test_status_mapping_norwegian(self):
        """Test Norwegian status strings."""
        mapping = {
            "på lager": 15,
            "ikke på lager": 0,
            "lite på lager": 3
        }
        assert normalize_status("På lager", mapping) == 15
        assert normalize_status("Ikke på lager", mapping) == 0

    def test_number_extraction_from_string(self):
        """Test extracting number from text."""
        assert normalize_status("5 items in stock", {}) == 5
        assert normalize_status("Stock: 42", {}) == 42

    def test_default_fallback_out_of_stock(self):
        """Test default fallback for out of stock keywords."""
        assert normalize_status("out", {}) == 0
        assert normalize_status("slut", {}) == 0
        assert normalize_status("ikke", {}) == 0

    def test_default_fallback_low_stock(self):
        """Test default fallback for low stock keywords."""
        assert normalize_status("low available", {}) == 3
        assert normalize_status("lite", {}) == 3

    def test_default_fallback_in_stock(self):
        """Test default fallback for in stock keywords."""
        assert normalize_status("in stock now", {}) == 15
        assert normalize_status("available", {}) == 15


class TestNormalizeEan:
    """Tests for normalize_ean function."""

    def test_valid_ean(self):
        """Test valid EAN."""
        assert normalize_ean("5901234567890") == "5901234567890"

    def test_ean_with_spaces(self):
        """Test EAN with spaces."""
        assert normalize_ean("590 1234 567890") == "5901234567890"

    def test_ean_with_dashes(self):
        """Test EAN with dashes."""
        assert normalize_ean("590-1234-567890") == "5901234567890"

    def test_ean_with_mixed_separators(self):
        """Test EAN with various separators."""
        assert normalize_ean("590-1234 567_890") == "5901234567890"

    def test_ean8(self):
        """Test 8-digit EAN."""
        assert normalize_ean("12345678") == "12345678"

    def test_ean13(self):
        """Test 13-digit EAN."""
        assert normalize_ean("1234567890123") == "1234567890123"

    def test_invalid_ean_too_short(self):
        """Test invalid EAN (too short)."""
        assert normalize_ean("1234567") is None

    def test_invalid_ean_too_long(self):
        """Test invalid EAN (too long)."""
        assert normalize_ean("123456789012345") is None

    def test_invalid_ean_non_numeric(self):
        """Test invalid EAN with letters."""
        assert normalize_ean("ABC123456789") is None

    def test_none_ean(self):
        """Test None input."""
        assert normalize_ean(None) is None

    def test_empty_ean(self):
        """Test empty string."""
        assert normalize_ean("") is None


class TestNormalizeSku:
    """Tests for normalize_sku function."""

    def test_valid_sku(self):
        """Test valid SKU."""
        assert normalize_sku("ABC-123") == "ABC-123"

    def test_sku_with_spaces(self):
        """Test SKU with leading/trailing spaces."""
        assert normalize_sku("  ABC-123  ") == "ABC-123"

    def test_lowercase_sku(self):
        """Test lowercase SKU gets uppercased."""
        assert normalize_sku("abc-123") == "ABC-123"

    def test_mixed_case_sku(self):
        """Test mixed case SKU."""
        assert normalize_sku("AbC-123") == "ABC-123"

    def test_none_sku(self):
        """Test None input."""
        assert normalize_sku(None) is None

    def test_empty_sku(self):
        """Test empty string."""
        assert normalize_sku("") is None


class TestCalculateQuantityDropPercent:
    """Tests for calculate_quantity_drop_percent function."""

    def test_80_percent_drop(self):
        """Test 80% drop."""
        assert calculate_quantity_drop_percent(100, 20) == 80.0

    def test_50_percent_drop(self):
        """Test 50% drop."""
        assert calculate_quantity_drop_percent(100, 50) == 50.0

    def test_100_percent_drop(self):
        """Test 100% drop."""
        assert calculate_quantity_drop_percent(100, 0) == 100.0

    def test_no_drop(self):
        """Test no change."""
        assert calculate_quantity_drop_percent(50, 50) == 0.0

    def test_quantity_increase(self):
        """Test quantity increase returns 0."""
        assert calculate_quantity_drop_percent(10, 20) == 0.0

    def test_zero_old_quantity(self):
        """Test with zero old quantity."""
        assert calculate_quantity_drop_percent(0, 10) == 0.0


class TestFormatProductIdentifier:
    """Tests for format_product_identifier function."""

    def test_both_ean_and_sku(self):
        """Test with both EAN and SKU."""
        result = format_product_identifier(ean="5901234567890", sku="ABC-123")
        assert result == "EAN: 5901234567890 / SKU: ABC-123"

    def test_ean_only(self):
        """Test with only EAN."""
        result = format_product_identifier(ean="5901234567890")
        assert result == "EAN: 5901234567890"

    def test_sku_only(self):
        """Test with only SKU."""
        result = format_product_identifier(sku="ABC-123")
        assert result == "SKU: ABC-123"

    def test_no_identifiers(self):
        """Test with no identifiers."""
        result = format_product_identifier()
        assert result == "No identifier"


class TestSanitizeSupplierName:
    """Tests for sanitize_supplier_name function."""

    def test_simple_name(self):
        """Test simple name."""
        assert sanitize_supplier_name("Supplier1") == "supplier1"

    def test_name_with_spaces(self):
        """Test name with spaces."""
        assert sanitize_supplier_name("Oase Outdoors") == "oase_outdoors"

    def test_name_with_special_chars(self):
        """Test name with special characters."""
        assert sanitize_supplier_name("Supplier-1 (API)") == "supplier_1_api"

    def test_name_with_multiple_spaces(self):
        """Test name with multiple consecutive spaces."""
        assert sanitize_supplier_name("Supplier   Name") == "supplier_name"

    def test_name_with_leading_trailing_special(self):
        """Test name with leading/trailing special chars."""
        assert sanitize_supplier_name("--Supplier--") == "supplier"
