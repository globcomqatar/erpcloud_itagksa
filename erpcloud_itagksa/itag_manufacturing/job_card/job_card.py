# -*- coding: utf-8 -*-
# Copyright (c) 2026, Globcom Manufacturing and contributors
# For license information, please see license.txt

"""
Custom Job Card Controller (Doc Events Approach)

Extends standard ERPNext Job Card with:
- Auto-population of operation description from Work Order Operation
- Auto-population of quality inspection requirement flag
- Quality Inspection validation on submission

CONVERTED: 2026-02-08 - From override_doctype_class to doc_events
Reason: Testing if override class was causing random submission bugs
"""

import frappe
from frappe import _


def validate(doc, method=None):
    """Validate Job Card before save/submit.

    ERPNext's JobCard.validate() runs first, then this hook.

    Args:
        doc: Job Card document
        method: Event method name (not used)

    Validations:
    - Serial number required for time logs (unless bypassed)
    """
    # DEBUG: Log current state BEFORE validation
    frappe.logger().debug(f"""
    🔍 [JOB CARD VALIDATE - DOC EVENTS] {doc.name}
    - Current docstatus: {doc.docstatus}
    - Current status: {doc.status}
    - Quality Inspection: {doc.quality_inspection}
    - custom_inspection_required: {doc.custom_inspection_required}
    - Completed Qty: {doc.total_completed_qty} / {doc.for_quantity}
    - Has items: {len(doc.items) if doc.items else 0}
    """)

    validate_serial_for_time_logs(doc)

    # DEBUG: Log state AFTER validation
    frappe.logger().debug(f"""
    🔍 [JOB CARD AFTER VALIDATE - DOC EVENTS] {doc.name}
    - docstatus: {doc.docstatus}
    - status: {doc.status}
    """)


def validate_serial_for_time_logs(doc):
    """Validate that serial number is selected when time logs exist.

    Can be bypassed with custom_serial_no_not_available checkbox.

    Validation logic:
    - If parent has serial: PASS (user is working on a time log)
    - If work is completed (all time logs have serials + qty completed): PASS
    - Otherwise: FAIL (serial required)

    Args:
        doc: Job Card document

    Raises:
        frappe.ValidationError: If time logs exist but no serial and not bypassed
    """
    # Check if bypass is enabled
    if doc.get("custom_serial_no_not_available"):
        return  # Validation bypassed

    # Check if time logs exist with actual time entries
    if not doc.time_logs or len(doc.time_logs) == 0:
        return  # No time logs, validation not needed

    has_time_entries = False
    for log in doc.time_logs:
        if log.get("from_time") or log.get("to_time"):
            has_time_entries = True
            break

    if not has_time_entries:
        return  # No actual time entries yet

    # Check if parent has serial (user is currently working)
    if doc.get("custom_work_order_serial_no"):
        return  # Parent has serial - validation passed

    # Parent has NO serial - check if work is completed
    # Work is completed when:
    # 1. All time logs have serial numbers
    # 2. for_quantity = total_completed_qty + process_loss_qty

    # Check condition 1: All time logs have serials
    all_time_logs_have_serials = True
    for log in doc.time_logs:
        if log.get("from_time") or log.get("to_time"):
            if not log.get("custom_serial_no"):
                all_time_logs_have_serials = False
                break

    # Check condition 2: Quantity completed
    from frappe.utils import flt
    for_quantity = flt(doc.get("for_quantity"))
    total_completed = flt(doc.get("total_completed_qty"))
    process_loss = flt(doc.get("process_loss_qty"))
    quantity_completed = (for_quantity == (total_completed + process_loss))

    # If both conditions met, work is completed - skip validation
    if all_time_logs_have_serials and quantity_completed:
        return  # Work completed - ready to submit

    # Work NOT completed but parent has no serial - throw error
    frappe.throw(
        _(
            "Please select a <b>Serial Number</b> before adding time logs.<br><br>"
            "Or check <b>'Serial No Not Available'</b> if serial no is not available."
        ),
        title=_("Serial Number Required")
    )


