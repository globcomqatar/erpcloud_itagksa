# Copyright (c) 2026, ITAG KSA and Contributors
# License: MIT
"""Raise incoming Quality Inspections for the serials on a flagged Stock Entry.

A Stock Entry marked Quality Verification Required brings in material that has to
be checked serial by serial, so each serial gets its own Quality Inspection and a
mixed receipt can be part accepted and part rejected.
"""

import frappe
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.serial_batch_bundle import get_serial_nos_from_bundle
from frappe import _


INSPECTION_ROLE_FIELD = "inward_inspection_role"


@frappe.whitelist()
def create_quality_inspections(stock_entry):
	"""Create one draft Incoming Quality Inspection per received serial.

	Returns the names created. Serials already carrying an inspection on this Stock
	Entry are skipped, so the button can be pressed again after more serials are
	entered without duplicating what is already there.
	"""
	source = frappe.get_doc("Stock Entry", stock_entry)
	if source.docstatus == 2:
		frappe.throw(_("{0} is cancelled.").format(source.name))

	if not user_may_inspect():
		frappe.throw(
			_("Only the {0} role can create Quality Inspections.").format(inspection_role()),
			frappe.PermissionError,
		)

	if not any(received_serials(row) for row in source.items):
		frappe.throw(_("No serial numbers on the received rows of {0} to inspect.").format(source.name))

	return [new_inspection(source, row, serial_no).name for row, serial_no in pending_serials(source)]


@frappe.whitelist()
def may_create_quality_inspections(stock_entry):
	"""Whether the Create Quality Inspection button has anything left to offer.

	The form cannot work this out on its own: the serials may sit in a Serial and
	Batch Bundle rather than on the row, and the configured role lives on a Single
	the user need not be able to read.
	"""
	source = frappe.get_doc("Stock Entry", stock_entry)
	if source.docstatus == 2 or not user_may_inspect():
		return False

	return bool(pending_serials(source))


def inspection_role():
	return frappe.db.get_single_value("ITAG KSA Settings", INSPECTION_ROLE_FIELD)


def user_may_inspect():
	"""No configured role means the site has not restricted this yet — stay open.

	Locking everyone out of the receipt flow until someone fills in a setting would
	be a worse failure than leaving it as it was before the setting existed.
	"""
	role = inspection_role()
	if not role:
		return True
	return role in frappe.get_roles()


def pending_serials(source):
	"""Received serials still without an inspection, each paired with its row."""
	inspected = already_inspected_serials(source.name)
	return [
		(row, serial_no)
		for row in source.items
		for serial_no in received_serials(row)
		if serial_no not in inspected
	]


def received_serials(row):
	"""Serials the row brings in — an outgoing row creates nothing to inspect.

	Serials live either in the row's own field or in its Serial and Batch Bundle,
	depending on the Stock Settings 'Use Serial / Batch Fields' toggle and on how
	the entry was raised; both carriers are in use.
	"""
	if row.s_warehouse:
		return []
	return get_serial_nos(row.serial_no) or get_serial_nos_from_bundle(row.serial_and_batch_bundle)


def already_inspected_serials(stock_entry):
	return set(
		frappe.get_all(
			"Quality Inspection",
			filters={
				"reference_type": "Stock Entry",
				"reference_name": stock_entry,
				"docstatus": ("<", 2),
			},
			pluck="item_serial_no",
		)
	)


def new_inspection(source, row, serial_no):
	"""Draft inspection for one serial — readings come from the Item's template.

	Left as a draft: the inspector fills the readings and submits, which is what
	decides Accepted or Rejected.

	Inserted with ignore_links because inspection happens on the draft receipt, before
	the Stock Entry is submitted and the Serial No records exist. item_serial_no holds
	the name the serial will be given, so the link resolves once the receipt is
	submitted. Link validation still runs when the inspector submits the inspection,
	which keeps a serial that was never actually received from being signed off.
	"""
	inspection = frappe.new_doc("Quality Inspection")
	inspection.inspection_type = "Incoming"
	inspection.reference_type = "Stock Entry"
	inspection.reference_name = source.name
	inspection.item_code = row.item_code
	inspection.item_serial_no = serial_no
	inspection.batch_no = row.batch_no
	inspection.sample_size = 1
	inspection.company = source.company
	# The field's "user" default is resolved by the form, not by new_doc server-side.
	inspection.inspected_by = frappe.session.user
	inspection.insert(ignore_links=True)
	return inspection
