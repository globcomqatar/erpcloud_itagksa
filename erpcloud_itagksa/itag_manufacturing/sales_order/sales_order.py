# -*- coding: utf-8 -*-
# Copyright (c) 2026, Globcom Manufacturing and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import today, flt
from frappe.model.mapper import get_mapped_doc


@frappe.whitelist()
def create_material_receipt_from_sales_order(source_name, target_doc=None):
    """Create Material Receipt Stock Entry from Sales Order.

    Uses Frappe's get_mapped_doc utility for proper field mapping.

    Args:
        source_name (str): Sales Order name/ID
        target_doc: Target document (optional)

    Returns:
        Document: Stock Entry document (unsaved)

    Raises:
        frappe.ValidationError: If Sales Order not found or not submitted
    """

    def set_missing_values(source, target):
        """Set custom fields and stock entry type."""
        target.stock_entry_type = "Material Receipt - CPI"
        target.posting_date = today()
        target.custom_customer_sales_order_number = source.name
        target.custom_customer_name__cpi = source.customer_name
        target.custom_subcontracted_job = 1
        target.custom_inward_inspection_required = 1

    def update_item(source_item, target_item, source_parent):
        """Set target qty to remaining unreceived quantity for this item.

        Subtracts already-received qty (across all non-cancelled Material
        Receipts for this SO) from the SO ordered qty so the new GRN
        opens pre-filled with what's still outstanding.
        """
        already_received = frappe.db.sql("""
            SELECT COALESCE(SUM(sed.qty), 0)
            FROM `tabStock Entry Detail` sed
            JOIN `tabStock Entry` se ON se.name = sed.parent
            WHERE se.custom_customer_sales_order_number = %(sales_order)s
            AND se.purpose = 'Material Receipt'
            AND se.docstatus != 2
            AND sed.item_code = %(item_code)s
        """, {
            "sales_order": source_parent.name,
            "item_code": source_item.item_code,
        })[0][0] or 0

        remaining_qty = flt(source_item.qty) - flt(already_received)
        target_item.qty = max(flt(remaining_qty), 0)
        target_item.transfer_qty = target_item.qty

    # Use get_mapped_doc to map Sales Order to Stock Entry
    doc = get_mapped_doc(
        "Sales Order",
        source_name,
        {
            "Sales Order": {
                "doctype": "Stock Entry",
                "validation": {
                    "docstatus": ["=", 1]
                }
            },
            "Sales Order Item": {
                "doctype": "Stock Entry Detail",
                "field_map": {
                    "uom": "uom",
                    "stock_uom": "stock_uom"
                },
                "condition": lambda item: frappe.db.get_value("Item", item.item_code, "is_stock_item"),
                "postprocess": update_item
            }
        },
        target_doc,
        set_missing_values
    )

    return doc


@frappe.whitelist()
def has_material_receipt(sales_order_name):
    """Check if Material Receipt Stock Entry already exists for Sales Order.

    Args:
        sales_order_name (str): Sales Order name/ID

    Returns:
        dict: {"exists": bool, "stock_entry": str or None}
    """
    if not sales_order_name:
        return {"exists": False, "stock_entry": None}

    stock_entry = frappe.db.get_value(
        "Stock Entry",
        {
            "custom_customer_sales_order_number": sales_order_name,
            "purpose": "Material Receipt",
            "docstatus": ["!=", 2]
        },
        "name"
    )

    return {
        "exists": bool(stock_entry),
        "stock_entry": stock_entry
    }


def validate_subcontract_grn_exists(sales_order_name):
    """Validate that GRN exists for subcontracted Sales Order.

    For subcontracted jobs, a submitted Material Receipt (GRN) must exist
    before Work Order can be created.

    Args:
        sales_order_name (str): Sales Order name/ID

    Raises:
        frappe.ValidationError: If Sales Order is subcontracted but no GRN exists

    Returns:
        bool: True if validation passes (not subcontracted OR GRN exists)
    """
    if not sales_order_name:
        return True

    # Check if Sales Order is subcontracted
    sales_order = frappe.db.get_value(
        "Sales Order",
        sales_order_name,
        ["custom_subcontracted_job", "name"],
        as_dict=True
    )

    # If not found or not subcontracted, no validation needed
    if not sales_order or not sales_order.get("custom_subcontracted_job"):
        return True

    # Check if submitted Material Receipt exists
    grn_exists = frappe.db.exists(
        "Stock Entry",
        {
            "custom_customer_sales_order_number": sales_order_name,
            "purpose": "Material Receipt",
            "custom_subcontracted_job": 1,
            "docstatus": 1  # Must be submitted
        }
    )

    if not grn_exists:
        frappe.throw(
            _(
                "<b>Cannot Create Work Order for Subcontracted Job</b><br><br>"
                "This Sales Order (<b>{0}</b>) is marked as a subcontracted job. "
                "You must create and submit a <b>Good Receipt Note (GRN)</b> before creating a Work Order.<br><br>"
                "<b>Steps:</b><br>"
                "1. Go to Sales Order: {0}<br>"
                "2. Click <b>Create > Good Receipt Note</b><br>"
                "3. Fill in the received materials and submit<br>"
                "4. Then create the Work Order"
            ).format(sales_order_name),
            title=_("GRN Required for Subcontracted Job")
        )

    return True
