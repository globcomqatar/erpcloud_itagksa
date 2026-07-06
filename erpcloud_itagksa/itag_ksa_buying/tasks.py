# -*- coding: utf-8 -*-
# Copyright (c) 2026, ITAG and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today

REEVALUATION_REACHED = "Re-evaluation date reached"


def freeze_lapsed_suppliers():
	"""Freeze suppliers whose re-evaluation is due or whose documents expired.

	Runs daily. Only ever sets `is_frozen` — unfreezing is manual. Each freeze
	leaves a timeline comment naming the trigger.
	"""
	cutoff = today()

	reasons = {}

	due = frappe.get_all(
		"Supplier",
		filters=[
			["is_frozen", "=", 0],
			["disabled", "=", 0],
			["custom_next_reevaluation_date", "is", "set"],
			["custom_next_reevaluation_date", "<=", cutoff],
		],
		pluck="name",
		ignore_permissions=True,
	)
	for name in due:
		reasons[name] = REEVALUATION_REACHED

	expired_docs = frappe.get_all(
		"Supplier Documents",
		filters=[
			["parenttype", "=", "Supplier"],
			["expiry_date", "is", "set"],
			["expiry_date", "<=", cutoff],
		],
		fields=["parent", "document_name"],
		ignore_permissions=True,
	)
	for row in expired_docs:
		reasons.setdefault(row.parent, "Expired document: {0}".format(row.document_name))

	if not reasons:
		return

	frozen = set(
		frappe.get_all(
			"Supplier",
			filters={"name": ["in", list(reasons)], "is_frozen": 1},
			pluck="name",
			ignore_permissions=True,
		)
	)

	for name, reason in reasons.items():
		if name in frozen:
			continue
		frappe.db.set_value("Supplier", name, "is_frozen", 1)
		frappe.get_doc("Supplier", name).add_comment("Info", "Auto-frozen: {0}".format(reason))

	frappe.db.commit()