def before_save(doc, method=None):
    """Auto-populate custom fields from Work Order Operation and Serial No.

    ERPNext's JobCard.before_save() runs first, then this hook.

    Args:
        doc: Job Card document
        method: Event method name (not used)

    Fetches and populates:
    - custom_operation_description: Description from Work Order Operation
    - custom_inspection_required: Quality inspection requirement flag
    - custom_heat_no, custom_drawing_no, custom_part_no: From Serial No master
    """
    # DEBUG: Log state BEFORE save
    frappe.logger().debug(f"""
    🔍 [JOB CARD BEFORE_SAVE - DOC EVENTS] {doc.name}
    - docstatus: {doc.docstatus}
    - status: {doc.status}
    - Quality Inspection: {doc.quality_inspection}
    """)

    from erpcloud_itagksa.itag_quality.acceptance_criteria.acceptance_criteria import (
        propagate_job_card_from_wo,
    )
    propagate_job_card_from_wo(doc)

    # Fetch serial attributes from Serial No master if serial is selected
    fetch_serial_attributes(doc)


def fetch_serial_attributes(doc):
    """Fetch heat_no, heat_lot_no, drawing_no, part_no from Serial No master.

    Called before save to ensure serial attributes persist even with
    fetch_from configuration on fields.

    Args:
        doc: Job Card document
    """
    if not doc.get("custom_work_order_serial_no"):
        return

    try:
        # Get Serial No document
        serial_no = doc.custom_work_order_serial_no
        serial_doc = frappe.get_doc("Serial No", serial_no)

        # Set attributes from Serial No master (overrides fetch_from)
        doc.custom_heat_no = serial_doc.get('custom_heat_no') or ''
        doc.custom_heat_lot_no = serial_doc.get('custom_heat_lot_no') or ''
        doc.custom_drawing_no = serial_doc.get('custom_drawing_no') or ''
        doc.custom_part_no = serial_doc.get('custom_part_no') or ''

    except frappe.DoesNotExistError:
        # Serial doesn't exist - clear fields
        doc.custom_heat_no = ''
        doc.custom_heat_lot_no = ''
        doc.custom_drawing_no = ''
        doc.custom_part_no = ''

    except Exception as e:
        # Log error but don't block save
        frappe.log_error(
            message=f"Error fetching serial attributes for Job Card {doc.name}: {frappe.get_traceback()}",
            title="Job Card Serial Attributes Fetch Error"
        )


def on_submit(doc, method=None):
    """Validate Quality Inspection before submission.

    ERPNext's JobCard.on_submit() runs first, then this hook.

    Args:
        doc: Job Card document
        method: Event method name (not used)

    If custom_inspection_required is checked:
    - Requires Quality Inspection to be linked
    - Validates Quality Inspection is submitted (docstatus = 1)
    - Validates Quality Inspection status is "Accepted"

    Raises:
        frappe.ValidationError: If validation fails
    """
    # DEBUG: Log submission attempt
    frappe.logger().debug(f"""
    🚨 [JOB CARD ON_SUBMIT - DOC EVENTS] {doc.name}
    - Submitting Job Card!
    - Quality Inspection: {doc.quality_inspection}
    - Stack trace: {frappe.get_traceback()}
    """)

    # Inspection gate lives in the quality module (cross-module seam)
    from erpcloud_itagksa.itag_quality.job_card_inspection import (
        validate_inspection_before_submit,
    )
    validate_inspection_before_submit(doc)

    # Update Work Order job cards completion status
    update_work_order_job_cards_status(doc)


@frappe.whitelist()
def persist_auto_selected_serial(job_card, serial_no):
	"""Persist auto-selected serial and its attributes directly to DB.

	Called by the client when a single serial is auto-selected on form open.
	Fetches attributes from the Serial No master and writes everything in one
	db_set call, keeping the form clean (not dirty) from the user's perspective.

	Args:
		job_card (str): Job Card docname.
		serial_no (str): Serial number to persist.

	Returns:
		dict: Fetched attributes {heat_no, heat_lot_no, drawing_no, part_no}
		      so the client can update the UI without a second server call.
	"""
	frappe.has_permission("Job Card", ptype="write", doc=job_card, throw=True)

	serial_attributes = (
		frappe.db.get_value(
			"Serial No",
			serial_no,
			["custom_heat_no", "custom_heat_lot_no", "custom_drawing_no", "custom_part_no"],
			as_dict=True,
		)
		or {}
	)

	frappe.db.set_value(
		"Job Card",
		job_card,
		{
			"custom_work_order_serial_no": serial_no,
			"custom_heat_no": serial_attributes.get("custom_heat_no") or "",
			"custom_heat_lot_no": serial_attributes.get("custom_heat_lot_no") or "",
			"custom_drawing_no": serial_attributes.get("custom_drawing_no") or "",
			"custom_part_no": serial_attributes.get("custom_part_no") or "",
		},
		update_modified=False,
	)

	return {
		"heat_no": serial_attributes.get("custom_heat_no") or "",
		"heat_lot_no": serial_attributes.get("custom_heat_lot_no") or "",
		"drawing_no": serial_attributes.get("custom_drawing_no") or "",
		"part_no": serial_attributes.get("custom_part_no") or "",
	}


