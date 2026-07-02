# Copyright (c) 2026, Globcom Qatar and contributors
# For license information, please see license.txt

"""
Shared validation for collaboration Calibration Item rows on Purchase Order Item
and Material Request Item. When a row's Serial No is set it must exist, belong to
the row's Calibration Item, and not be already delivered.

Kept separate from serial_no_validation.py: that module checks heat/part/drawing
attributes against the Serial No master; this one checks calibration-item
membership and delivered status for the collaboration service flow.
"""

import frappe
from frappe import _

DELIVERED_STATUS = "Delivered"


def validate_serial_no_items(doc, validation_title):
    for row in doc.items:
        serial = row.get("custom_serial_no")
        if not serial:
            continue
        if not row.get("custom_sub_item"):
            frappe.throw(
                _("Row {0}: Calibration Item is required when Serial No is set.").format(row.idx),
                title=validation_title,
            )
        _validate_serial(row, serial, validation_title)


def _validate_serial(row, serial, validation_title):
    sn = frappe.db.get_value(
        "Serial No", serial, ["item_code", "status"], as_dict=True
    )
    if not sn:
        frappe.throw(
            _("Row {0}: Serial No {1} does not exist.").format(row.idx, serial),
            title=validation_title,
        )
    if sn.item_code != row.custom_sub_item:
        frappe.throw(
            _("Row {0}: Serial No {1} belongs to Item {2}, not Calibration Item {3}.")
            .format(row.idx, serial, sn.item_code, row.custom_sub_item),
            title=validation_title,
        )
    if sn.status == DELIVERED_STATUS:
        frappe.throw(
            _("Row {0}: Serial No {1} is already delivered and cannot be selected.")
            .format(row.idx, serial),
            title=validation_title,
        )
