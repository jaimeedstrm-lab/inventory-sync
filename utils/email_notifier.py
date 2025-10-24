"""Email notification system for inventory sync."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
from datetime import datetime


class EmailNotifier:
    """Send email notifications for sync events."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_email: str,
        to_emails: List[str],
        send_on_success: bool = False,
        send_on_warnings: bool = True,
        send_on_errors: bool = True,
        subject_prefix: str = "[Inventory Sync]"
    ):
        """Initialize email notifier.

        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            username: SMTP authentication username
            password: SMTP authentication password
            from_email: Sender email address
            to_emails: List of recipient email addresses
            send_on_success: Whether to send email on successful sync
            send_on_warnings: Whether to send email on warnings
            send_on_errors: Whether to send email on errors
            subject_prefix: Prefix for email subjects
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.to_emails = to_emails
        self.send_on_success = send_on_success
        self.send_on_warnings = send_on_warnings
        self.send_on_errors = send_on_errors
        self.subject_prefix = subject_prefix

    def should_send(self, has_errors: bool, has_warnings: bool) -> bool:
        """Determine if notification should be sent.

        Args:
            has_errors: Whether sync had errors
            has_warnings: Whether sync had warnings

        Returns:
            True if notification should be sent
        """
        if has_errors and self.send_on_errors:
            return True
        if has_warnings and self.send_on_warnings:
            return True
        if not has_errors and not has_warnings and self.send_on_success:
            return True

        return False

    def send_sync_report(
        self,
        summary: Dict[str, Any],
        not_found_products: List[Dict[str, Any]],
        flagged_products: List[Dict[str, Any]],
        errors: List[Dict[str, Any]],
        suppliers_processed: List[str]
    ):
        """Send sync report email.

        Args:
            summary: Summary statistics dictionary
            not_found_products: List of products not found in Shopify
            flagged_products: List of products flagged for review
            errors: List of errors
            suppliers_processed: List of processed supplier names
        """
        has_errors = summary.get("errors", 0) > 0
        has_warnings = (
            summary.get("not_found_in_shopify", 0) > 0 or
            summary.get("flagged_for_review", 0) > 0 or
            summary.get("duplicate_identifiers", 0) > 0
        )

        if not self.should_send(has_errors, has_warnings):
            return

        # Determine email type for subject
        if has_errors:
            status = "⚠️ ERRORS"
        elif has_warnings:
            status = "⚠️ WARNINGS"
        else:
            status = "✓ SUCCESS"

        subject = f"{self.subject_prefix} {status} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # Build email body
        body = self._build_email_body(
            summary,
            not_found_products,
            flagged_products,
            errors,
            suppliers_processed
        )

        # Send email
        try:
            self._send_email(subject, body)
            print(f"✓ Email notification sent to {', '.join(self.to_emails)}")
        except Exception as e:
            print(f"✗ Failed to send email notification: {e}")

    def _build_email_body(
        self,
        summary: Dict[str, Any],
        not_found_products: List[Dict[str, Any]],
        flagged_products: List[Dict[str, Any]],
        errors: List[Dict[str, Any]],
        suppliers_processed: List[str]
    ) -> str:
        """Build email body text.

        Args:
            summary: Summary statistics
            not_found_products: Products not found in Shopify
            flagged_products: Products flagged for review
            errors: Error list
            suppliers_processed: List of suppliers processed

        Returns:
            Email body as plain text
        """
        lines = []
        lines.append("Inventory Sync Report")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Suppliers: {', '.join(suppliers_processed)}")
        lines.append("")

        # Summary
        lines.append("SUMMARY")
        lines.append("-" * 60)
        lines.append(f"Total supplier products:  {summary.get('total_supplier_products', 0)}")
        lines.append(f"Matched in Shopify:       {summary.get('matched_products', 0)}")
        lines.append(f"Updated in Shopify:       {summary.get('updated_in_shopify', 0)}")
        lines.append(f"No change needed:         {summary.get('no_change', 0)}")
        lines.append("")
        lines.append(f"Not found in Shopify:     {summary.get('not_found_in_shopify', 0)}")
        lines.append(f"Duplicate identifiers:    {summary.get('duplicate_identifiers', 0)}")
        lines.append(f"Flagged for review:       {summary.get('flagged_for_review', 0)}")
        lines.append(f"Errors:                   {summary.get('errors', 0)}")
        lines.append("")

        # Products not found in Shopify
        if not_found_products:
            lines.append("PRODUCTS NOT FOUND IN SHOPIFY")
            lines.append("-" * 60)
            for product in not_found_products[:20]:  # Limit to 20 to keep email reasonable
                ean = product.get("ean", "N/A")
                sku = product.get("sku", "N/A")
                supplier = product.get("supplier", "N/A")
                lines.append(f"  • EAN: {ean} / SKU: {sku} (from {supplier})")

            if len(not_found_products) > 20:
                lines.append(f"  ... and {len(not_found_products) - 20} more")
            lines.append("")

        # Flagged products
        if flagged_products:
            lines.append("PRODUCTS FLAGGED FOR REVIEW")
            lines.append("-" * 60)
            for product in flagged_products[:20]:
                ean = product.get("ean", "N/A")
                sku = product.get("sku", "N/A")
                reason = product.get("reason", "N/A")
                old_qty = product.get("old_qty", 0)
                new_qty = product.get("new_qty", 0)
                lines.append(f"  • EAN: {ean} / SKU: {sku}")
                lines.append(f"    Reason: {reason}")
                lines.append(f"    Change: {old_qty} → {new_qty}")

            if len(flagged_products) > 20:
                lines.append(f"  ... and {len(flagged_products) - 20} more")
            lines.append("")

        # Errors
        if errors:
            lines.append("ERRORS")
            lines.append("-" * 60)
            for error in errors[:10]:
                error_type = error.get("type", "Unknown")
                message = error.get("message", "No message")
                lines.append(f"  • {error_type}: {message}")

            if len(errors) > 10:
                lines.append(f"  ... and {len(errors) - 10} more")
            lines.append("")

        # Footer
        lines.append("-" * 60)
        lines.append("This is an automated message from the Inventory Sync System.")
        lines.append("Please review flagged items and address any errors.")

        return "\n".join(lines)

    def _send_email(self, subject: str, body: str):
        """Send email via SMTP.

        Args:
            subject: Email subject
            body: Email body (plain text)

        Raises:
            Exception: If sending fails
        """
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = ", ".join(self.to_emails)

        # Add body
        text_part = MIMEText(body, "plain")
        msg.attach(text_part)

        # Send via SMTP
        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
            server.starttls()  # Enable TLS
            server.login(self.username, self.password)
            server.send_message(msg)

    def test_connection(self) -> bool:
        """Test SMTP connection and authentication.

        Returns:
            True if connection successful
        """
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                server.starttls()
                server.login(self.username, self.password)
            print(f"✓ Email SMTP connection successful")
            return True
        except Exception as e:
            print(f"✗ Email SMTP connection failed: {e}")
            return False
