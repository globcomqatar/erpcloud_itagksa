# Copyright (c) 2026, ITAG KSA and Contributors
# License: MIT
"""Auto-raise a Calibration Schedule when a calibration serial is created.

Serials appear two ways: typed on the Serial No form (after_insert), or bulk-created
by a stock receipt. Stock receipts bypass the Serial No ORM hooks, so the inward
Serial and Batch Bundle is the reliable trigger — every listed serial exists by the
time the bundle is submitted. This covers every inward voucher (Purchase Receipt,
Stock Entry, Stock Reconciliation) since the bundle is the universal serial carrier.
"""

import frappe
from frappe.utils import today

from erpcloud_itagksa.itag_quality.doctype.calibration_schedule.calibration_schedule import (
	recompute_progress,
)


def serial_no_after_insert(doc, method=None):
	create_calibration_schedule(doc.name, doc.item_code)


def stock_entry_on_submit(doc, method=None):
	sync_calibration_visits(doc, completed=True)


def stock_entry_on_cancel(doc, method=None):
	sync_calibration_visits(doc, completed=False)


def sync_calibration_visits(se, completed):
	"""Complete (or reopen) the calibration visits a return receipt covers.

	Only the collaboration GRN — the equipment coming back from the supplier —
	closes a visit. Each returned row carries the visit's row name (propagated down
	the Material Request -> Purchase Order -> Stock Entry chain), so the exact visit
	is closed even when a serial has several scheduled calibrations. Cancelling the
	receipt reopens them. The visit sits on a submitted schedule, so `db.set_value`
	is the right tool; the parent tally is refreshed after.
	"""
	if not se.get("custom_is_collaboration_grn"):
		return

	schedules = set()
	for row in se.items:
		visit = row.get("custom_calibration_visit")
		if not visit or not frappe.db.exists("Calibration Schedule Detail", visit):
			continue
		if completed:
			frappe.db.set_value(
				"Calibration Schedule Detail",
				visit,
				{"completion_status": "Fully Completed", "actual_date": se.posting_date},
			)
		else:
			frappe.db.set_value(
				"Calibration Schedule Detail",
				visit,
				{"completion_status": "Pending", "actual_date": None},
			)
		schedules.add(frappe.db.get_value("Calibration Schedule Detail", visit, "parent"))

	for schedule in filter(None, schedules):
		recompute_progress(schedule)
	frappe.db.commit()


def bundle_on_submit(doc, method=None):
	if doc.type_of_transaction != "Inward":
		return
	for entry in doc.entries:
		if entry.serial_no:
			create_calibration_schedule(
				entry.serial_no, doc.item_code, source_type=doc.voucher_type, source_name=doc.voucher_no
			)


def create_calibration_schedule(serial_no, item_code, source_type=None, source_name=None):
	"""Raise one Calibration Schedule for a calibration serial, once.

	Acts only on serials whose Item is flagged as a calibration item with a
	frequency and a positive calibration count; the schedule then fans that
	frequency x count out into its schedules table. Idempotent: skips if the
	serial already sits on any Calibration Schedule line.

	When raised from a stock receipt, source_type/source_name point back to the
	voucher (Stock Entry / Purchase Receipt) so it surfaces in that voucher's
	Connections tab. Manually created serials have no source.
	"""
	if not serial_no or not item_code:
		return

	item = frappe.db.get_value(
		"Item",
		item_code,
		["custom_is_calibration_item", "custom_calibration_frequency", "custom_no_of_calibrations"],
		as_dict=True,
	)
	if not item or not item.custom_is_calibration_item:
		return
	if not item.custom_calibration_frequency or int(item.custom_no_of_calibrations or 0) < 1:
		return

	if frappe.db.exists("Calibration Schedule Item", {"serial_no": serial_no}):
		return

	company = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")

	schedule = frappe.new_doc("Calibration Schedule")
	schedule.company = company
	schedule.transaction_date = today()
	if source_type and source_name:
		schedule.source_document_type = source_type
		schedule.source_document = source_name
	schedule.append(
		"items",
		{
			"item_code": item_code,
			"serial_no": serial_no,
			"start_date": today(),
			"periodicity": item.custom_calibration_frequency,
			"no_of_visits": int(item.custom_no_of_calibrations),
		},
	)
	schedule.insert(ignore_permissions=True)
	frappe.db.commit()
