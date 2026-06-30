# -*- coding: utf-8 -*-
# Copyright (c) 2026, Globcom Manufacturing and contributors
# For license information, please see license.txt

"""
Reusable Serial Number Validation Utilities

This module provides validation functions for serial number attributes
(Heat No, Drawing No, Part No) that can be used across doctypes:
- Stock Entry (Material Receipt, Material Transfer)
- Delivery Note (future)
- Purchase Receipt (future)
"""

import frappe
from frappe import _

# Use ERPNext's standard serial number parsing utility
# Handles both comma and newline separators, more robust than custom implementation
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos


def validate_1_to_1_counts(item, row_number=None):
    """Validate 1:1 relationship between serial nos and attributes.

    For Material Receipt (subcontracted jobs only): Each serial number must
    have exactly one heat number, drawing number, and part number.

    Note: This validation only runs when Stock Entry has
    custom_subcontracted_job = 1.

    Args:
        item: Stock Entry Detail item
        row_number (int): Row number for error message

    Raises:
        frappe.ValidationError: If counts don't match
    """
    # Skip if validation is disabled
    if item.get('custom_disable_1_to_1_validation'):
        return

    # Skip if no serial numbers
    if not item.get('serial_no'):
        return

    # Parse all fields
    # Note: custom_drawing_no is a Data field (single value), not Text field
    # Drawing number is shared across all serial numbers (not 1:1 relationship)
    serial_nos = get_serial_nos(item.serial_no)
    heat_nos = get_serial_nos(item.get('custom_heat_no'))
    heat_lot_nos = get_serial_nos(item.get('custom_heat_lot_no'))
    part_nos = get_serial_nos(item.get('custom_part_no'))

    # Get counts
    serial_count = len(serial_nos)
    heat_count = len(heat_nos)
    heat_lot_count = len(heat_lot_nos)
    part_count = len(part_nos)

    # Validate counts match (excluding drawing_no which is a single shared value)
    if not (serial_count == heat_count == heat_lot_count == part_count):
        row_label = f"Row {row_number}" if row_number else "Item"

        # Build detailed error message with formatting
        # Note: Drawing No is excluded as it's a single shared value (Data field)
        error_msg = _(
            "<b>{0}: Serial Number Validation Failed</b><br><br>"
            "Each serial number must have exactly one Heat No, Heat Lot No, and Part No.<br>"
            "(Drawing No is shared across all serials)<br><br>"
            "<b>Expected:</b> {1} of each<br>"
            "<b>Found:</b><br>"
            "• Serial Numbers: {2}<br>"
            "• Heat Numbers: {3} {4}<br>"
            "• Heat Lot Numbers: {5} {6}<br>"
            "• Part Numbers: {7} {8}"
        ).format(
            row_label,
            serial_count,
            serial_count,
            heat_count,
            "❌" if heat_count != serial_count else "✓",
            heat_lot_count,
            "❌" if heat_lot_count != serial_count else "✓",
            part_count,
            "❌" if part_count != serial_count else "✓"
        )

        frappe.throw(error_msg)


