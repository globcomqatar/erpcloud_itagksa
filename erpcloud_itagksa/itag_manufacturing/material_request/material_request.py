# Copyright (c) 2026, Globcom Qatar and contributors
# For license information, please see license.txt

"""
Material Request collaboration hook for ITAG KSA.

validate: When MR is a collaboration service request, ensure each row's Serial
No, if set, belongs to the row's custom_sub_item Item and is not already
delivered.
"""

from frappe import _

from erpcloud_itagksa.itag_manufacturing.utils.collab_serial import validate_serial_no_items
from erpcloud_itagksa.itag_manufacturing.utils.supplier_store import apply_default_supplier_store


def validate(doc, method=None):
    apply_default_supplier_store(doc)
    if not doc.get("custom_is_collaboration_service_po"):
        return
    validate_serial_no_items(doc, _("Collaboration MR validation"))
