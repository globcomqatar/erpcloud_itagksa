import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc

from erpcloud_itagksa.itag_manufacturing.purchase_order.purchase_order import (
    recompute_collaboration_status,
)


def validate(doc, method=None):
    _validate_mutual_exclusion(doc)
    _validate_receipt_cumulative_qty(doc)


def on_submit(doc, method=None):
    _recompute_po_status_if_issue(doc)


def on_cancel(doc, method=None):
    _recompute_po_status_if_issue(doc)


def _validate_mutual_exclusion(doc):
    if doc.custom_is_collaboration_delivery_note and doc.custom_is_collaboration_grn:
        frappe.throw(
            _("A Stock Entry cannot be both a Collaboration Delivery Note and a Collaboration GRN."),
            title=_("Collaboration SE validation"),
        )


def _validate_receipt_cumulative_qty(doc):
    if not doc.custom_is_collaboration_grn:
        return
    if not doc.outgoing_stock_entry:
        return
    if not _get_validate_receipt_qty_setting():
        return

    issued_per_item = _issued_qty_by_item(doc.outgoing_stock_entry)
    received_prior = _prior_received_qty_by_item(doc.outgoing_stock_entry, exclude_name=doc.name)
    pending_in_doc = _sum_qty_by_item(doc.items)

    for item_code, pending_qty in pending_in_doc.items():
        issued_qty = issued_per_item.get(item_code, 0)
        prior_qty = received_prior.get(item_code, 0)
        if (prior_qty + pending_qty) > issued_qty:
            frappe.throw(
                _("Receipt qty for {0} ({1}) would exceed Issue SE qty ({2}) including {3} already received.")
                .format(item_code, pending_qty, issued_qty, prior_qty),
                title=_("Cumulative receipt exceeds issued qty"),
            )


def _recompute_po_status_if_issue(doc):
    if not _is_issue_se(doc):
        return
    if not doc.custom_purchase_order:
        return
    recompute_collaboration_status(doc.custom_purchase_order)


def _is_issue_se(doc):
    return bool(doc.custom_is_collaboration_delivery_note)


def _get_validate_receipt_qty_setting():
    return frappe.db.get_single_value("ITAG KSA Settings", "validate_receipt_qty") or 0


def _sum_qty_by_item(rows, qty_field="qty"):
    totals = {}
    for r in rows:
        totals[r.item_code] = totals.get(r.item_code, 0) + (getattr(r, qty_field, 0) or 0)
    return totals


def _issued_qty_by_item(issue_se_name):
    rows = frappe.db.sql(
        """
        SELECT item_code, SUM(qty) AS qty
        FROM `tabStock Entry Detail`
        WHERE parent = %(name)s
        GROUP BY item_code
        """,
        {"name": issue_se_name},
        as_dict=True,
    )
    return {r.item_code: r.qty or 0 for r in rows}


def _prior_received_qty_by_item(issue_se_name, exclude_name):
    rows = frappe.db.sql(
        """
        SELECT sed.item_code, SUM(sed.qty) AS qty
        FROM `tabStock Entry` se
        JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
        WHERE se.docstatus = 1
          AND se.custom_is_collaboration_grn = 1
          AND se.outgoing_stock_entry = %(issue)s
          AND se.name != %(exclude)s
        GROUP BY sed.item_code
        """,
        {"issue": issue_se_name, "exclude": exclude_name or ""},
        as_dict=True,
    )
    return {r.item_code: r.qty or 0 for r in rows}


@frappe.whitelist()
def pull_from_po(po_name):
    po_doc = frappe.get_doc("Purchase Order", po_name)
    return {
        "items": _build_se_items_from_po(po_doc, po_doc.custom_supplier_store),
        "supplier": po_doc.supplier,
        "supplier_name": po_doc.supplier_name,
        "target_warehouse": po_doc.custom_supplier_store,
    }


def _build_se_items_from_po(po_doc, target_warehouse):
    rows = []
    for row in po_doc.items:
        if not row.custom_sub_item:
            continue
        stock_uom, item_description = frappe.db.get_value(
            "Item", row.custom_sub_item, ["stock_uom", "description"]
        )
        rows.append({
            "item_code": row.custom_sub_item,
            "qty": row.qty or 0,
            "serial_no": row.custom_serial_no,
            "t_warehouse": target_warehouse,
            "uom": stock_uom,
            "stock_uom": stock_uom,
            "conversion_factor": 1,
            "description": row.custom_sub_item_description or item_description,
        })
    return rows


@frappe.whitelist()
def make_grn_from_issue(source_name):
    issue_doc = frappe.get_doc("Stock Entry", source_name)
    _guard_make_grn(issue_doc)

    def _postprocess(source, target):
        target.stock_entry_type = "Material Receipt from Supplier"
        target.purpose = "Material Transfer"
        target.custom_is_collaboration_grn = 1
        target.custom_is_collaboration_delivery_note = 0
        target.custom_purchase_order = source.custom_purchase_order
        target.custom_supplier = source.custom_supplier
        target.custom_supplier_name = source.custom_supplier_name
        target.outgoing_stock_entry = source.name
        target.from_warehouse = None
        target.to_warehouse = None
        for idx, row in enumerate(target.items):
            source_row = source.items[idx] if idx < len(source.items) else None
            row.s_warehouse = source_row.t_warehouse if source_row else None
            row.t_warehouse = None
            stock_uom = frappe.db.get_value("Item", row.item_code, "stock_uom")
            row.uom = stock_uom
            row.stock_uom = stock_uom
            row.conversion_factor = 1
            row.serial_no = source_row.serial_no if source_row else None
            row.use_serial_batch_fields = 1
        target.set_missing_values()

    receipt = get_mapped_doc(
        "Stock Entry",
        source_name,
        {
            "Stock Entry": {
                "doctype": "Stock Entry",
                "field_no_map": [
                    "name",
                    "naming_series",
                    "stock_entry_type",
                    "purpose",
                    "from_warehouse",
                    "to_warehouse",
                    "custom_is_collaboration_delivery_note",
                    "custom_is_collaboration_grn",
                    "outgoing_stock_entry",
                ],
            },
            "Stock Entry Detail": {
                "doctype": "Stock Entry Detail",
                "field_map": {
                    "qty": "qty",
                },
                "field_no_map": [
                    "name",
                    "s_warehouse",
                    "t_warehouse",
                    "uom",
                    "stock_uom",
                    "conversion_factor",
                    "basic_rate",
                    "basic_amount",
                    "amount",
                    "valuation_rate",
                    "actual_qty",
                    "serial_no",
                ],
            },
        },
        postprocess=_postprocess,
    )
    return receipt.as_dict()


def _guard_make_grn(issue_doc):
    if not issue_doc.custom_is_collaboration_delivery_note:
        frappe.throw(_("Create GRN is only available on collaboration Issue Stock Entries."))
    if issue_doc.docstatus != 1:
        frappe.throw(_("Submit the Issue Stock Entry before creating a GRN."))