def validate_serial_attributes_match(item, row_number=None):
    """Validate that heat/drawing/part numbers match Serial No master.

    For Material Transfer/Issue: Verify that the entered heat number,
    drawing number, and part number belong to the specified serial numbers.

    Args:
        item: Stock Entry Detail item
        row_number (int): Row number for error message

    Raises:
        frappe.ValidationError: If attributes don't match Serial No master
    """
    # Skip if validation is disabled
    if item.get('custom_disable_1_to_1_validation'):
        return

    # Skip if no serial numbers
    if not item.get('serial_no'):
        return

    # Parse fields
    # Note: custom_drawing_no is a Data field (single value), not Text field
    serial_nos = get_serial_nos(item.serial_no)
    heat_nos = get_serial_nos(item.get('custom_heat_no'))
    heat_lot_nos = get_serial_nos(item.get('custom_heat_lot_no'))
    drawing_no = item.get('custom_drawing_no') or ''  # Single value (Data field)
    part_nos = get_serial_nos(item.get('custom_part_no'))

    # Fetch Serial No master data for all serial numbers
    serial_data = {}
    for serial_no in serial_nos:
        if frappe.db.exists("Serial No", serial_no):
            data = frappe.db.get_value(
                "Serial No",
                serial_no,
                ["custom_heat_no", "custom_heat_lot_no", "custom_drawing_no", "custom_part_no"],
                as_dict=True
            )
            serial_data[serial_no] = data

    # Build sets of valid values from Serial No master
    valid_heat_nos = set()
    valid_heat_lot_nos = set()
    valid_drawing_nos = set()
    valid_part_nos = set()

    for serial_no, data in serial_data.items():
        if data.get('custom_heat_no'):
            valid_heat_nos.add(data['custom_heat_no'])
        if data.get('custom_heat_lot_no'):
            valid_heat_lot_nos.add(data['custom_heat_lot_no'])
        if data.get('custom_drawing_no'):
            valid_drawing_nos.add(data['custom_drawing_no'])
        if data.get('custom_part_no'):
            valid_part_nos.add(data['custom_part_no'])

    # Validate heat numbers
    for heat_no in heat_nos:
        if heat_no not in valid_heat_nos:
            row_label = f"Row {row_number}" if row_number else "Item"
            valid_list = "<br>• ".join(sorted(valid_heat_nos)) if valid_heat_nos else "None found"
            frappe.throw(_(
                "<b>{0}: Invalid Heat Number</b><br><br>"
                "Heat No <b>'{1}'</b> does not belong to the selected serial numbers.<br><br>"
                "<b>Valid Heat Numbers:</b><br>• {2}"
            ).format(row_label, heat_no, valid_list))

    # Validate heat lot numbers
    for heat_lot_no in heat_lot_nos:
        if heat_lot_no not in valid_heat_lot_nos:
            row_label = f"Row {row_number}" if row_number else "Item"
            valid_list = "<br>• ".join(sorted(valid_heat_lot_nos)) if valid_heat_lot_nos else "None found"
            frappe.throw(_(
                "<b>{0}: Invalid Heat Lot Number</b><br><br>"
                "Heat Lot No <b>'{1}'</b> does not belong to the selected serial numbers.<br><br>"
                "<b>Valid Heat Lot Numbers:</b><br>• {2}"
            ).format(row_label, heat_lot_no, valid_list))

    # Validate drawing number (single value - Data field)
    if drawing_no and drawing_no not in valid_drawing_nos:
        row_label = f"Row {row_number}" if row_number else "Item"
        valid_list = "<br>• ".join(sorted(valid_drawing_nos)) if valid_drawing_nos else "None found"
        frappe.throw(_(
            "<b>{0}: Invalid Drawing Number</b><br><br>"
            "Drawing No <b>'{1}'</b> does not belong to the selected serial numbers.<br><br>"
            "<b>Valid Drawing Numbers:</b><br>• {2}"
        ).format(row_label, drawing_no, valid_list))

    # Validate part numbers
    for part_no in part_nos:
        if part_no not in valid_part_nos:
            row_label = f"Row {row_number}" if row_number else "Item"
            valid_list = "<br>• ".join(sorted(valid_part_nos)) if valid_part_nos else "None found"
            frappe.throw(_(
                "<b>{0}: Invalid Part Number</b><br><br>"
                "Part No <b>'{1}'</b> does not belong to the selected serial numbers.<br><br>"
                "<b>Valid Part Numbers:</b><br>• {2}"
            ).format(row_label, part_no, valid_list))


