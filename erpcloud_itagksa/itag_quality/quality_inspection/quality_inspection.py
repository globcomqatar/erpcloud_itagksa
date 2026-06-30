# -*- coding: utf-8 -*-
# Copyright (c) 2026, Globcom Manufacturing and contributors
# For license information, please see license.txt

"""
Quality Inspection Controller

Handles auto-submission of linked Job Card when Quality Inspection is submitted.

Stock Entry auto-submit moved to `quality_itagqatar` on 2026-05-14
(see quality_itagqatar.quality_itag_qatar.quality_inspection.auto_submit).
"""

import frappe
from frappe import _


def on_submit(doc, method=None):
    """Auto-submit linked Job Card when Quality Inspection is submitted.

    Called via doc_events hook in hooks.py.

    Args:
        doc: Quality Inspection document
        method: Event method name (not used)
    """
    if doc.reference_type == "Job Card" and doc.reference_name:
        auto_submit_job_card(doc)


def auto_submit_job_card(doc):
    """Auto-submit linked Job Card when Quality Inspection is submitted.

    Only submits if:
    - Job Card is in draft state (docstatus = 0)
    - User has permission to submit Job Card
    - Job Card passes all standard validations

    If validation fails, shows warning but doesn't block QI submission (lenient).

    Args:
        doc: Quality Inspection document
    """
    # Get the linked Job Card
    try:
        job_card = frappe.get_doc("Job Card", doc.reference_name)
    except frappe.DoesNotExistError:
        frappe.msgprint(
            _("Job Card {0} does not exist").format(doc.reference_name),
            title=_("Job Card Not Found"),
            indicator="red",
            alert=True
        )
        return

    # Check if Job Card is already submitted
    if job_card.docstatus == 1:
        # Already submitted - skip silently (idempotent)
        return

    if job_card.docstatus == 2:
        # Cancelled - cannot submit
        frappe.msgprint(
            _("Job Card {0} is cancelled. Cannot auto-submit.").format(doc.reference_name),
            indicator="orange",
            alert=True
        )
        return

    # Check if user has permission to submit Job Card
    if not job_card.has_permission("submit"):
        frappe.msgprint(
            _("You don't have permission to submit Job Card {0}. Please ask a user with submit permissions to complete this Job Card.").format(
                frappe.bold(doc.reference_name)
            ),
            title=_("Insufficient Permissions"),
            indicator="orange",
            alert=True
        )
        return

    # Validate Job Card is ready to submit
    is_ready, error_message = validate_job_card_ready_to_submit(job_card)

    if not is_ready:
        # Not ready - show warning (lenient: don't block QI submission)
        frappe.msgprint(
            _("Job Card {0} cannot be auto-submitted: {1}<br><br>Please submit the Job Card manually after fixing these issues.").format(
                frappe.bold(doc.reference_name),
                error_message
            ),
            title=_("Job Card Not Ready"),
            indicator="orange",
            alert=True
        )
        return

    # Job Card is ready - attempt to submit
    try:
        job_card.submit()
        frappe.msgprint(
            _("Job Card {0} has been submitted automatically").format(
                frappe.get_desk_link("Job Card", doc.reference_name)
            ),
            indicator="green",
            alert=True
        )
    except frappe.ValidationError as e:
        # Validation error - show warning (lenient)
        frappe.msgprint(
            _("Job Card {0} could not be auto-submitted due to validation errors: {1}<br><br>Please submit manually after fixing these issues.").format(
                frappe.bold(doc.reference_name),
                str(e)
            ),
            title=_("Job Card Auto-Submit Failed"),
            indicator="orange",
            alert=True
        )
        frappe.log_error(
            message=f"Job Card auto-submit failed for {doc.reference_name}: {frappe.get_traceback()}",
            title="Job Card Auto-Submit Validation Error"
        )
    except Exception as e:
        # Other errors - show warning and log
        frappe.msgprint(
            _("Job Card {0} could not be auto-submitted: {1}<br><br>Please submit manually.").format(
                frappe.bold(doc.reference_name),
                str(e)
            ),
            title=_("Job Card Auto-Submit Failed"),
            indicator="red",
            alert=True
        )
        frappe.log_error(
            message=f"Job Card auto-submit failed for {doc.reference_name}: {frappe.get_traceback()}",
            title="Job Card Auto-Submit Error"
        )


def validate_job_card_ready_to_submit(job_card):
    """Validate if Job Card meets all standard ERPNext submission requirements.

    Checks:
    1. Time logs exist (not empty)
    2. Quantities match: for_quantity <= total_completed_qty + process_loss_qty
    3. Materials transferred (if items exist): transferred_qty >= for_quantity
    4. Work Order status != "Stopped"
    5. Time log dates filled (if enforce_time_logs enabled)

    Args:
        job_card: Job Card document

    Returns:
        tuple: (bool, str) - (is_ready, error_message)
            - is_ready: True if Job Card can be submitted, False otherwise
            - error_message: Description of validation failures (empty if is_ready=True)
    """
    from frappe.utils import flt

    errors = []

    # 1. Check if Work Order is stopped
    if job_card.work_order:
        wo_status = frappe.get_cached_value("Work Order", job_card.work_order, "status")
        if wo_status == "Stopped":
            errors.append(_("Work Order {0} is stopped").format(
                frappe.bold(job_card.work_order)
            ))

    # 2. Check time logs exist
    if not job_card.time_logs:
        errors.append(_("Time logs are required"))
    else:
        # 3. Check if enforce_time_logs is enabled - validate from_time and to_time
        enforce_time_logs = frappe.db.get_single_value("Manufacturing Settings", "enforce_time_logs")
        if enforce_time_logs:
            for idx, row in enumerate(job_card.time_logs, start=1):
                if not row.from_time or not row.to_time:
                    errors.append(_("Row #{0}: From Time and To Time are required").format(idx))

    # 4. Check quantities match
    precision = job_card.precision("total_completed_qty")
    total_completed_qty = flt(
        flt(job_card.total_completed_qty, precision) + flt(job_card.process_loss_qty, precision)
    )

    if job_card.for_quantity and flt(total_completed_qty, precision) != flt(job_card.for_quantity, precision):
        errors.append(
            _("Total Completed Qty ({0}) must equal Qty to Manufacture ({1})").format(
                frappe.bold(flt(total_completed_qty, precision)),
                frappe.bold(job_card.for_quantity)
            )
        )

    # 5. Check materials transferred (if items exist and not corrective job card)
    if not job_card.is_corrective_job_card and job_card.items:
        if flt(job_card.transferred_qty) < flt(job_card.for_quantity):
            errors.append(
                _("Materials need to be transferred to work in progress warehouse (Transferred: {0}, Required: {1})").format(
                    frappe.bold(job_card.transferred_qty),
                    frappe.bold(job_card.for_quantity)
                )
            )

    # Return validation result
    if errors:
        return False, "<br>".join(errors)
    else:
        return True, ""
