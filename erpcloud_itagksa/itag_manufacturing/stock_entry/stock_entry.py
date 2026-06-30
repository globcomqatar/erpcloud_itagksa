# -*- coding: utf-8 -*-
# Copyright (c) 2026, Globcom Manufacturing and contributors
# For license information, please see license.txt

"""
Stock Entry Controller

Handles custom validations for Stock Entry including serial number
attribute validation (Heat No, Drawing No, Part No).
"""

import frappe
from frappe import _
from frappe.utils import add_days, flt, today
from erpcloud_itagksa.itag_manufacturing.utils.serial_no_validation import (
    validate_stock_entry_items,
    update_serial_no_master_on_receipt
)


def validate(doc, method=None):
    """Validate Stock Entry before save/submit.

    Called via doc_events hook in hooks.py.

    Args:
        doc: Stock Entry document
        method: Event method name (not used)
    """
    # Populate serial attributes from Work Order Item (if created from Work Order)
    populate_serial_attributes_from_work_order(doc)

    # Validate serial number attributes
    validate_stock_entry_items(doc)


def on_submit(doc, method=None):
    """Update Serial No master and SO GRN status after Stock Entry submission.

    Called via doc_events hook in hooks.py.

    Args:
        doc: Stock Entry document
        method: Event method name (not used)
    """
    update_serial_no_master_on_receipt(doc)
    update_so_grn_status(doc)


def on_cancel(doc, method=None):
    """Update SO GRN status when a Material Receipt is cancelled.

    Called via doc_events hook in hooks.py.

    Args:
        doc: Stock Entry document
        method: Event method name (not used)
    """
    update_so_grn_status(doc)


def update_so_grn_status(doc):
    """Update custom_grn_status on the linked Sales Order.

    Computes receipt progress by summing received qty across all non-cancelled
    Material Receipt Stock Entries for each SO item and sets the status field.

    Status values:
        "Not Received"       — no qty received yet
        "Partially Received" — some qty received but not all items at 100%
        "Fully Received"     — all SO items received in full

    Only runs for Material Receipt Stock Entries linked to a Sales Order.

    Args:
        doc: Stock Entry document
    """
    if doc.purpose != "Material Receipt":
        return

    sales_order_name = doc.custom_customer_sales_order_number
    if not sales_order_name:
        return

    so_items = frappe.db.get_all(
        "Sales Order Item",
        filters={"parent": sales_order_name},
        fields=["item_code", "qty"],
    )

    if not so_items:
        return

    total_ordered = 0.0
    total_received = 0.0

    for so_item in so_items:
        received_qty = frappe.db.sql("""
            SELECT COALESCE(SUM(sed.qty), 0)
            FROM `tabStock Entry Detail` sed
            JOIN `tabStock Entry` se ON se.name = sed.parent
            WHERE se.custom_customer_sales_order_number = %(sales_order)s
            AND se.purpose = 'Material Receipt'
            AND se.docstatus != 2
            AND sed.item_code = %(item_code)s
        """, {
            "sales_order": sales_order_name,
            "item_code": so_item.item_code,
        })[0][0] or 0

        total_ordered += flt(so_item.qty)
        total_received += flt(received_qty)

    if total_received <= 0:
        grn_status = "Not Received"
    elif total_received >= total_ordered:
        grn_status = "Fully Received"
    else:
        grn_status = "Partially Received"

    frappe.db.set_value("Sales Order", sales_order_name, "custom_grn_status", grn_status)


