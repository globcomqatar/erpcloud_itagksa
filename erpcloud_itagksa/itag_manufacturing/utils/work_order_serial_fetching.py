# -*- coding: utf-8 -*-
# Copyright (c) 2026, Globcom Manufacturing and contributors
# For license information, please see license.txt

"""
Work Order Serial Number Fetching

Auto-fetches serial numbers from Stock Entries when Work Order
is created from Sales Order.
"""

import frappe
from frappe import _
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpcloud_itagksa.itag_manufacturing.utils.serial_field_utils import populate_serial_fields


def fetch_serials_from_stock_entries(work_order):
    """Fetch serial numbers from Stock Entries linked to Sales Order.

    Fetches serials on FIFO basis (oldest Stock Entry first) and populates
    Work Order Item (required_items) with serial numbers, heat numbers,
    drawing numbers, and part numbers.

    Args:
        work_order: Work Order document

    Logic:
        1. Find Stock Entries linked to Sales Order
        2. For each Work Order Item, fetch serials FIFO
        3. Track already allocated serials
        4. Only fetch quantity needed
        5. Populate Work Order Item fields
    """
    # Skip if no Sales Order linked
    if not work_order.sales_order:
        return

    # Find Stock Entries linked to this Sales Order
    stock_entries = frappe.get_all(
        "Stock Entry",
        filters={
            "custom_customer_sales_order_number": work_order.sales_order,
            "custom_subcontracted_job": 1,
            "docstatus": 1
        },
        fields=["name", "posting_date"],
        order_by="posting_date ASC"  # FIFO - oldest first
    )

    if not stock_entries:
        return

    # Get already allocated serials from other Work Orders for this Sales Order
    allocated_serials = get_allocated_serials(work_order.sales_order, exclude_work_order=work_order.name)

    # Process each Work Order Item (required_items)
    for wo_item in work_order.required_items:
        if not wo_item.required_qty:
            continue

        # Fetch serials for this item
        serials_data = fetch_serials_for_item(
            item_code=wo_item.item_code,
            required_qty=wo_item.required_qty,
            stock_entries=stock_entries,
            allocated_serials=allocated_serials
        )

        if serials_data:
            # Populate Work Order Item fields using reusable utility
            populate_serial_fields(wo_item, serials_data)


def get_allocated_serials(sales_order, exclude_work_order=None):
    """Get serials already allocated to other Work Orders for this Sales Order.

    Args:
        sales_order (str): Sales Order name
        exclude_work_order (str): Work Order name to exclude (current WO)

    Returns:
        set: Set of serial numbers already allocated
    """
    allocated_serials = set()

    # Get all Work Orders for this Sales Order (except current one)
    filters = {"sales_order": sales_order}
    if exclude_work_order:
        filters["name"] = ["!=", exclude_work_order]

    work_orders = frappe.get_all(
        "Work Order",
        filters=filters,
        fields=["name"]
    )

    # Collect serials from all Work Order Items
    for wo in work_orders:
        wo_doc = frappe.get_doc("Work Order", wo.name)
        for item in wo_doc.required_items:
            if item.get('custom_serial_no'):
                serials = get_serial_nos(item.custom_serial_no)
                allocated_serials.update(serials)

    return allocated_serials


def fetch_serials_for_item(item_code, required_qty, stock_entries, allocated_serials):
    """Fetch serials for a specific item from Stock Entries (FIFO).

    Args:
        item_code (str): Item code to fetch serials for
        required_qty (float): Quantity needed
        stock_entries (list): List of Stock Entry names (ordered by posting_date)
        allocated_serials (set): Already allocated serial numbers to skip

    Returns:
        dict: {serial_nos: [], heat_nos: [], heat_lot_nos: [], drawing_no: str, part_nos: []}
        Note: drawing_no is a single value (Data field), not an array
    """
    result = {
        'serial_nos': [],
        'heat_nos': [],
        'heat_lot_nos': [],
        'drawing_no': '',  # Single value (Data field)
        'part_nos': []
    }

    qty_fetched = 0

    # Process Stock Entries in FIFO order
    for ste in stock_entries:
        if qty_fetched >= required_qty:
            break  # Got enough serials

        # Get Stock Entry document
        ste_doc = frappe.get_doc("Stock Entry", ste.name)

        # Find items matching this item_code
        for item in ste_doc.items:
            if item.item_code != item_code:
                continue

            if not item.get('serial_no'):
                continue

            # Parse serial numbers
            # Note: custom_drawing_no is a Data field (single value), not Text field
            serial_nos = get_serial_nos(item.serial_no)
            heat_nos = get_serial_nos(item.get('custom_heat_no') or '')
            heat_lot_nos = get_serial_nos(item.get('custom_heat_lot_no') or '')
            drawing_no = item.get('custom_drawing_no') or ''  # Single value (Data field)
            part_nos = get_serial_nos(item.get('custom_part_no') or '')

            # Fetch serials one by one (FIFO within Stock Entry)
            for idx, serial_no in enumerate(serial_nos):
                if qty_fetched >= required_qty:
                    break

                # Skip if already allocated
                if serial_no in allocated_serials:
                    continue

                # Add serial and corresponding attributes
                result['serial_nos'].append(serial_no)

                # Add corresponding heat/part number (same index)
                if idx < len(heat_nos):
                    result['heat_nos'].append(heat_nos[idx])
                if idx < len(heat_lot_nos):
                    result['heat_lot_nos'].append(heat_lot_nos[idx])
                if idx < len(part_nos):
                    result['part_nos'].append(part_nos[idx])

                # Set drawing number (single value shared across all serials)
                if drawing_no and not result['drawing_no']:
                    result['drawing_no'] = drawing_no

                qty_fetched += 1

            if qty_fetched >= required_qty:
                break  # Got enough from this Stock Entry

    return result if result['serial_nos'] else None
