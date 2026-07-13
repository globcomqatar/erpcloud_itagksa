# -*- coding: utf-8 -*-
# Copyright (c) 2026, ITAG and contributors
# For license information, please see license.txt

import frappe
from frappe import _

# ERPNext's parser — splits on comma/newline, same as the serial:heat attributes use.
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos


def validate_item_tags(doc, method=None):
	"""Enforce a 1:1 count of Item Tags to serial numbers on receipt rows.

	Mirrors the serial:heat rule: one tag per serial, in entry order. Runs on
	Purchase Receipt and Stock Entry. Only incoming rows are checked — a tag is
	meaningful only where stock is received and serial numbers are created.
	"""
	for idx, row in enumerate(doc.items, start=1):
		if not _is_incoming(row) or not row.get("custom_item_tag"):
			continue

		serial_nos = get_serial_nos(row.get("serial_no"))
		if not serial_nos:
			continue

		item_tags = get_serial_nos(row.get("custom_item_tag"))
		if len(item_tags) != len(serial_nos):
			frappe.throw(_(
				"Row {0}: enter exactly one Item Tag per serial number "
				"({1} serial numbers, {2} item tags)."
			).format(idx, len(serial_nos), len(item_tags)))


def bind_item_tags(doc, method=None):
	"""Write each incoming row's Item Tags onto its serial numbers, 1:1 by position.

	Runs on submit of Purchase Receipt and Stock Entry. Tag i is written onto
	serial number i — both parsed in entry order — matching the serial:heat pattern.
	Counts are already reconciled in validate_item_tags.
	"""
	for row in doc.items:
		if not _is_incoming(row) or not row.get("custom_item_tag"):
			continue

		serial_nos = get_serial_nos(row.get("serial_no"))
		item_tags = get_serial_nos(row.get("custom_item_tag"))
		for serial_no, tag in zip(serial_nos, item_tags):
			frappe.db.set_value("Serial No", serial_no, "custom_item_tag", tag)


def sync_outgoing_item_tags(doc, method=None):
	"""Fetch each outgoing row's Item Tags from its serial numbers and verify them.

	The mirror of bind_item_tags: on an issue or transfer the serials already carry
	their tags, so the row must reflect them. A blank row is auto-filled from the
	serial masters; a row whose tags disagree with the serials is rejected. Only
	outgoing rows (with a source warehouse) on tag-tracked items are handled.
	"""
	for idx, row in enumerate(doc.items, start=1):
		if _is_incoming(row):
			continue

		# custom_track_item_tags is a client fetch_from the Item, so it is blank on any
		# row not typed in the UI — rows built by a mapper or server API (Material Issue
		# button, pull-from-PO, Sales Order -> Stock Entry, imports). Resolve it from the
		# Item so the tag fill runs for every outgoing row, not just hand-entered ones.
		if not row.get("custom_track_item_tags"):
			row.custom_track_item_tags = frappe.db.get_value(
				"Item", row.item_code, "custom_track_item_tags"
			)
		if not row.get("custom_track_item_tags"):
			continue

		serial_nos = get_serial_nos(row.get("serial_no"))
		if not serial_nos:
			continue

		expected = _serial_tags(serial_nos)
		if not all(expected):
			# No tags, or only some serials tagged — nothing to map 1:1 here.
			continue

		if not row.get("custom_item_tag"):
			row.custom_item_tag = "\n".join(expected)
			continue

		item_tags = get_serial_nos(row.get("custom_item_tag"))
		if item_tags != expected:
			frappe.throw(_(
				"Row {0}: Item Tags do not match the serial numbers. "
				"Expected {1}, got {2}."
			).format(idx, ", ".join(expected), ", ".join(item_tags)))


@frappe.whitelist()
def get_serial_tags(serial_nos_text):
	"""Return the Item Tags of the given serial numbers, newline-separated, in order.

	Used by the Stock Entry client script to pre-fill a row's Item Tag when serials
	are entered on an issue/transfer.
	"""
	serial_nos = get_serial_nos(serial_nos_text)
	if not serial_nos:
		return ""
	return "\n".join(_serial_tags(serial_nos))


def _serial_tags(serial_nos):
	"""Item Tag of each serial, aligned to the input order ("" when a serial has none)."""
	tags = dict(frappe.get_all(
		"Serial No",
		filters={"name": ["in", serial_nos]},
		fields=["name", "custom_item_tag"],
		as_list=True,
	))
	return [tags.get(sn) or "" for sn in serial_nos]


def _is_incoming(row):
	"""A row that brings stock in — true unless it issues from a source warehouse."""
	return not row.get("s_warehouse")
