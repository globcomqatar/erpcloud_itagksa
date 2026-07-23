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

from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

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
				entry.serial_no,
				doc.item_code,
				source_type=doc.voucher_type,
				source_name=doc.voucher_no,
				purchase_date=doc.posting_date,
			)


def create_calibration_schedule(
	serial_no, item_code, source_type=None, source_name=None, purchase_date=None
):
	"""Raise one draft Calibration Schedule for a calibration serial, once.

	Acts only on serials whose Item is flagged as a calibration item. The schedule
	is left as a draft: end of life date and number of calibrations are the
	operator's call, and the visit rows appear only once they press Generate
	Calibration Schedule. Idempotent: skips if the serial already has a schedule.

	When raised from a stock receipt, source_type/source_name point back to the
	voucher (Stock Entry / Purchase Receipt) so it surfaces in that voucher's
	Connections tab, and the receipt's posting date seeds the purchase date.
	Manually created serials have no source, so the purchase date falls back to today.
	"""
	if not serial_no or not item_code:
		return

	if not frappe.db.get_value("Item", item_code, "custom_is_calibration_item"):
		return

	if frappe.db.exists("Calibration Schedule", {"serial_no": serial_no}):
		return

	company = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")

	schedule = frappe.new_doc("Calibration Schedule")
	schedule.company = company
	schedule.transaction_date = today()
	if source_type and source_name:
		schedule.source_document_type = source_type
		schedule.source_document = source_name
	schedule.item_code = item_code
	schedule.serial_no = serial_no
	schedule.purchase_date = purchase_date or today()
	schedule.insert(ignore_permissions=True)
	frappe.db.commit()


def stamp_schedule_item_tags(doc, method=None):
	"""Fill Item Tag on calibration schedules once the receipt has tagged its serials.

	A schedule auto-raised from an inward voucher is created (via the serial bundle)
	before bind_item_tags writes each row's Item Tag onto its serials, so it starts
	with a blank tag. Wired LAST on the voucher's on_submit, this runs after the tags
	exist and copies each serial's tag onto the schedule header and its visit rows.
	"""
	serials = set()
	for row in doc.items:
		if row.get("s_warehouse"):  # outgoing row — no serials created here
			continue
		serials.update(get_serial_nos(row.get("serial_no")))

	for serial_no in serials:
		tag = frappe.db.get_value("Serial No", serial_no, "custom_item_tag")
		if tag:
			_stamp_tag_on_schedules(serial_no, tag)


def _stamp_tag_on_schedules(serial_no, tag):
	"""Write the tag onto every blank Item Tag field carrying this serial."""
	for schedule in frappe.get_all(
		"Calibration Schedule", filters={"serial_no": serial_no}, fields=["name", "item_tag"]
	):
		if not schedule.item_tag:
			frappe.db.set_value("Calibration Schedule", schedule.name, "item_tag", tag, update_modified=False)

	for row in frappe.get_all(
		"Calibration Schedule Detail", filters={"serial_no": serial_no}, fields=["name", "item_tag"]
	):
		if not row.item_tag:
			frappe.db.set_value(
				"Calibration Schedule Detail", row.name, "item_tag", tag, update_modified=False
			)
