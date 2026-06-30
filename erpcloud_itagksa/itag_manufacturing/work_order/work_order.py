# -*- coding: utf-8 -*-
# Copyright (c) 2026, Globcom Manufacturing and contributors
# For license information, please see license.txt

"""
Work Order Controller

Auto-fetches serial numbers from Stock Entries when Work Order
is created from Sales Order.

Validates that GRN exists for subcontracted Sales Orders before
allowing Work Order creation.
"""

import frappe
from frappe import _
from erpcloud_itagksa.itag_manufacturing.utils.work_order_serial_fetching import (
    fetch_serials_from_stock_entries
)
from erpcloud_itagksa.itag_manufacturing.sales_order.sales_order import validate_subcontract_grn_exists


def validate(doc, method=None):
    """Validate Work Order before save.

    Called via doc_events hook in hooks.py.

    Args:
        doc: Work Order document
        method: Event method name (not used)

    Validations:
    - If linked Sales Order is subcontracted, GRN must exist
    - If linked to a Stock Entry, populate subcontracted flag and serial fields
    """
    # Validate GRN exists for subcontracted Sales Orders
    if doc.sales_order:
        validate_subcontract_grn_exists(doc.sales_order)

    # Populate fields from linked Stock Entry (SE → WO flow)
    if doc.custom_stock_entry:
        populate_fields_from_stock_entry(doc)


def after_insert(doc, method=None):
    """Auto-fetch serial numbers after Work Order creation.

    Called via doc_events hook in hooks.py.

    Args:
        doc: Work Order document
        method: Event method name (not used)
    """
    # Fetch serials from Stock Entries linked via Sales Order (existing flow)
    fetch_serials_from_stock_entries(doc)


def populate_fields_from_stock_entry(work_order):
    """Populate Work Order fields from directly linked Stock Entry.

    Called during validate when custom_stock_entry is set. Handles:
    1. Sets custom_subcontracted_job to match the source Stock Entry.
    2. For each required_item whose serial fields are empty, copies
       serial_no, heat_no, heat_lot_no, drawing_no, and part_no from
       the matching Stock Entry Detail row (matched by item_code).

    Only fills empty fields — does not overwrite values the user has set.

    Args:
        work_order: Work Order document (in-memory, modifications persist on save)
    """
    stock_entry = frappe.get_doc("Stock Entry", work_order.custom_stock_entry)

    # Mirror the subcontracted flag from the source Stock Entry
    work_order.custom_subcontracted_job = stock_entry.custom_subcontracted_job

    if not work_order.required_items:
        return

    # Build a lookup of SE items by item_code (first match per code)
    se_items_by_code = {}
    for se_item in stock_entry.items:
        if se_item.item_code not in se_items_by_code:
            se_items_by_code[se_item.item_code] = se_item

    if not se_items_by_code:
        return

    for wo_item in work_order.required_items:
        se_item = se_items_by_code.get(wo_item.item_code)
        if not se_item:
            continue

        # Only populate serial fields that are currently empty
        if wo_item.custom_serial_no:
            continue

        wo_item.custom_serial_no = se_item.get("serial_no") or ""
        wo_item.custom_heat_no = se_item.get("custom_heat_no") or ""
        wo_item.custom_heat_lot_no = se_item.get("custom_heat_lot_no") or ""
        wo_item.custom_drawing_no = se_item.get("custom_drawing_no") or ""
        wo_item.custom_part_no = se_item.get("custom_part_no") or ""
