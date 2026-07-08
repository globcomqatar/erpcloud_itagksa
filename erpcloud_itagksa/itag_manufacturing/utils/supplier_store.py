# Copyright (c) 2026, Globcom Qatar and contributors
# For license information, please see license.txt

"""Default Supplier Store for Material Request and Purchase Order.

Prefills custom_supplier_store from ITAG KSA Settings on a new document. A value
the user has already set is never overwritten.
"""

import frappe


def apply_default_supplier_store(doc):
	if not doc.is_new() or doc.get("custom_supplier_store"):
		return

	default_store = frappe.db.get_single_value("ITAG KSA Settings", "default_supplier_store")
	if default_store:
		doc.custom_supplier_store = default_store