def validate_stock_entry_items(stock_entry):
    """Validate all items in Stock Entry based on entry type.

    This is the main validation function called from Stock Entry controller.

    Args:
        stock_entry: Stock Entry document

    Validation Rules:
    - Material Receipt (subcontracted only): 1:1 count validation
    - Material Transfer/Issue: Attribute matching validation
    - Other types: No validation
    """
    if not stock_entry.items:
        return

    for idx, item in enumerate(stock_entry.items, start=1):
        # Skip items without serial numbers
        if not item.get('serial_no'):
            continue

        # Skip if validation is disabled for this item
        if item.get('custom_disable_1_to_1_validation'):
            continue

        # Apply validation based on Stock Entry purpose (works for custom Stock Entry Types)
        if stock_entry.purpose == "Material Receipt":
            # ONLY validate 1:1 for subcontracted jobs
            if stock_entry.get('custom_subcontracted_job'):
                validate_1_to_1_counts(item, row_number=idx)

        elif stock_entry.purpose in ["Material Transfer", "Material Issue"]:
            # For Transfer/Issue: Validate attributes match Serial No master
            validate_serial_attributes_match(item, row_number=idx)

        # For other stock entry types, no validation is applied
        # Future: Add validation for other types as needed


def update_serial_no_master_on_receipt(stock_entry):
    """Update Serial No master with heat/drawing/part numbers on Material Receipt.

    This creates a permanent record of attributes in the Serial No master,
    enabling validation on all future transactions.

    Args:
        stock_entry: Stock Entry document

    Note:
        Only runs for Material Receipt stock entry type with subcontracted jobs.
        Attributes are stored permanently in Serial No master.
    """
    # Only update for Material Receipt purpose (works for custom Stock Entry Types like "Material Receipt - CPI")
    if stock_entry.purpose != "Material Receipt":
        return

    # Only update for subcontracted jobs
    if not stock_entry.get('custom_subcontracted_job'):
        return

    if not stock_entry.items:
        return

    for item in stock_entry.items:
        # Skip items without serial numbers
        if not item.get('serial_no'):
            continue

        # Skip if no attributes to update
        if not any([item.get('custom_heat_no'), item.get('custom_heat_lot_no'), item.get('custom_drawing_no'), item.get('custom_part_no')]):
            continue

        # Parse all fields using ERPNext's utility
        # Note: custom_drawing_no is a Data field (single value shared across all serials)
        serial_nos = get_serial_nos(item.serial_no)
        heat_nos = get_serial_nos(item.get('custom_heat_no'))
        heat_lot_nos = get_serial_nos(item.get('custom_heat_lot_no'))
        drawing_no = item.get('custom_drawing_no') or ''  # Single value (Data field)
        part_nos = get_serial_nos(item.get('custom_part_no'))

        # Update each serial number with its corresponding attributes
        # Assumes 1:1 relationship (already validated in validate_1_to_1_counts)
        for idx, serial_no in enumerate(serial_nos):
            # Check if Serial No exists
            if not frappe.db.exists("Serial No", serial_no):
                continue

            # Prepare update dict
            update_dict = {}

            # Add heat number if available
            if idx < len(heat_nos) and heat_nos[idx]:
                update_dict['custom_heat_no'] = heat_nos[idx]

            # Add heat lot number if available
            if idx < len(heat_lot_nos) and heat_lot_nos[idx]:
                update_dict['custom_heat_lot_no'] = heat_lot_nos[idx]

            # Add drawing number if available (single value shared across all serials)
            if drawing_no:
                update_dict['custom_drawing_no'] = drawing_no

            # Add part number if available
            if idx < len(part_nos) and part_nos[idx]:
                update_dict['custom_part_no'] = part_nos[idx]

            # Update Serial No master using Document API
            if update_dict:
                serial_no_doc = frappe.get_doc("Serial No", serial_no)

                # Update fields
                for field, value in update_dict.items():
                    serial_no_doc.set(field, value)

                # Save using proper Document API (triggers hooks and validation)
                serial_no_doc.save()
