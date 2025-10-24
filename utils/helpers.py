"""Helper functions for inventory sync system."""
import re
from typing import Union, Optional, Dict


def normalize_status(
    raw_status: Union[str, int, float],
    status_mapping: Dict[str, int]
) -> int:
    """Normalize inventory status to quantity.

    Args:
        raw_status: Raw status value (string like "In Stock" or numeric quantity)
        status_mapping: Dictionary mapping status strings to quantities

    Returns:
        Normalized quantity as integer

    Examples:
        >>> normalize_status("In Stock", {"in stock": 15})
        15
        >>> normalize_status("På lager", {"på lager": 15})
        15
        >>> normalize_status(25, {})
        25
        >>> normalize_status("5", {})
        5
    """
    # If already numeric, return as integer
    if isinstance(raw_status, (int, float)):
        return int(raw_status)

    # Try to parse as number first
    try:
        return int(float(raw_status))
    except (ValueError, TypeError):
        pass

    # Convert to lowercase for case-insensitive matching
    status_str = str(raw_status).strip().lower()

    # Try exact match in mapping
    if status_str in status_mapping:
        return status_mapping[status_str]

    # Try to extract number from string (e.g., "5 items in stock" -> 5)
    number_match = re.search(r'(\d+)', status_str)
    if number_match:
        return int(number_match.group(1))

    # Default fallback based on common patterns
    if any(keyword in status_str for keyword in ['out', 'slut', 'ikke', 'ej']):
        return 0
    elif any(keyword in status_str for keyword in ['low', 'lite', 'låg', 'få']):
        return 3
    elif any(keyword in status_str for keyword in ['in stock', 'lager', 'available', 'tillgänglig']):
        return 15

    # If nothing matches, assume out of stock for safety
    return 0


def normalize_ean(ean: Optional[str]) -> Optional[str]:
    """Normalize EAN/barcode by removing spaces and dashes.

    Args:
        ean: Raw EAN string

    Returns:
        Normalized EAN string or None if invalid

    Examples:
        >>> normalize_ean("590-1234-567890")
        "5901234567890"
        >>> normalize_ean("590 1234 567890")
        "5901234567890"
        >>> normalize_ean(None)
        None
    """
    if not ean:
        return None

    # Remove spaces, dashes, and other common separators
    normalized = re.sub(r'[\s\-_]', '', str(ean).strip())

    # Validate it's all digits and has reasonable length (8-14 digits for EAN)
    if normalized.isdigit() and 8 <= len(normalized) <= 14:
        return normalized

    return None


def normalize_sku(sku: Optional[str]) -> Optional[str]:
    """Normalize SKU by trimming whitespace and converting to uppercase.

    Args:
        sku: Raw SKU string

    Returns:
        Normalized SKU string or None if invalid

    Examples:
        >>> normalize_sku("  abc-123  ")
        "ABC-123"
        >>> normalize_sku(None)
        None
    """
    if not sku:
        return None

    normalized = str(sku).strip().upper()
    return normalized if normalized else None


def calculate_quantity_drop_percent(old_qty: int, new_qty: int) -> float:
    """Calculate percentage drop in quantity.

    Args:
        old_qty: Previous quantity
        new_qty: New quantity

    Returns:
        Percentage drop (0-100). Returns 0 if quantity increased.

    Examples:
        >>> calculate_quantity_drop_percent(100, 20)
        80.0
        >>> calculate_quantity_drop_percent(50, 50)
        0.0
        >>> calculate_quantity_drop_percent(10, 20)
        0.0
    """
    if old_qty <= 0:
        return 0.0

    if new_qty >= old_qty:
        return 0.0

    drop = old_qty - new_qty
    return (drop / old_qty) * 100


def format_product_identifier(ean: Optional[str] = None, sku: Optional[str] = None) -> str:
    """Format product identifier for display.

    Args:
        ean: Product EAN
        sku: Product SKU

    Returns:
        Formatted identifier string

    Examples:
        >>> format_product_identifier(ean="5901234567890", sku="ABC-123")
        "EAN: 5901234567890 / SKU: ABC-123"
        >>> format_product_identifier(sku="ABC-123")
        "SKU: ABC-123"
    """
    parts = []
    if ean:
        parts.append(f"EAN: {ean}")
    if sku:
        parts.append(f"SKU: {sku}")

    return " / ".join(parts) if parts else "No identifier"


def sanitize_supplier_name(name: str) -> str:
    """Sanitize supplier name for use in filenames and IDs.

    Args:
        name: Raw supplier name

    Returns:
        Sanitized name (lowercase, alphanumeric with underscores)

    Examples:
        >>> sanitize_supplier_name("Oase Outdoors")
        "oase_outdoors"
        >>> sanitize_supplier_name("Supplier-1 (API)")
        "supplier_1_api"
    """
    # Convert to lowercase and replace spaces/special chars with underscores
    sanitized = re.sub(r'[^a-z0-9]+', '_', name.lower())
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    return sanitized