def populate_serial_attributes_from_work_order(doc):
    """Populate serial attributes from Work Order required_items to Stock Entry Detail.

    Handles two Stock Entry purposes:

    - Material Transfer for Manufacture:
        Copies serial_no, heat_no, heat_lot_no, drawing_no, part_no to all SE items
        that match a Work Order required_item by item_code.

    - Manufacture (Finish):
        Copies serial attributes only to consumed items (those with s_warehouse set).
        Finished goods items (t_warehouse only) are left untouched — user enters
        serial details manually for the finished product.

    Args:
        doc: Stock Entry document
    """
    if not doc.work_order:
        return

    if doc.purpose not in ("Material Transfer for Manufacture", "Manufacture"):
        return

    work_order = frappe.get_doc("Work Order", doc.work_order)

    # Build item_code → Work Order Item lookup for quick matching
    wo_items_map = {}
    for wo_item in work_order.required_items:
        wo_items_map[wo_item.item_code] = wo_item

    if doc.purpose == "Material Transfer for Manufacture":
        # Copy serial attributes to all SE items matching WO required_items
        for se_item in doc.items:
            if se_item.item_code not in wo_items_map:
                continue
            wo_item = wo_items_map[se_item.item_code]
            se_item.serial_no = wo_item.custom_serial_no or ""
            se_item.custom_heat_no = wo_item.custom_heat_no or ""
            se_item.custom_heat_lot_no = wo_item.custom_heat_lot_no or ""
            se_item.custom_drawing_no = wo_item.custom_drawing_no or ""
            se_item.custom_part_no = wo_item.custom_part_no or ""

    elif doc.purpose == "Manufacture":
        # Copy serial attributes only to consumed items (items with s_warehouse)
        # Finished goods items (t_warehouse only) are intentionally skipped
        for se_item in doc.items:
            if not se_item.s_warehouse:
                continue  # Skip finished goods items

            if se_item.item_code not in wo_items_map:
                continue

            wo_item = wo_items_map[se_item.item_code]
            se_item.serial_no = wo_item.custom_serial_no or ""
            se_item.custom_heat_no = wo_item.custom_heat_no or ""
            se_item.custom_heat_lot_no = wo_item.custom_heat_lot_no or ""
            se_item.custom_drawing_no = wo_item.custom_drawing_no or ""
            se_item.custom_part_no = wo_item.custom_part_no or ""


@frappe.whitelist()
def create_sales_order_from_stock_entry(stock_entry_name):
    """Create a draft Sales Order from a subcontracted Stock Entry for billing.

    Maps customer and item information from the Stock Entry, saves the Sales Order
    as a draft, then links it back to the Stock Entry via custom_customer_sales_order_number.

    Args:
        stock_entry_name (str): Stock Entry name

    Returns:
        str: Created Sales Order name

    Raises:
        frappe.ValidationError: If SE is not subcontracted, SO already exists, or no customer set
    """
    stock_entry = frappe.get_doc("Stock Entry", stock_entry_name)

    if not stock_entry.custom_subcontracted_job:
        frappe.throw(_("Sales Order can only be created for subcontracted Stock Entries."))

    if stock_entry.custom_customer_sales_order_number:
        frappe.throw(
            _("Sales Order {0} is already linked to this Stock Entry.").format(
                stock_entry.custom_customer_sales_order_number
            )
        )

    if not stock_entry.custom_customer:
        frappe.throw(_("Customer must be set on the Stock Entry before creating a Sales Order."))

    sales_order = frappe.new_doc("Sales Order")
    sales_order.customer = stock_entry.custom_customer
    sales_order.custom_subcontracted_job = 1
    sales_order.po_no = stock_entry.custom_customer_po_no or ""
    sales_order.delivery_date = add_days(today(), 30)

    for se_item in stock_entry.items:
        sales_order.append("items", {
            "item_code": se_item.item_code,
            "qty": se_item.qty,
            "uom": se_item.uom or se_item.stock_uom,
            "delivery_date": sales_order.delivery_date,
        })

    if not sales_order.items:
        frappe.throw(_("No items found in Stock Entry to add to Sales Order."))

    sales_order.insert(ignore_permissions=False)

    # Link the new Sales Order back to the Stock Entry
    frappe.db.set_value(
        "Stock Entry",
        stock_entry_name,
        "custom_customer_sales_order_number",
        sales_order.name
    )

    # Link the new Sales Order to the Work Order created from this Stock Entry
    linked_work_order = frappe.db.get_value(
        "Work Order",
        {"custom_stock_entry": stock_entry_name, "docstatus": ["!=", 2]},
        "name"
    )
    if linked_work_order:
        frappe.db.set_value("Work Order", linked_work_order, "sales_order", sales_order.name)

    return sales_order.name


