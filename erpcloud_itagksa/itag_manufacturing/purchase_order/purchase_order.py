import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc

from erpcloud_itagksa.itag_manufacturing.utils.collab_serial import validate_serial_no_items


def validate(doc, method=None):
    if not doc.custom_is_collaboration_service_po:
        return
    validate_serial_no_items(doc, _("Collaboration PO validation"))


def recompute_collaboration_status(po_name):
    new_status = _compute_status_from_issued(po_name)
    frappe.db.set_value("Purchase Order", po_name, "custom_collaboration_status", new_status)
    return new_status


def _compute_status_from_issued(po_name):
    po_totals = _po_sub_item_totals(po_name)
    if not po_totals:
        return "Pending"

    issued = _issued_sub_item_totals(po_name)
    total_issued = sum(issued.values())
    if total_issued == 0:
        return "Pending"

    fully_covered = all(
        issued.get(sub_item, 0) >= required_qty
        for sub_item, required_qty in po_totals.items()
    )
    return "Fully Issued" if fully_covered else "Partially Issued"


def _po_sub_item_totals(po_name):
    rows = frappe.get_all(
        "Purchase Order Item",
        filters={"parent": po_name, "parenttype": "Purchase Order"},
        fields=["custom_sub_item", "qty"],
    )
    totals = {}
    for r in rows:
        if not r.custom_sub_item:
            continue
        totals[r.custom_sub_item] = totals.get(r.custom_sub_item, 0) + (r.qty or 0)
    return totals


def _issued_sub_item_totals(po_name):
    rows = frappe.db.sql(
        """
        SELECT sed.item_code AS sub_item, SUM(sed.qty) AS qty
        FROM `tabStock Entry` se
        JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
        WHERE se.docstatus = 1
          AND se.custom_purchase_order = %(po)s
          AND se.custom_is_collaboration_delivery_note = 1
        GROUP BY sed.item_code
        """,
        {"po": po_name},
        as_dict=True,
    )
    return {r.sub_item: r.qty or 0 for r in rows}


@frappe.whitelist()
def make_material_issue_se(po_name):
    po_doc = frappe.get_doc("Purchase Order", po_name)
    _guard_make_material_issue(po_doc)

    def _postprocess(source, target):
        target.stock_entry_type = "Material Issue to Supplier"
        target.purpose = "Material Transfer"
        target.custom_purchase_order = source.name
        target.custom_is_collaboration_delivery_note = 1
        target.to_warehouse = source.custom_supplier_store
        for row in target.items:
            row.t_warehouse = source.custom_supplier_store
            stock_uom = frappe.db.get_value("Item", row.item_code, "stock_uom")
            row.uom = stock_uom
            row.stock_uom = stock_uom
            row.conversion_factor = 1
        target.set_missing_values()

    se = get_mapped_doc(
        "Purchase Order",
        po_name,
        {
            "Purchase Order": {
                "doctype": "Stock Entry",
            },
            "Purchase Order Item": {
                "doctype": "Stock Entry Detail",
                "field_map": {
                    "custom_sub_item": "item_code",
                    "custom_serial_no": "serial_no",
                    "custom_sub_item_description": "description",
                },
                "field_no_map": [
                    "uom",
                    "stock_uom",
                    "conversion_factor",
                    "rate",
                    "amount",
                    "warehouse",
                    "description",
                    "item_name",
                ],
                "condition": lambda row: bool(row.custom_sub_item),
            },
        },
        postprocess=_postprocess,
    )
    return se.as_dict()


def _guard_make_material_issue(po_doc):
    if not po_doc.custom_is_collaboration_service_po:
        frappe.throw(_("Material Issue is only available on collaboration service POs."))
    if po_doc.docstatus != 1:
        frappe.throw(_("Submit the Purchase Order before issuing material."))
    if po_doc.custom_collaboration_status == "Fully Issued":
        frappe.throw(_("All sub-items have been fully issued for this PO."))
    if not po_doc.custom_supplier_store:
        frappe.throw(_("Set the Supplier Store on the PO before issuing material."))
    if not any(row.custom_sub_item for row in po_doc.items):
        frappe.throw(_("No sub-items found on this PO. Add a Sub Item to at least one row first."))
