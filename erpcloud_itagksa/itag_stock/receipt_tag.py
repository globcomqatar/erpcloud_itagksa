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


def _is_incoming(row):
	"""A row that brings stock in — true unless it issues from a source warehouse."""
	return not row.get("s_warehouse")