def on_update(doc, method=None):
    """Update Work Order when Job Card status changes.

    ERPNext's JobCard.on_update() runs first, then this hook.

    Args:
        doc: Job Card document
        method: Event method name (not used)
    """
    auto_create_quality_inspection_if_needed(doc)

    # Update Work Order job cards completion status when status changes
    if doc.docstatus == 1:  # Only for submitted Job Cards
        update_work_order_job_cards_status(doc)

def on_cancel(doc, method=None):
    """Update Work Order when Job Card is cancelled.

    ERPNext's JobCard.on_cancel() runs first, then this hook.

    Args:
        doc: Job Card document
        method: Event method name (not used)
    """
    # Recheck Work Order job cards status (cancelled ones are now excluded)
    update_work_order_job_cards_status(doc)


def update_work_order_job_cards_status(doc):
    """Check if all Job Cards for Work Order are completed and update flag.

    Updates Work Order's custom_job_cards_completed field:
    - Sets to 1 if all Job Cards have status "Completed"
    - Sets to 0 if any Job Card is not completed
    - Ignores cancelled Job Cards (docstatus = 2)

    Args:
        doc: Job Card document
    """
    if not doc.work_order:
        return

    # Get all Job Cards for this Work Order (excluding cancelled)
    job_cards = frappe.get_all(
        "Job Card",
        filters={
            "work_order": doc.work_order,
            "docstatus": ["!=", 2]  # Exclude cancelled Job Cards
        },
        fields=["name", "status"]
    )

    if not job_cards:
        return

    # Check if all Job Cards are completed
    all_completed = all(jc["status"] == "Completed" for jc in job_cards)

    # Update Work Order field - using get_doc and save to trigger notifications
    try:
        work_order_doc = frappe.get_doc("Work Order", doc.work_order)
        work_order_doc.custom_job_cards_completed = 1 if all_completed else 0

        # Save without updating modified timestamp to avoid affecting Work Order's modification history
        work_order_doc.save(ignore_permissions=True)

    except Exception as e:
        # Log error but don't block Job Card save
        frappe.log_error(
            message=f"Error updating Work Order job cards status for {doc.work_order}: {frappe.get_traceback()}",
            title="Work Order Job Cards Status Update Error"
        )
def auto_create_quality_inspection_if_needed(doc):
    """Auto-create Quality Inspection when conditions are met.

    Conditions:
    1. for_quantity == total_completed_qty + process_loss_qty
    2. custom_inspection_required == 1
    3. No QI already linked
    4. Job Card is saved (has name)

    Args:
        doc: Job Card document
    """
    # Condition 1: Check if QI already exists
    if doc.quality_inspection:
        return  # Already has QI, skip

    # Condition 2: Check if inspection is required
    if not doc.get("custom_inspection_required"):
        return  # Inspection not required, skip

    # Condition 3: Check if Job Card is saved
    if not doc.name:
        return  # Not saved yet, skip

    # Condition 4: Check if quantities match
    from frappe.utils import flt
    for_quantity = flt(doc.for_quantity)
    total_completed = flt(doc.total_completed_qty)
    process_loss = flt(doc.process_loss_qty)

    if for_quantity != (total_completed + process_loss):
        return  # Quantities don't match, skip

    # All conditions passed - create Quality Inspection
    try:
        qi_doc = frappe.get_doc({
            "doctype": "Quality Inspection",
            "inspection_type": "In Process",
            "reference_type": "Job Card",
            "reference_name": doc.name,
            "item_code": doc.production_item,
            "sample_size": doc.for_quantity,
            "inspected_by": frappe.session.user
        })

        qi_doc.insert(ignore_permissions=True)

        # Link QI to Job Card
        doc.db_set("quality_inspection", qi_doc.name, update_modified=False)

        frappe.msgprint(
            _("Quality Inspection {0} created automatically").format(qi_doc.name),
            alert=True,
            indicator="green"
        )

    except Exception:
        frappe.log_error(
            message=f"Error auto-creating Quality Inspection for Job Card {doc.name}: {frappe.get_traceback()}",
            title="Auto-Create QI Error"
        )