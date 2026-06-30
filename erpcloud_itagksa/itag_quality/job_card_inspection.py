# -*- coding: utf-8 -*-
# Copyright (c) 2026, ITAG and contributors
# For license information, please see license.txt

"""
Job Card inspection gate (cross-module seam).

The inspection-required check reads Quality Inspection state, so it is quality
logic and lives in the ITAG Quality module. It is called from the ITAG
Manufacturing Job Card on_submit handler — one import across the seam.
"""

import frappe
from frappe import _


def validate_inspection_before_submit(doc):
    """Block Job Card submission until its Quality Inspection is accepted.

    When custom_inspection_required is checked, the Job Card must have a linked
    Quality Inspection that is submitted (docstatus = 1) and status "Accepted".

    Args:
        doc: Job Card document

    Raises:
        frappe.ValidationError: If the inspection requirement is not met.
    """
    if not doc.get("custom_inspection_required", False):
        return

    if not doc.quality_inspection:
        frappe.throw(
            _("Please link a <b>Quality Inspection</b> document before completing this Job Card.")
        )

    qi_doc = frappe.get_doc("Quality Inspection", doc.quality_inspection)

    if qi_doc.get("docstatus") != 1:
        frappe.throw(
            _(f"The linked Quality Inspection <b>{doc.quality_inspection}</b> must be "
              f"<b>Submitted</b> before you can complete or submit this Job Card <b>{doc.name}</b>.")
        )

    if qi_doc.get("status") != "Accepted":
        frappe.throw(
            _(f"The linked Quality Inspection <b>{doc.quality_inspection}</b> must be "
              f"<b>Accepted</b> before you can complete or submit this Job Card <b>{doc.name}</b>.")
        )
